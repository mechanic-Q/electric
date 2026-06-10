"""
电力数据加载器 — 中国电力市场数据接入层
===========================================

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DataLoader 是一个**抽象基类**，定义了电力数据加载的标准接口。
这样做的好处是：无论数据来源是什么（API、CSV 文件、数据库），
下游的清洗、特征工程、预测代码**完全不需要修改**。

这就是面向对象设计的**依赖倒置原则 (Dependency Inversion Principle)**：
高层模块（预测模型）不依赖低层模块（数据获取），两者都依赖抽象接口。

数据源架构 (Data Source Architecture)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

     ┌──────────────────────────────────────┐
     │         DataLoader (抽象基类)          │
     │  load_data() → pd.DataFrame           │
     │  列: timestamp, load_mw, region       │
     └──────────────┬───────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────┐       ┌──────────────────┐
│OWIDChinaLoader│       │ChineseDataLoader │
│ (自动拉取年级)  │       │ (手动日/小时数据)  │
│ ourworldindata │       │ data/xxx.csv     │
└───────────────┘       └──────────────────┘

为什么选择 OWID 数据？
~~~~~~~~~~~~~~~~~~~~~
Our World in Data (OWID) 是一个**完全开源、自动更新**的全球能源数据库。
它整合了 Ember、EIA、IEA 等多个权威数据源。
对中国来说，它提供了 2000-2025 年的年度发电量、用电量数据，
虽然粒度是年级的，但作为学习的起点有以下优势：

1. **自动获取** — 一行代码拉取，不需要手动下载
2. **可复现** — 数据版本固定（GitHub raw URL），结果一致
3. **真实数据** — 来自中国官方统计来源，不是模拟数据
4. **多维度** — 总发电、煤电、太阳能、风电各自独立列

模块职责 (Module Responsibilities)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- DataLoader          : 抽象接口，定义 load_data() 签名
- OWIDChinaLoader     : 从 OWID GitHub raw CSV 自动拉取中国年数据
- ChineseDataLoader   : 加载手动下载的日/小时级本地 CSV/Parquet 文件
- create_loader()     : 工厂函数，根据参数自动选择加载器
"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime, timezone
import pandas as pd
import urllib.request
import urllib.error
import io
import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# OWID 能源数据集的多级 URL
# 优先级 1: OWID 官方 CDN（国内更稳定）
# 优先级 2: GitHub raw（备用）
# 这个 CSV 大约 25MB，包含全球所有国家的能源数据
# 我们只过滤 iso_code == 'CHN'（中国）的行
OWID_CDN_URL = (
    "https://owid-public.owid.io/data/energy/"
    "owid-energy-data.csv"
)
OWID_GITHUB_URL = (
    "https://raw.githubusercontent.com/owid/energy-data/"
    "master/owid-energy-data.csv"
)
# 保留旧常量以兼容外部引用
OWID_ENERGY_CSV_URL = OWID_GITHUB_URL

# 我们关心的列（从 OWID 100+ 列中筛选）
OWID_COLUMNS_OF_INTEREST = {
    "year": "year",
    "electricity_generation": "generation_twh",
    "electricity_demand": "demand_twh",
    "coal_electricity": "coal_twh",
    "gas_electricity": "gas_twh",
    "solar_electricity": "solar_twh",
    "wind_electricity": "wind_twh",
    "hydro_electricity": "hydro_twh",
    "nuclear_electricity": "nuclear_twh",
    "per_capita_electricity": "per_capita_kwh",
}


# ═══════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════


class DataLoader(ABC):
    """
    电力数据加载器抽象基类。

    所有数据加载器必须实现 load_data() 方法，
        返回一个包含 timestamp、load_mw 列的标准 DataFrame。

    为什么用抽象基类（ABC）？
    ~~~~~~~~~~~~~~~~~~~~~~~~
    ABC 强制子类实现特定方法。如果 ChineseDataLoader 忘了实现
    load_data()，Python 会在**实例化时**就报错，而不是在运行时才发现。
    这叫"尽早失败 (Fail Fast)"原则。
    """

    @abstractmethod
    def load_data(self, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
        """
        加载电力数据。

        Args:
            start: 开始日期，格式 'YYYY-MM-DD'（可选）
            end:   结束日期，格式 'YYYY-MM-DD'（可选）

        Returns:
            DataFrame，列必须包含:
            - timestamp: 时间戳 (datetime64[ns, UTC])
            - load_mw:   负荷值 (float64, 单位 MW 或等效)
            - region:    区域标识 (str, 可选)
        """
        ...

    def get_metadata(self) -> dict:
        """
        返回数据集的元信息。

        Returns:
            dict with:
            - source:       数据来源
            - data_version: 数据版本标识
            - rows:         行数
            - start:        起始时间
            - end:          结束时间
            - frequency:    时间频率
        """
        df = self.load_data()
        return {
            "source": getattr(self, "_metadata_source", "unknown"),
            "data_version": getattr(self, "_metadata_version", "unknown"),
            "rows": len(df),
            "start": str(df["timestamp"].min()),
            "end": str(df["timestamp"].max()),
            "frequency": pd.infer_freq(df["timestamp"]) or "unknown",
        }


# ═══════════════════════════════════════════════════════
# OWID 中国年数据自动加载器
# ═══════════════════════════════════════════════════════


class OWIDChinaLoader(DataLoader):
    """
    从 Our World in Data 自动拉取中国电力年度数据。

    三级回退策略 (Fallback Chain)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. OWID 官方 CDN (owid-public.owid.io) — 优先，国内更稳定，15s 超时
    2. GitHub raw (raw.githubusercontent.com) — 备用，30s 超时
    3. 本地 Parquet 缓存 — 兜底，网络全断也能用上次数据

    缓存策略 (Cache Strategy)
    ~~~~~~~~~~~~~~~~~~~~~~~~
    每次从网络成功拉取后，自动写入 ellectric/data/owid_china_cache.parquet。
    调用 load_data(refresh=True) 可跳过缓存强制拉取。

    实现细节 (Implementation)
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    - 流式 CSV 解析（~25MB 文件不加载到内存）
    - csv.DictReader 逐行过滤 iso_code == 'CHN' + year >= 2000
    - TWh → 日均 MW 转换（_twh_to_daily_mw）
    - 优先级: 用电量(demand) > 发电量(generation)
    """

    # ── 拉取链路配置 ──

    # 多级数据源 URL（按优先级排列）
    _FETCH_SOURCES = [
        ("OWID CDN", OWID_CDN_URL, 15),
        ("GitHub raw", OWID_GITHUB_URL, 30),
    ]

    # 本地缓存路径
    CACHE_DIR = Path("ellectric/data")
    CACHE_FILE = Path("ellectric/data/owid_china_cache.parquet")

    _metadata_source = "OWID"
    _metadata_version = "owid china (multi-source)"

    # ═══════════════════════════════
    # 公开接口
    # ═══════════════════════════════

    def load_data(
        self, start: Optional[str] = None, end: Optional[str] = None,
        refresh: bool = False
    ) -> pd.DataFrame:
        """
        从 OWID 加载中国电力年数据（三级回退 + 缓存）。

        Args:
            start:   开始日期 'YYYY-MM-DD'（可选）
            end:     结束日期 'YYYY-MM-DD'（可选）
            refresh: True 跳过缓存强制从网络拉取

        Returns:
            DataFrame[timestamp, load_mw, year, generation_twh, ...]
        """
        df = None
        used_source = None

        # ── 路径 1+2: 尝试网络拉取 ──
        if not refresh:
            # 非 refresh 模式：先尝试网络，失败才用缓存
            used_source, df = self._try_fetch_chain()

            if df is not None:
                # 网络拉取成功 → 写缓存
                try:
                    self._save_cache(df)
                except Exception as e:
                    logger.warning(f"缓存写入失败（不影响数据返回）: {e}")

        if df is None and not refresh:
            # ── 路径 3: 本地缓存兜底 ──
            logger.warning("网络源均不可用，尝试本地缓存")
            try:
                df = self._load_from_cache()
                used_source = "本地缓存"
            except FileNotFoundError:
                pass

        if df is None and refresh:
            # refresh 模式：强制走网络
            used_source, df = self._try_fetch_chain()

        if df is None:
            raise RuntimeError(
                "OWID 数据全部不可用 —— "
                "CDN 和 GitHub 拉取均失败，且本地缓存不存在。\n"
                "请检查网络连接，或手动下载 OWID CSV 放入 data/ 目录。"
            )

        # ── 时间范围过滤 ──
        if start:
            df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        if end:
            df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

        # 更新版本信息
        self._metadata_version = (
            f"{used_source} @ {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )

        logger.info(
            f"OWID 中国数据加载完成: {len(df)} 行 "
            f"(年份 {df['year'].min()}-{df['year'].max()}, 来源: {used_source})"
        )
        return df

    # ═══════════════════════════════
    # 内部：网络拉取
    # ═══════════════════════════════

    def _try_fetch_chain(self) -> tuple[Optional[str], Optional[pd.DataFrame]]:
        """
        按优先级依次尝试从 OWID_CDN_URL → OWID_GITHUB_URL 拉取数据。

        Returns:
            (source_label, DataFrame) — 成功时 source_label 非空；
            全部失败返回 (None, None)。
        """
        for label, url, timeout in self._FETCH_SOURCES:
            try:
                df = self._fetch_from_url(url, timeout)
                logger.info(f"OWID 数据拉取成功（来源: {label}）")
                return label, df
            except Exception as e:
                logger.warning(f"{label} 不可用: {e}")

        return None, None

    def _fetch_from_url(self, url: str, timeout: int) -> pd.DataFrame:
        """
        从指定 URL 流式拉取 OWID CSV，过滤中国数据。

        Args:
            url:     CSV 文件 URL
            timeout: HTTP 超时秒数

        Returns:
            解析后的 DataFrame

        Raises:
            urllib.error.URLError: 网络不可达
            ValueError: 数据格式异常
        """
        logger.info(f"正在拉取 OWID 数据 ({url[:60]}...)")

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Ellectric/1.0"}
        )
        response = urllib.request.urlopen(req, timeout=timeout)

        reader = csv.DictReader(io.TextIOWrapper(response, "utf-8"))

        rows = []
        for row in reader:
            if row.get("iso_code") != "CHN":
                continue
            year = int(row.get("year", 0))
            if year < 2000:
                continue

            gen = _safe_float(row.get("electricity_generation"))
            demand = _safe_float(row.get("electricity_demand"))
            solar = _safe_float(row.get("solar_electricity"))
            wind = _safe_float(row.get("wind_electricity"))
            coal = _safe_float(row.get("coal_electricity"))

            if gen is None:
                continue

            rows.append({
                "timestamp": pd.Timestamp(f"{year}-07-01", tz="UTC"),
                "year": year,
                "load_mw": _twh_to_daily_mw(demand or gen),
                "generation_twh": gen,
                "demand_twh": demand,
                "solar_twh": solar,
                "wind_twh": wind,
                "coal_twh": coal,
                "region": "中国",
                "source": "OWID",
            })

        response.close()

        if not rows:
            raise ValueError("未找到中国数据（iso_code='CHN' 行为空）")

        df = pd.DataFrame(rows)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    # ═══════════════════════════════
    # 内部：本地缓存
    # ═══════════════════════════════

    def _load_from_cache(self) -> pd.DataFrame:
        """从本地 Parquet 缓存加载数据。缓存不存在时 raise FileNotFoundError。"""
        if not self.CACHE_FILE.exists():
            raise FileNotFoundError(
                f"本地缓存不存在: {self.CACHE_FILE}\n"
                f"请确保至少成功拉取过一次 OWID 数据，缓存会自动生成。"
            )
        df = pd.read_parquet(self.CACHE_FILE)
        logger.info(f"从本地缓存加载: {len(df)} 行")
        return df

    def _save_cache(self, df: pd.DataFrame) -> None:
        """保存 DataFrame 到本地 Parquet 缓存。"""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df_with_version = df.copy()
        df_with_version["data_version"] = (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        df_with_version.to_parquet(self.CACHE_FILE, index=False)
        logger.info(f"OWID 数据已缓存: {self.CACHE_FILE} ({len(df)} 行)")


# ═══════════════════════════════════════════════════════
# 中国手动数据加载器（日级/小时级）
# ═══════════════════════════════════════════════════════


class ChineseDataLoader(DataLoader):
    """
    加载手动下载的中国电力日级/小时级数据。

    设计意图:
    ~~~~~~~~~
    中国地方平台的电力数据需要手动浏览器下载（无法自动爬取）。
    你从和鲸社区、阿里天池或地方开放平台下载 CSV/Excel 后，
    放到 data/ 目录下，这个 Loader 就会自动加载。

    支持格式:
    ~~~~~~~~
    - CSV: 包含 timestamp + load_mw 列
    - Excel (.xlsx): 同上
    - Parquet: 同上（推荐，读写更快）

    为什么支持多种格式？
    ~~~~~~~~~~~~~~~~~~~
    pandas 的 read_csv / read_excel / read_parquet 会自动
    检测格式。我们用 try/except 依次尝试，保证最大兼容性。
    """

    def __init__(self, data_path: str):
        """
        Args:
            data_path: 数据文件的路径（相对于项目根目录或绝对路径）
                       例如: 'data/guangdong_daily_2023.csv'
        """
        self.data_path = Path(data_path)
        self.data_version = self.data_path.stem
        self._metadata_source = f"local ({self.data_path.name})"
        self._metadata_version = self.data_version

    def load_data(self, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
        """
        加载本地中国电力数据文件。

        会自动检测格式（CSV/Excel/Parquet），解析 timestamp 列，
        标准化列名，统一时区为 UTC。
        """
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"数据文件未找到: {self.data_path}\n"
                f"请参考 docs/chinese-electricity-data-guide.md 获取中国电力数据。\n"
                f"文件放到 data/ 目录后重新运行。"
            )

        logger.info(f"加载中国本地数据: {self.data_path}")

        # 自动检测格式 — pandas 可以根据扩展名和文件内容自动选择引擎
        suffix = self.data_path.suffix.lower()
        if suffix == ".parquet":
            df = pd.read_parquet(self.data_path)
        elif suffix in (".xlsx", ".xls"):
            df = pd.read_excel(self.data_path)
        else:
            df = pd.read_csv(self.data_path)

        # 标准化列名 — 支持各种可能的命名
        df = _standardize_columns(df)

        # 解析时间戳 — pandas 很智能，能自动识别大多数日期格式
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        # 时间范围过滤
        if start:
            df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        if end:
            df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

        df = df.sort_values("timestamp").reset_index(drop=True)
        logger.info(f"本地数据加载完成: {len(df)} 行")
        return df

    def load_hourly_demand(self, start: Optional[str] = None, end: Optional[str] = None) -> pd.Series:
        """
        加载每小时的需求负荷序列（按 timestamp 索引，仅 load_mw）。

        这是 load_data() 的便捷封装，直接返回模型可用的 Series。
        """
        df = self.load_data(start=start, end=end)
        return df.set_index("timestamp")["load_mw"]


# ═══════════════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════════════


def create_loader(source: str = "owid", **kwargs) -> DataLoader:
    """
    创建数据加载器的工厂函数。

    工厂模式 (Factory Pattern) 的好处：
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    你不需要知道具体用哪个类，只需要告诉工厂"我要什么类型的数据"。
    这在配置驱动的系统中非常有用——改个字符串就切换数据源。

    Args:
        source: 数据源类型
            - "owid"   : OWID 中国年级数据（自动拉取，三级回退）
            - "manual" : 手动下载的日/小时数据
            - "file"   : 同 manual，传 kwarg data_path
            - "ember"  : Ember Climate 中国小时级数据（探索性）

    Returns:
        对应的 DataLoader 实例

    Example:
        >>> loader = create_loader("owid")
        >>> df = loader.load_data()

        >>> loader = create_loader("manual", data_path="data/guangdong_2023.csv")
        >>> df = loader.load_data(start="2023-01-01", end="2023-12-31")

        >>> loader = create_loader("ember")
        >>> df = loader.load_data(start="2024-01-01", end="2024-12-31")
    """
    if source == "owid":
        return OWIDChinaLoader()
    elif source in ("manual", "file"):
        data_path = kwargs.get("data_path")
        if not data_path:
            raise ValueError("manual/file 模式需要指定 data_path 参数")
        return ChineseDataLoader(data_path=data_path)
    elif source == "ember":
        # 延迟导入 — EmberLoader 是可选模块
        from ellectric.pipeline.ember_loader import EmberLoader
        return EmberLoader()
    else:
        raise ValueError(f"未知数据源: {source}. 可选: 'owid', 'manual', 'file', 'ember'")


# ═══════════════════════════════════════════════════════
# 内部工具函数
# ═══════════════════════════════════════════════════════


def _safe_float(value: str) -> Optional[float]:
    """安全地将字符串转为 float，失败返回 None。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _twh_to_daily_mw(twh: float) -> float:
    """
    将 TWh/年 转换为日均 MW。

    转换公式:
      daily_mw = twh * 10^6 / 365

    解释:
    - 1 TWh = 10^6 MWh (太瓦时 → 兆瓦时，乘以一百万)
    - 一年有 365 天
    - 所以日均负荷 = 总用电量(TWh) × 1,000,000 / 365

    Example: 2024 年中国用电量约 10,070 TWh
      → daily_mw = 10,070 × 10^6 / 365 ≈ 27,589 MW
      （即全中国日均用电功率约 2,758 万千瓦，符合常识）
    """
    return twh * 1_000_000 / 365


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化列名：把各种可能的命名统一为内部标准名称。

    为什么需要这个？
    ~~~~~~~~~~~~~~~
    不同平台的数据列名不一致：
    - 有的用 '日期'/'时间'/'Datetime'
    - 有的用 '负荷'/'Load'/'负荷(MW)'/'demand'
    我们在这一步统一为 timestamp / load_mw。

    技术说明：
    这是 ETL 管道中的 'Transform' 步骤。
    ETL = Extract (提取) → Transform (转换) → Load (加载)
    """
    # 时间列的标准名称映射
    time_aliases = {
        "timestamp", "datetime", "date", "time", "日期", "时间",
        "utc_timestamp", "utc_time", "Datetime", "Time",
    }
    # 负荷列的标准名称映射
    load_aliases = {
        "load_mw", "load", "demand", "power", "负荷", "用电量",
        "load_mwh", "demand_mw", "power_mw", "Load (MW)", "Load",
        "负荷(MW)", "用电负荷",
    }

    rename_map = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in time_aliases:
            rename_map[col] = "timestamp"
        elif any(alias in col_lower for alias in load_aliases):
            rename_map[col] = "load_mw"
        elif col_lower in ("region", "area", "区域", "province", "省份"):
            rename_map[col] = "region"

    if rename_map:
        df = df.rename(columns=rename_map)
    return df
