"""
山东 15min 电力数据加载器 — Shandong 15min Data Loader
=======================================================

数据来源: 山东_2024-2026_15min.csv (用户提供)
时间跨度: 2024-01-01 ~ 2026-01-14
时间粒度: 15 分钟 (96 点/日)
总行数: 745 天 × 96 点 = 71,520 行

列 (21 列):
  基础: 日期, 时刻, 是否节假日, 是否周末休息日
  预测: 直调负荷(预测), 联络线受电负荷(预测), 风电总加(预测),
        光伏总加(预测), 非市场化核电总加(预测), 自备机组总加(预测),
        地方电厂发电总加(预测)
  实际: 直调负荷(实际), 联络线受电负荷(实际), 风电总加(实际),
        光伏总加(实际), 抽蓄(实际), 地方电厂发电总加(实际),
        非市场化核电总加(实际), 自备机组总加(实际)
  价格: 日前价格, 实时价格

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 继承 DataLoader ABC，保持工厂统一性
- 扩展 schema — 21 列全部保留，下游按需取
- 日前价格 75% null → 实时价格为主要价格信号
- 预测列默认不映射到短列名，通过 include_forecasts=True 开启

字段映射 (Column Mapping)
~~~~~~~~~~~~~~~~~~~~~~~~~
  原始列 → DataFrame 列:
    日期 + 时刻        → timestamp (UTC)
    直调负荷(实际)      → load_mw
    实时价格            → rt_price
    日前价格            → da_price
    风电总加(实际)      → wind_actual_mw
    光伏总加(实际)      → solar_actual_mw
    非市场化核电总加(实际) → nuclear_actual_mw
    自备机组总加(实际)   → captive_actual_mw
    联络线受电负荷(实际) → tie_line_actual_mw
    抽蓄(实际)          → pumped_storage_mw
    地方电厂发电总加(实际) → local_gen_actual_mw
    是否节假日           → is_holiday
    是否周末休息日       → is_weekend

用法 (Usage)
~~~~~~~~~~~~
    from ellectric.pipeline.data_loader import create_loader
    loader = create_loader("shandong")
    df = loader.load_data("2024-06", "2024-08")
    print(df.shape)  # (92 × 96 = 8832, ~18)
"""

# ═════════════════════════════════════════════
# 标准库 & 第三方
# ═════════════════════════════════════════════

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

# ═════════════════════════════════════════════
# Pipeline 抽象基类
# ═════════════════════════════════════════════

from ellectric.pipeline.data_loader import DataLoader

logger = logging.getLogger(__name__)

# ── 列映射 ──

_COLUMN_MAP = {
    "日期": "date_str",
    "时刻": "time_str",
    "是否节假日": "is_holiday",
    "是否周末休息日": "is_weekend",
    # 实际值 → 优先映射
    "直调负荷(实际)": "load_mw",
    "实时价格": "rt_price",
    "日前价格": "da_price",
    "风电总加(实际)": "wind_actual_mw",
    "光伏总加(实际)": "solar_actual_mw",
    "非市场化核电总加(实际)": "nuclear_actual_mw",
    "自备机组总加(实际)": "captive_actual_mw",
    "联络线受电负荷(实际)": "tie_line_actual_mw",
    "抽蓄(实际)": "pumped_storage_mw",
    "地方电厂发电总加(实际)": "local_gen_actual_mw",
}

# 预测列 — 仅当 include_forecasts=True 时映射
_FORECAST_COLUMN_MAP = {
    "直调负荷(预测)": "load_forecast_mw",
    "联络线受电负荷(预测)": "tie_line_forecast_mw",
    "风电总加(预测)": "wind_forecast_mw",
    "光伏总加(预测)": "solar_forecast_mw",
    "非市场化核电总加(预测)": "nuclear_forecast_mw",
    "自备机组总加(预测)": "captive_forecast_mw",
    "地方电厂发电总加(预测)": "local_gen_forecast_mw",
}

# 注入常量
_INJECTED_COLUMNS = {
    "province": "shandong",
    "source": "user-provided-csv",
    "granularity": "15min",
}


# ═══════════════════════════════════════════════════════
# ShandongDataLoader
# ═══════════════════════════════════════════════════════


