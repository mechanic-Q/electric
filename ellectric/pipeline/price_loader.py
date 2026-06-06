"""
电价数据加载器 — ZionLuo xlsx 数据接入层
===========================================

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PriceDataLoader **不继承 DataLoader 抽象基类**。这是因为电价数据格式与
负荷数据差异大：7 列多维度数据（价格、负荷、新能源、联络线），而非单列
负荷。如果强行套用 DataLoader 接口，反而会引入不必要的抽象负担。

这里遵循的是**组合优于继承 (Composition over Inheritance)** 原则：
提供独立的 PriceDataLoader，其接口与 DataLoader 风格一致（load_data()、
get_metadata()），但不共享其 ABC 继承链。

数据源架构 (Data Source Architecture)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    ┌────────────────────────────────────────────────────┐
    │                PriceDataLoader                      │
    │  load_data() → pd.DataFrame (7 columns)              │
    │  列: timestamp, price_da, price_rt, load_mw,         │
    │      wind_mw, solar_mw, tie_line_mw                  │
    └────────────────────────┬───────────────────────────┘
                             │
                             ▼
    ┌────────────────────────────────────────────────────┐
    │           ZionLuo price_data.xlsx                    │
    │  日前价格 | 实时价格 | 统调负荷 | 风电 | 光伏 | 联络线  │
    │  ~2000 行, 小时级, 中国短期现货数据                    │
    └────────────────────────────────────────────────────┘

数据来源说明 (Data Source)
~~~~~~~~~~~~~~~~~~~~~~~~~~

数据来自 ZionLuo/Electricity-Price-Forecasting GitHub 仓库中的
price data.xlsx 文件，包含约 2000 条中国省份小时级电力市场数据。

共 7 列:
+-----------+----------+----------+----------+----------+-----------+-------------+
| timestamp | price_da | price_rt | load_mw  | wind_mw  | solar_mw  | tie_line_mw  |
+-----------+----------+----------+----------+----------+-----------+-------------+
| UTC 时间   | 日前价格   | 实时价格   | 统调负荷   | 风电出力   | 光伏出力    | 省间联络线    |
|           | (元/MWh) | (元/MWh) | (MW)     | (MW)     | (MW)      | (MW)        |
+-----------+----------+----------+----------+----------+-----------+-------------+

模块职责 (Module Responsibilities)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- PriceDataLoader      : 加载 xlsx → 列名标准化 → UTC 时区 → 排序返回
- create_price_loader(): 工厂函数，简化构造
- _standardize_columns(): 内部函数，中文列名 → 英文标准名
"""

from pathlib import Path
from typing import Optional

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# 列名标准化映射表
# ═══════════════════════════════════════════════════════

COLUMN_NAME_MAP: dict[tuple[str, ...], str] = {
    # 时间戳
    ("时间", "日期", "datetime", "time"): "timestamp",
    # 日前价格
    ("日前价格", "日前", "dam", "day_ahead_price"): "price_da",
    # 实时价格
    ("实时价格", "实时", "rt", "real_time_price"): "price_rt",
    # 统调负荷
    ("负荷", "统调负荷", "用电负荷", "load"): "load_mw",
    # 风电出力
    ("风电", "风电出力", "wind"): "wind_mw",
    # 光伏出力
    ("光伏", "光伏出力", "solar", "pv", "光"): "solar_mw",
    # 省间联络线
    ("联络线", "省间联络线", "tie_line", "省间"): "tie_line_mw",
}


# ═══════════════════════════════════════════════════════
# PriceDataLoader
# ═══════════════════════════════════════════════════════


class PriceDataLoader:
    """
    加载 ZionLuo xlsx 电价数据，返回列名标准化、时区统一的 DataFrame。

    与 DataLoader (Phase 1) 的区别:
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - 不继承 ABC：电价数据多列结构（7 列），不适合套用单列负荷的 load_data() 接口
    - 不接受 start/end 过滤参数：Wave 1 不要求时间范围过滤
    - 返回 DataFrame 含 7 列而非 3 列

    Example:
        >>> loader = PriceDataLoader("data/price_data.xlsx")
        >>> df = loader.load_data()
        >>> df.columns.tolist()
        ['timestamp', 'price_da', 'price_rt', 'load_mw', 'wind_mw', 'solar_mw', 'tie_line_mw']
    """

    def __init__(self, data_path: str) -> None:
        """
        Args:
            data_path: xlsx 文件路径（相对于项目根目录或绝对路径）
                       例如: 'data/price_data.xlsx'
        """
        self.data_path = Path(data_path)
        self.data_version = self.data_path.stem
        self._metadata_source = f"ZionLuo ({self.data_path.name})"
        self._metadata_version = self.data_version

    # ── 数据加载 ────────────────────────────────────────

    def load_data(self) -> pd.DataFrame:
        """
        加载 ZionLuo xlsx 文件，标准化列名，统一时区为 UTC，按时间排序。

        Returns:
            DataFrame with 7 columns:
            - timestamp:   datetime64[ns, UTC]
            - price_da:    float64  日前价格 (元/MWh)
            - price_rt:    float64  实时价格 (元/MWh)
            - load_mw:     float64  统调负荷 (MW)
            - wind_mw:     float64  风电出力 (MW)
            - solar_mw:    float64  光伏出力 (MW)
            - tie_line_mw: float64  省间联络线功率 (MW)

        Raises:
            FileNotFoundError: xlsx 文件不存在
        """
        # ── 检查文件存在 ──
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"电价数据文件未找到: {self.data_path}\n"
                f"请从 ZionLuo/Electricity-Price-Forecasting 仓库下载\n"
                f"  https://github.com/ZionLuo/Electricity-Price-Forecasting\n"
                f"将 price data.xlsx 放到 data/ 目录后重新运行。"
            )

        logger.info(f"加载电价数据: {self.data_path}")

        # ── 读取 xlsx（默认第一个 sheet） ──
        xls = pd.ExcelFile(self.data_path)
        sheet_name = xls.sheet_names[0]
        if len(xls.sheet_names) > 1:
            logger.info(f"xlsx 包含 {len(xls.sheet_names)} 个 sheet，默认读取第一个: '{sheet_name}'")
        df = pd.read_excel(self.data_path, sheet_name=sheet_name)

        logger.info(f"原始列名: {list(df.columns)}")

        # ── 标准化列名 ──
        df, unrecognized = _standardize_columns(df)
        if unrecognized:
            logger.warning(f"未识别的列名，将保留原列名: {unrecognized}")

        # ── 检查必需列 ──
        required = {"timestamp", "price_da", "price_rt", "load_mw",
                     "wind_mw", "solar_mw", "tie_line_mw"}
        missing = required - set(df.columns)
        if missing:
            logger.warning(f"缺少标准列（部分列可能未识别）: {missing}")

        # ── 解析时间戳 ──
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            # 丢弃无法解析的行
            bad_ts = df["timestamp"].isna().sum()
            if bad_ts > 0:
                logger.warning(f"{bad_ts} 行时间戳解析失败，已丢弃")
                df = df.dropna(subset=["timestamp"])
        else:
            logger.warning("时间戳列 'timestamp' 不存在，返回空 DataFrame")
            df["timestamp"] = pd.NaT

        # ── 数值列安全转换 ──
        numeric_cols = ["price_da", "price_rt", "load_mw",
                        "wind_mw", "solar_mw", "tie_line_mw"]
        for col in numeric_cols:
            if col in df.columns:
                orig_count = df[col].notna().sum()
                df[col] = pd.to_numeric(df[col], errors="coerce")
                damaged = orig_count - df[col].notna().sum()
                if damaged > 0:
                    ratio = damaged / max(len(df), 1) * 100
                    logger.warning(f"列 '{col}' 有 {damaged}/{len(df)} 行非数字 ({ratio:.1f}%)")

        # ── 检查空数据 ──
        if len(df) == 0:
            logger.warning("加载后数据集为空（无有效行）")
            # 仍返回空 DataFrame 以保持管道连续性
            return df

        # ── 排序 ──
        df = df.sort_values("timestamp").reset_index(drop=True)

        logger.info(f"电价数据加载完成: {len(df)} 行, "
                     f"时间范围 {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        return df

    # ── 元数据 ────────────────────────────────────────

    def get_metadata(self) -> dict:
        """
        返回数据集的元信息。

        Returns:
            dict with:
            - source:       数据来源
            - data_version: 版本标识（文件名 stem）
            - rows:         行数
            - start:        起始时间
            - end:          结束时间
            - frequency:    时间频率
            - price_da_stats: 日前价格统计描述
            - price_rt_stats: 实时价格统计描述
            - load_stats:      统调负荷统计描述
        """
        df = self.load_data()
        meta: dict = {
            "source": self._metadata_source,
            "data_version": self._metadata_version,
            "rows": len(df),
            "start": str(df["timestamp"].min()) if len(df) > 0 else "N/A",
            "end": str(df["timestamp"].max()) if len(df) > 0 else "N/A",
            "frequency": pd.infer_freq(df["timestamp"]) or "unknown" if len(df) > 0 else "unknown",
        }
        if len(df) > 0:
            meta["price_da_stats"] = {
                "min": float(df["price_da"].min()),
                "max": float(df["price_da"].max()),
                "mean": float(df["price_da"].mean()),
                "std": float(df["price_da"].std()),
                "count": int(df["price_da"].notna().sum()),
            }
            meta["price_rt_stats"] = {
                "min": float(df["price_rt"].min()),
                "max": float(df["price_rt"].max()),
                "mean": float(df["price_rt"].mean()),
                "std": float(df["price_rt"].std()),
                "count": int(df["price_rt"].notna().sum()),
            }
            meta["load_stats"] = {
                "min": float(df["load_mw"].min()),
                "max": float(df["load_mw"].max()),
                "mean": float(df["load_mw"].mean()),
                "std": float(df["load_mw"].std()),
                "count": int(df["load_mw"].notna().sum()),
            }
        return meta


# ═══════════════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════════════


def create_price_loader(data_path: str = "data/price_data.xlsx") -> PriceDataLoader:
    """
    创建 PriceDataLoader 实例的工厂函数。

    工厂模式让调用方不需要直接实例化 PriceDataLoader，
    未来如果需要切换数据源（如 CSV 文件、数据库），只需要改工厂函数内部逻辑。

    Args:
        data_path: xlsx 文件路径，默认 "data/price_data.xlsx"

    Returns:
        PriceDataLoader 实例

    Example:
        >>> loader = create_price_loader()
        >>> df = loader.load_data()
    """
    return PriceDataLoader(data_path=data_path)


# ═══════════════════════════════════════════════════════
# 内部工具函数
# ═══════════════════════════════════════════════════════


def _standardize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    标准化列名：中文/别名 → 英文标准名。

    遍历 DataFrame 的列名，对每一列尝试匹配 COLUMN_NAME_MAP 中的别名。
    如果匹配成功则重命名；如果无任何别名匹配，将该列归入 unrecognized 列表。

    Args:
        df: 原始 DataFrame（列名可能是中文或各种别名）

    Returns:
        (df_renamed, unrecognized_cols)
        - df_renamed: 列名标准化后的 DataFrame
        - unrecognized_cols: 未匹配任何别名的原始列名列表
    """
    rename_map: dict[str, str] = {}
    unrecognized: list[str] = []

    for col in df.columns:
        col_stripped = str(col).strip()
        matched = False
        for aliases, standard_name in COLUMN_NAME_MAP.items():
            if col_stripped in aliases or col_stripped.lower() in aliases:
                rename_map[col] = standard_name
                matched = True
                break
        if not matched:
            unrecognized.append(col)

    if rename_map:
        df = df.rename(columns=rename_map)
    return df, unrecognized


def _safe_float(value) -> Optional[float]:
    """安全类型转换：将值转为 float，失败返回 None。"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