class ShandongDataLoader(DataLoader):
    """山东 15min 电力数据加载器。

    加载 山东_2024-2026_15min.csv 并产出标准 DataFrame。
    21 列全部保留，下游按需取列。

    Attributes:
        REQUIRED_COLUMNS: 数据合约要求列 {"timestamp", "load_mw"}
        data_path: CSV 文件路径
    """

    REQUIRED_COLUMNS = {"timestamp", "load_mw"}

    def __init__(
        self,
        data_path: str = "ellectric/data/shandong/山东_2024-2026_15min.csv",
        include_forecasts: bool = False,
    ) -> None:
        """
        Args:
            data_path: CSV 文件路径
            include_forecasts: 是否映射预测列（默认 False，节省内存）
        """
        self.data_path = Path(data_path)
        self.include_forecasts = include_forecasts
        self._metadata_source = "山东用户提供CSV"
        self._metadata_version = "shandong_2024-2026_15min_v1"

    # ── 公共接口 ──

    def load_data(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """加载山东 15min 数据。

        Args:
            start: 起始日期 (YYYY-MM-DD 或 YYYY-MM)，可选
            end: 结束日期，可选

        Returns:
            DataFrame[timestamp(UTC), load_mw, rt_price, da_price,
                       wind_actual_mw, solar_actual_mw, ...]
        """
        self._resolve_path()

        logger.info("加载山东 15min 数据: %s", self.data_path)
        df = pd.read_csv(self.data_path, encoding="utf-8-sig")

        # 列重命名
        df = df.rename(columns=_COLUMN_MAP, errors="ignore")
        if self.include_forecasts:
            df = df.rename(columns=_FORECAST_COLUMN_MAP, errors="ignore")

        # 构造 timestamp — 24:00 转换为次日 00:00
        mask_2400 = df["time_str"] == "24:00"
        df.loc[mask_2400, "time_str"] = "00:00"
        prefix = df["date_str"] + " " + df["time_str"]
        df["timestamp"] = pd.to_datetime(prefix, utc=True)
        df.loc[mask_2400, "timestamp"] += pd.Timedelta(days=1)

        # 注入常量列
        for col, val in _INJECTED_COLUMNS.items():
            df[col] = val

        # 类型转换 — 节假日标记
        if "is_holiday" in df.columns:
            df["is_holiday"] = df["is_holiday"].map({"是": 1, "否": 0})
        if "is_weekend" in df.columns:
            df["is_weekend"] = df["is_weekend"].map({"是": 1, "否": 0})

        # 时间过滤
        if start:
            df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        if end:
            df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

        # 确保数值列为 float
        numeric_cols = [
            c for c in df.columns
            if c not in ("timestamp", "date_str", "time_str",
                         "source", "province", "granularity",
                         "is_holiday", "is_weekend")
        ]
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")

        # 排序
        df = df.sort_values("timestamp").reset_index(drop=True)

        # 清理临时列
        df = df.drop(columns=["date_str", "time_str"], errors="ignore")

        # 验证合约
        self._validate(df)
        logger.info(
            "山东数据加载完成: %d 行, %d 列, %s ~ %s",
            len(df), len(df.columns),
            str(df["timestamp"].min()), str(df["timestamp"].max()),
        )
        return df

    # ── 内部 ──

    def _resolve_path(self) -> None:
        """解析 data_path，不存在时报错。"""
        if self.data_path.exists():
            return
        # 尝试项目根目录相对路径
        alt = Path("/mnt/e/Electric") / self.data_path
        if alt.exists():
            self.data_path = alt
            return
        raise FileNotFoundError(
            f"山东数据文件未找到: {self.data_path}\n"
            f"请将山东_2024-2026_15min.csv 放到 ellectric/data/shandong/ 目录下"
        )

    def _validate(self, df: pd.DataFrame) -> None:
        """验证合约列和基本完整性。"""
        # 合约检查
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            logger.warning("数据合约列缺失: %s", missing)

        # 空值检查
        nulls = df["load_mw"].isna().sum()
        if nulls > 0:
            logger.warning("load_mw 含 %d 个空值", nulls)

        rt_nulls = df["rt_price"].isna().sum() if "rt_price" in df.columns else 0
        if rt_nulls > 0:
            logger.info("rt_price 含 %d 个空值 (/ %d)", rt_nulls, len(df))

        da_nulls = df["da_price"].isna().sum() if "da_price" in df.columns else 0
        if da_nulls > 0:
            logger.info(
                "da_price 含 %d 个空值 (/ %d, %.0f%%)",
                da_nulls, len(df), 100 * da_nulls / len(df),
            )
