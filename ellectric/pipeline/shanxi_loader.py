"""
山西电力现货数据加载器 — 省级 15min 现货市场数据接入层
========================================================

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

本模块为山西电力交易中心 (pmos.sx.sgcc.com.cn) 零售商城公开 API
提供本地 JSON 归档数据的 loader 适配层。所有 loader 共享文件扫描、
月份过滤、UTC 时间标准化、24:00 边界处理等公共逻辑，由抽象基类
ShanxiBaseLoader 提供，子类只需实现 _standardize() 完成字段映射。

为什么用抽象基类分拆？
~~~~~~~~~~~~~~~~~~~~~
山西现货数据包含日前 (spot_da)、实时 (spot_rt)、月结算 (month_settle)
三种 JSON 格式。三者的字段名虽不同但文件组织方式和时间解析规则完全一致。
基类承载共性（文件扫描、月份过滤、UTC 化），子类仅负责字段映射，避免
三份重复代码。

类层次 (Class Hierarchy)
~~~~~~~~~~~~~~~~~~~~~~~~~

  DataLoader (ABC, data_loader.py)
       |
       └── ShanxiBaseLoader (本模块, 抽象基类)
              ├── ShanxiSpotDaLoader      (task-03)
              ├── ShanxiSpotRtLoader      (task-04)
              └── ShanxiMonthSettleLoader (task-05)
"""

from __future__ import annotations

import json
import logging
import re
from abc import abstractmethod
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ellectric.pipeline.data_loader import DataLoader

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# 模块级常量与正则
# ═══════════════════════════════════════════════════════

# 默认数据目录（相对于项目根）
_DEFAULT_DATA_DIR = Path("ellectric/data/raw/shanxi")

# 文件名中年月提取正则，如 spot_da_2024-05.json → "2024-05"
_YEAR_MONTH_RE = re.compile(r"_(\d{4}-\d{2})\.json$")


# ═══════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════


class ShanxiBaseLoader(DataLoader):
    """
    山西现货数据 loader 抽象基类。

    封装文件扫描、月份过滤、UTC 时间标准化、24:00 边界处理等公共逻辑。
    子类只需实现 _standardize() 完成原始字段到标准化列的映射。

    类属性 (Class Attributes，子类可覆盖):
        _metadata_source : 元数据来源标识
        _province        : 省份标识
        _source          : 数据源标识
        _granularity     : 数据粒度
    """

    _metadata_source: str = "shanxi-pxf-phbsx-shop"
    _province: str = "shanxi"
    _source: str = "pxf-phbsx-shop"
    _granularity: str = "15min"

    def __init__(
        self,
        data_prefix: str,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        """
        初始化 ShanxiBaseLoader。

        Args:
            data_prefix: 文件名前缀，如 "spot_da" / "spot_rt" / "month_settle"。
            data_dir:    数据目录，默认 ellectric/data/raw/shanxi。
        """
        self.data_prefix: str = data_prefix
        self.data_dir: Path = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
        self._metadata_version: str = f"{data_prefix}/local-json"

    # ── 公开接口 ──

    def load_data(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        扫描 prefix 匹配的 JSON 文件，按月份过滤并合并为标准化 DataFrame。

        控制流:
            1. glob 匹配 {prefix}_*.json（排除 _dict.json）
            2. 文件名解析 YYYY-MM
            3. 按 [start, end] 月份过滤
            4. 读 JSON → _records_from_json → _standardize（按月分片）
            5. concat + 注入基础列 (province/source/granularity) + 排序

        Args:
            start: 开始月份，接受 "YYYY-MM" 或 "YYYY-MM-DD"（取前7字符），
                   None 表示不限左边界。
            end:   结束月份，同上。

        Returns:
            DataFrame，至少含 timestamp / load_mw / province / source / granularity 列。
            无匹配数据时返回带这些列的空的 DataFrame。
        """
        # ── 步骤 1：glob 匹配 ──
        pattern = f"{self.data_prefix}_*.json"
        files: list[Path] = sorted(self.data_dir.glob(pattern))

        # ── 步骤 2：过滤 _dict.json wrapper 文件 ──
        files = [f for f in files if not f.name.endswith("_dict.json")]

        # ── 步骤 3：按月份过滤 ──
        filtered: list[tuple[Path, str]] = self._filter_files_by_month(files, start, end)

        if not filtered:
            logger.warning(
                "未匹配到任何数据 (prefix=%s, start=%s, end=%s)",
                self.data_prefix,
                start,
                end,
            )
            return self._empty_frame()

        # ── 步骤 4-5：逐月读取并标准化 ──
        parts: list[pd.DataFrame] = []
        for path, ym in filtered:
            try:
                with path.open("r", encoding="utf-8") as f:
                    raw: Union[dict, list] = json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON 解码失败: {path.name}: {exc}") from exc
            except OSError as exc:
                logger.warning("读取文件失败，跳过 %s: %s", path.name, exc)
                continue

            records: list[dict] = self._records_from_json(raw)
            if not records:
                # 单月 records 为空但文件存在 → 跳过，不污染最终结果
                continue

            df_m: pd.DataFrame = self._standardize(records, ym)

            if df_m.empty:
                continue
            parts.append(df_m)

        if not parts:
            logger.warning(
                "未匹配到任何数据 (prefix=%s, start=%s, end=%s)",
                self.data_prefix,
                start,
                end,
            )
            return self._empty_frame()

        # ── 步骤 6-8：合并 + 注入基础列 + 排序 ──
        df: pd.DataFrame = pd.concat(parts, ignore_index=True)
        df["province"] = self._province
        df["source"] = self._source
        df["granularity"] = self._granularity
        if "timestamp" in df.columns:
            df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    # ── 子类钩子 ──

    @abstractmethod
    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        """
        子类实现：将原始 records 转为标准化 DataFrame。

        返回的 DataFrame 需含 timestamp + load_mw + 业务字段列，
        不需含 province / source / granularity（基类负责注入）。

        Args:
            records:    单月 JSON 文件中的记录列表。
            year_month: 当前月份字符串 "YYYY-MM"（可用于构造默认时间戳）。

        Returns:
            标准化 DataFrame，至少含 timestamp (datetime64[ns, UTC]) 和
            load_mw (float64) 列。
        """
        ...

    def _records_from_json(self, raw: Union[dict, list]) -> list[dict]:
        """
        从 JSON 顶层结构提取 records 列表，子类可覆盖。

        默认兼容三种结构：
            - 顶层即 list
            - {"data": [...]}
            - {"records": [...]}

        Args:
            raw: json.load 输出的原始结构。

        Returns:
            records 列表；无法识别时返回空列表。
        """
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            # 优先 data 键，再退到 records 键
            data_val = raw.get("data")
            if isinstance(data_val, list):
                return data_val
            records_val = raw.get("records")
            if isinstance(records_val, list):
                return records_val
        return []

    # ── 辅助方法 ──

    def _make_timestamp(
        self,
        date_str: str,
        time_str: Optional[str] = None,
    ) -> pd.Timestamp:
        """
        将 date_str + time_str 转为 UTC pd.Timestamp。

        专为山西现货数据设计，处理以下场景：
            - "2024-05-01" + "08:15" → 2024-05-01 08:15 UTC
            - "2024-05-01" + "24:00" → 2024-05-02 00:00 UTC（跨日）
            - "2024-05" + None       → 2024-05-01 00:00 UTC

        Args:
            date_str: 日期字符串 "YYYY-MM-DD" 或 "YYYY-MM"。
            time_str: 时间字符串 "HH:MM"、"24:00" 或 None（默认 00:00）。

        Returns:
            UTC 时区的 pd.Timestamp。

        Raises:
            ValueError: 解析失败时抛出。
        """
        try:
            # 处理 24:00 跨日
            if time_str == "24:00":
                ts: pd.Timestamp = pd.Timestamp(date_str, tz="UTC") + pd.Timedelta(days=1)
                return ts

            # 构造完整日期时间字符串
            if time_str is not None:
                dt_str = f"{date_str} {time_str}"
            else:
                dt_str = date_str

            return pd.Timestamp(dt_str, tz="UTC")

        except Exception as exc:
            raise ValueError(
                f"无法解析时间戳: date={date_str}, time={time_str}"
            ) from exc

    def _filter_files_by_month(
        self,
        files: list[Path],
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[tuple[Path, str]]:
        """
        从文件名抽取 YYYY-MM，按 [start, end] 闭区间过滤。

        匹配逻辑：
            - 用 _YEAR_MONTH_RE 从文件名提取年月
            - 不匹配的文件 logger.warning 跳过
            - start/end 取前 7 字符（"YYYY-MM"），
              None 表示该侧不设限
            - 字符串比较 YYYY-MM 与字符序一致，无需转日期

        Args:
            files: 候选文件列表。
            start: 起始月份 "YYYY-MM" 或 "YYYY-MM-DD"（取前7字符）。
            end:   结束月份，同上。

        Returns:
            (Path, "YYYY-MM") 列表，按文件名排序。
        """
        # 前处理 start/end
        start_ym: Optional[str] = start[:7] if start is not None else None
        end_ym: Optional[str] = end[:7] if end is not None else None

        result: list[tuple[Path, str]] = []
        for fp in files:
            m = _YEAR_MONTH_RE.search(fp.name)
            if m is None:
                logger.warning("跳过文件: 无法解析年月 %s", fp.name)
                continue
            ym: str = m.group(1)

            # 月份范围过滤
            if start_ym is not None and ym < start_ym:
                continue
            if end_ym is not None and ym > end_ym:
                continue

            result.append((fp, ym))

        # 按文件名排序（字符序即时间序）
        result.sort(key=lambda x: x[0].name)
        return result

    def _empty_frame(self) -> pd.DataFrame:
        """
        返回带基础列名的空 DataFrame。

        保证即使无数据时下游 cleaner 也能安全调用 validate_schema()。

        Returns:
            空的 DataFrame，列含 timestamp / load_mw / province / source / granularity。
        """
        return pd.DataFrame(
            {
                "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
                "load_mw": pd.Series(dtype="float64"),
                "province": pd.Series(dtype="object"),
                "source": pd.Series(dtype="object"),
                "granularity": pd.Series(dtype="object"),
            }
        )


# ═══════════════════════════════════════════════════════
# 子类: 山西日前现货出清价 (spot_da)
# ═══════════════════════════════════════════════════════


# 复用 data_loader.py 中已有的 _safe_float 工具函数
# (放在模块底部以避免与上方 from ellectric.pipeline.data_loader import DataLoader
# 产生重复导入歧义；逻辑上等价于在文件顶部并列导入两个名字)
from ellectric.pipeline.data_loader import _safe_float  # noqa: E402


class ShanxiSpotDaLoader(ShanxiBaseLoader):
    """
    山西日前现货出清价 loader (15min × 96 点 × 50 月)。

    数据源 (Data Source)
    ~~~~~~~~~~~~~~~~~~~~
    山西电力交易中心零售商城 (pxf-phbsx-shop) `querySpotMarketClearing` API
    本地 JSON 归档，有效范围 2022-04 ~ 2026-05，每月 96 个 15min 时段。
    数据为**月度典型曲线**（不是逐日序列），故时间戳使用月份首日 +
    `endPointTime` 作为序数时间点。

    字段映射 (Field Mapping, D-002@v1, inferred)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - `endPointTime` → `timestamp`   (UTC, 15min 时段结束时间)
    - `record1`      → `da_price_a`  (日前出清价价区 A, 元/MWh, inferred)
    - `record2`      → `da_price_b`  (日前出清价价区 B, 元/MWh, inferred)
    - `load_mw`      → NaN           (价格类数据无负荷等效)

    输出列顺序固定:
        [timestamp, da_price_a, da_price_b, load_mw, province, source, granularity]
    """

    # 覆盖基类元数据标识（其余 _province / _source / _granularity 继承默认值）
    _metadata_source: str = "shanxi-spot-da"

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        """
        初始化 ShanxiSpotDaLoader。

        Args:
            data_dir: 数据目录，默认 ellectric/data/raw/shanxi。
        """
        super().__init__(data_prefix="spot_da", data_dir=data_dir)
        # 显式覆盖 _metadata_version
        # 基类按 prefix 设为 "spot_da/local-json"；子类追加 /v1 便于后续兼容管理
        self._metadata_version = "spot_da/local-json/v1"

    # ── 子类钩子实现 ──

    def _standardize(
        self,
        records: list[dict],
        year_month: str,
    ) -> pd.DataFrame:
        """
        将 spot_da 月度 records 转为标准化 DataFrame。

        控制流:
            1. 空 records → 返回 _empty_frame()
            2. 逐条解析 endPointTime / record1 / record2
            3. 非法时间戳 → WARNING + 跳过单行（不污染整月）
            4. null 价格 → 用 _safe_float 转为 NaN（保留 timestamp）
            5. 注入 load_mw=NaN + province/source/granularity
            6. 按固定列顺序返回

        说明:
            spot_da 数据为月度典型曲线（96 点 × 一个月），没有具体日期维度。
            时间戳构造方式: `{year_month}-01` 拼接 endPointTime。
            24:00 由父类 _make_timestamp 规约为次日 00:00 UTC。

        Args:
            records:    单月 JSON 的 `data` 列表。
            year_month: 当前月份字符串 "YYYY-MM"。

        Returns:
            7 列 DataFrame: timestamp / da_price_a / da_price_b /
            load_mw / province / source / granularity。
        """
        # 1. 空响应优雅退化
        if not records:
            return self._empty_frame()

        # 月度典型曲线使用月份首日作为序数日期
        date_str: str = f"{year_month}-01"

        # 2. 逐行解析
        rows: list[dict] = []
        for rec in records:
            end_point = rec.get("endPointTime")
            if end_point is None:
                logger.warning(
                    "spot_da %s: 跳过缺失 endPointTime 的记录", year_month
                )
                continue

            # 3. 时间戳解析，非法字符串跳过单行
            try:
                ts: pd.Timestamp = self._make_timestamp(date_str, end_point)
            except ValueError as exc:
                logger.warning(
                    "spot_da %s: 跳过非法时间 endPointTime=%r (%s)",
                    year_month,
                    end_point,
                    exc,
                )
                continue

            # 4. 价格字段 null 安全转换 → NaN
            rows.append(
                {
                    "timestamp": ts,
                    "da_price_a": _safe_float(rec.get("record1")),
                    "da_price_b": _safe_float(rec.get("record2")),
                }
            )

        # 整月全部坏行 → 优雅退化
        if not rows:
            return self._empty_frame()

        df: pd.DataFrame = pd.DataFrame(rows)
        if df.empty:
            return self._empty_frame()

        # 5. 注入 load_mw=NaN 与基础列
        #    注: province/source/granularity 也由父类 load_data() 注入；
        #    这里同步写入是为了让单测直接调 _standardize 时也返回 7 列完整结构。
        df["load_mw"] = float("nan")
        df["province"] = self._province
        df["source"] = self._source
        df["granularity"] = self._granularity

        # 6. 列顺序固定（便于下游/测试断言）
        return df[
            [
                "timestamp",
                "da_price_a",
                "da_price_b",
                "load_mw",
                "province",
                "source",
                "granularity",
            ]
        ]


# ═══════════════════════════════════════════════════════
# 子类: 山西实时现货电量 (spot_rt)
# ═══════════════════════════════════════════════════════


class ShanxiSpotRtLoader(ShanxiBaseLoader):
    """
    山西实时现货(spot_rt)数据加载器 (15min × 96 点 × 50 月)。

    数据源 (Data Source)
    ~~~~~~~~~~~~~~~~~~~~
    山西电力交易中心零售商城 (pxf-phbsx-shop) `queryRealTimeSpotMarketClearing`
    API 本地 JSON 归档，有效范围 2022-04 ~ 2026-05，每月 96 个 15min 时段。
    数据为**月度典型曲线**（不是逐日序列），故时间戳使用月份首日 +
    `dataTime` 作为序数时间点。

    字段推断说明 (Field Inference Disclaimer, D-003@v1, inferred)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - `rqRecord` → `rt_energy_demand` — 推断为实时需求量/日前申报量，万 MWh
    - `ssRecord` → `rt_energy_supply` — 推断为实时供应量/出清量，万 MWh
    - `load_mw`  ← rt_energy_demand   — 等效负荷（D-003@v1 决策；量纲为万 MWh，
       非 MW，下游使用方需自行交叉验证）

    输出列顺序固定:
        [timestamp, rt_energy_demand, rt_energy_supply, load_mw,
         province, source, granularity]
    """

    # 覆盖基类元数据标识（_province / _source / _granularity 继承默认值）
    _metadata_source: str = "shanxi-spot-rt"

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        """
        初始化 ShanxiSpotRtLoader。

        Args:
            data_dir: 数据目录，默认 ellectric/data/raw/shanxi。
        """
        super().__init__(data_prefix="spot_rt", data_dir=data_dir)
        # 显式覆盖 _metadata_version，对齐兄弟类命名风格
        self._metadata_version = "spot_rt/local-json/v1"

    # ── 子类钩子实现 ──

    def _standardize(
        self,
        records: list[dict],
        year_month: str,
    ) -> pd.DataFrame:
        """
        将 spot_rt 月度 records 转为标准化 DataFrame。

        控制流:
            1. 空 records → 返回 7 列名/类型完整的空 DataFrame
            2. 逐条解析 dataTime / rqRecord / ssRecord（仅 .get()，
               不原地修改传入 records）
            3. 非法时间戳 → WARNING + 跳过单行（不污染整月）
            4. null rqRecord/ssRecord → _safe_float 转为 NaN，
               记录 WARNING 日志（不中断处理）
            5. load_mw 列直接复制 rt_energy_demand 值 (D-003@v1)
            6. 注入 province / source / granularity
            7. 按固定列顺序返回

        说明:
            spot_rt 数据为月度典型曲线（96 点 × 一个月），没有具体日期维度。
            时间戳构造方式: `{year_month}-01` 拼接 dataTime。
            "24:00" 由父类 _make_timestamp 规约为次日 00:00 UTC，
            而不是 "23:59" 近似。

        Args:
            records:    单月 JSON 的 `data` 列表（本方法不会修改）。
            year_month: 当前月份字符串 "YYYY-MM"。

        Returns:
            7 列 DataFrame: timestamp / rt_energy_demand / rt_energy_supply /
            load_mw / province / source / granularity。
        """
        # 1. 空响应优雅退化
        if not records:
            return self._empty_rt_frame()

        # 月度典型曲线使用月份首日作为序数日期
        date_str: str = f"{year_month}-01"

        # 2. 逐行解析（仅 .get() 读，不修改原 records 元素或列表）
        rows: list[dict] = []
        for idx, rec in enumerate(records):
            data_time = rec.get("dataTime")
            if data_time is None:
                logger.warning(
                    "spot_rt %s: 跳过缺失 dataTime 的记录 (idx=%d)",
                    year_month,
                    idx,
                )
                continue

            # 3. 时间戳解析，非法字符串跳过单行
            try:
                ts: pd.Timestamp = self._make_timestamp(date_str, data_time)
            except ValueError as exc:
                logger.warning(
                    "spot_rt %s: 跳过非法时间 dataTime=%r (%s)",
                    year_month,
                    data_time,
                    exc,
                )
                continue

            # 4. 缺失 rqRecord/ssRecord → WARNING + NaN
            rq_raw = rec.get("rqRecord")
            ss_raw = rec.get("ssRecord")
            if rq_raw is None or ss_raw is None:
                logger.warning(
                    "spot_rt %s: record at index %d missing rqRecord/ssRecord",
                    year_month,
                    idx,
                )

            rt_demand: float = _safe_float(rq_raw)
            rt_supply: float = _safe_float(ss_raw)

            # 5. load_mw 直接复制 rt_energy_demand (D-003@v1)
            rows.append(
                {
                    "timestamp": ts,
                    "rt_energy_demand": rt_demand,
                    "rt_energy_supply": rt_supply,
                    "load_mw": rt_demand,
                }
            )

        # 整月全部坏行 → 优雅退化
        if not rows:
            return self._empty_rt_frame()

        df: pd.DataFrame = pd.DataFrame(rows)
        if df.empty:
            return self._empty_rt_frame()

        # 6. 注入 province / source / granularity
        #    注: 也由父类 load_data() 注入；这里同步写入是为了让单测
        #    直接调 _standardize 时也返回 7 列完整结构。
        df["province"] = self._province
        df["source"] = self._source
        df["granularity"] = self._granularity

        # 7. 列顺序固定（便于下游/测试断言）
        return df[
            [
                "timestamp",
                "rt_energy_demand",
                "rt_energy_supply",
                "load_mw",
                "province",
                "source",
                "granularity",
            ]
        ]

    # ── 辅助方法 ──

    def _empty_rt_frame(self) -> pd.DataFrame:
        """
        返回带 spot_rt 7 列名和类型的空 DataFrame。

        与基类 _empty_frame() (5 列) 区别：此方法面向 _standardize 的
        空输入场景，提供与正常 happy-path 一致的 7 列结构，便于单测
        直接断言列名/类型。

        Returns:
            空 DataFrame，列含 timestamp / rt_energy_demand /
            rt_energy_supply / load_mw / province / source / granularity。
        """
        return pd.DataFrame(
            {
                "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
                "rt_energy_demand": pd.Series(dtype="float64"),
                "rt_energy_supply": pd.Series(dtype="float64"),
                "load_mw": pd.Series(dtype="float64"),
                "province": pd.Series(dtype="object"),
                "source": pd.Series(dtype="object"),
                "granularity": pd.Series(dtype="object"),
            }
        )


# ═══════════════════════════════════════════════════════
# 子类: 山西月度结算电价 (month_settle)
# ═══════════════════════════════════════════════════════


def _coerce_time_point(value: object) -> Optional[int]:
    """
    将 month_settle 的 `point` 字段标准化为 0..23 小时编号。

    支持三种输入形态：
        - "HH:MM" 字符串 (如 "00:00" / "23:00") → 取冒号前部分转 int
        - 已是 int (兼容历史/未来) → 直接 int 化
        - 其它 (None / 非数字字符串 / float / bool) → None

    Args:
        value: 原始 `point` 字段值。

    Returns:
        0..23 之间的小时编号；非法值返回 None（调用方落入 pd.NA）。
    """
    if value is None:
        return None
    # bool 是 int 的子类，必须先排除（True/False 不应被当成时点）
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, str):
        head: str = value.split(":", 1)[0].strip()
        return int(head) if head.isdigit() else None
    return None


def _to_float(value: object) -> float:
    """
    安全 float 转换：None / 异常 → NaN。

    与 data_loader._safe_float 等价，但本模块为了保持 task-05 任务文档
    伪代码与实现一对一可追溯，单独命名一份本地工具函数。

    Args:
        value: 原始字段值（任意类型）。

    Returns:
        float64，None / TypeError / ValueError 时返回 NaN。
    """
    try:
        return float(value) if value is not None else float("nan")
    except (TypeError, ValueError):
        return float("nan")


class ShanxiMonthSettleLoader(ShanxiBaseLoader):
    """
    山西月度结算电价（逐日分时）加载器 — Monthly Settlement Price Loader.

    数据源 (Data Source)
    ~~~~~~~~~~~~~~~~~~~~
    山西电力交易中心零售商城 (pxf-phbsx-shop) `queryUserMonthSettlementPrice`
    API 本地 JSON 归档，覆盖范围 2018-01 ~ 2026-12（108 月），粒度为逐日
    分时（小时级，非 15min），单日 23 ~ 24 个时段。

    数据语义 (Data Semantics)
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    - 覆盖范围: 2018-01 ~ 2026-12（108 月）
    - 粒度: 逐日分时（每日 0..23 共 23~24 个时点，小时级）
    - 行数预估: 108 月 × ≈ 23.4 点 ≈ 2525 行
    - `dataTime` 为完整 ISO 日期 ("YYYY-MM-DD")，与 spot_da/spot_rt
      使用 `endPointTime`/`dataTime` 表示时段端点不同；本子类直接
      `pd.to_datetime(..., utc=True)` 解析，不调用父类 `_make_timestamp`。

    字段映射 (Field Mapping, D-002@v1)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - `dataTime`      → `timestamp`         (UTC, ISO 日期)
    - `point`         → `time_point`        (Int64 nullable, 0..23)
    - `dayPrice`      → `settle_day_price`  (float64, 元/MWh, 高频)
    - `realTimePrice` → `settle_rt_price`   (float64, 元/MWh, 高频)
    - `load_mw`       → NaN                 (合约填充，价格类数据无负荷等效)

    输出列顺序固定:
        [timestamp, time_point, settle_day_price, settle_rt_price,
         load_mw, province, source, granularity]
    """

    # 覆盖基类元数据标识（_province / _source 继承默认值，granularity 子类专属）
    _metadata_source: str = "shanxi-month-settle"
    _granularity: str = "daily-point"

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        """
        初始化 ShanxiMonthSettleLoader。

        Args:
            data_dir: 数据目录，默认 ellectric/data/raw/shanxi。
        """
        super().__init__(data_prefix="month_settle", data_dir=data_dir)
        # 显式覆盖 _metadata_version，对齐兄弟类命名风格
        self._metadata_version = "month_settle/local-json/v1"

    # ── 子类钩子实现 ──

    def _standardize(
        self,
        records: list[dict],
        year_month: str,
    ) -> pd.DataFrame:
        """
        将 month_settle 月度 records 转为标准化 DataFrame。

        控制流:
            1. 空 records → 返回 8 列名/类型完整的空 DataFrame
            2. 逐条解析 dataTime / point / dayPrice / realTimePrice
               （仅 .get() 读，不修改原 records）
            3. 非法 dataTime (None / 无法解析) → WARNING + 跳过单行
            4. point 通过 _coerce_time_point 归一为 int | None
               （后续整列 Int64 nullable，避免 NA 导致回退 object）
            5. dayPrice/realTimePrice 通过 _to_float 转换 (null → NaN)
            6. load_mw 全列 NaN (合约填充)
            7. 注入 province / source / granularity
            8. 按固定列顺序返回，行序与输入一致（不内部排序）

        Args:
            records:    单月 JSON 的 `data` 列表（本方法不会修改）。
            year_month: 当前月份字符串 "YYYY-MM"（仅用于日志/降级追踪）。

        Returns:
            8 列 DataFrame: timestamp / time_point / settle_day_price /
            settle_rt_price / load_mw / province / source / granularity。
        """
        logger.debug(
            "month_settle[%s] standardize 开始, 输入 records=%d",
            year_month,
            len(records),
        )

        # 1. 空响应优雅退化
        if not records:
            logger.debug("month_settle[%s] 无记录，返回空 DataFrame", year_month)
            return self._empty_month_settle_frame()

        # 2. 逐行解析（仅 .get() 读，不修改原 records 元素或列表）
        rows: list[dict] = []
        for idx, rec in enumerate(records):
            dt_raw = rec.get("dataTime")
            pt_raw = rec.get("point")
            day_p = rec.get("dayPrice")
            rt_p = rec.get("realTimePrice")

            # 3. 时间解析：完整 ISO 日期字符串 → UTC Timestamp
            #    None / 空串 / 非法格式 → NaT → WARNING + 跳过该行
            ts: pd.Timestamp = pd.to_datetime(dt_raw, errors="coerce", utc=True)
            if pd.isna(ts):
                logger.warning(
                    "month_settle[%s] 跳过无效 dataTime=%r (idx=%d)",
                    year_month,
                    dt_raw,
                    idx,
                )
                continue

            # 4. point 编码：'HH:MM' / int / 非法 → int | None
            tp: Optional[int] = _coerce_time_point(pt_raw)
            if tp is None and pt_raw is not None:
                logger.warning(
                    "month_settle[%s] 非法 point=%r 归一为 NA (idx=%d)",
                    year_month,
                    pt_raw,
                    idx,
                )

            # 5. 价格字段 null 安全转换 → NaN
            rows.append(
                {
                    "timestamp": ts,
                    "time_point": tp,
                    "settle_day_price": _to_float(day_p),
                    "settle_rt_price": _to_float(rt_p),
                }
            )

        # 整月全部坏行 → WARNING + 优雅退化
        if not rows:
            logger.warning(
                "month_settle[%s] 所有记录均解析失败，返回空 DataFrame", year_month
            )
            return self._empty_month_settle_frame()

        df: pd.DataFrame = pd.DataFrame(rows)
        if df.empty:
            return self._empty_month_settle_frame()

        # 6. time_point 整列 Int64 nullable（跨月 concat 时保持 dtype 稳定）
        df["time_point"] = df["time_point"].astype("Int64")

        # 7. load_mw 合约填充 + province / source / granularity 注入
        #    注: province/source/granularity 也由父类 load_data() 注入；
        #    这里同步写入是为了让单测直接调 _standardize 时也返回 8 列完整结构。
        df["load_mw"] = float("nan")
        df["province"] = self._province
        df["source"] = self._source
        df["granularity"] = self._granularity

        # 8. 列顺序固定（便于下游/测试断言）
        df = df[
            [
                "timestamp",
                "time_point",
                "settle_day_price",
                "settle_rt_price",
                "load_mw",
                "province",
                "source",
                "granularity",
            ]
        ]

        logger.debug(
            "month_settle[%s] standardize 完成, 输出 rows=%d", year_month, len(df)
        )
        return df

    # ── 辅助方法 ──

    def _empty_month_settle_frame(self) -> pd.DataFrame:
        """
        返回带 month_settle 8 列名和类型的空 DataFrame。

        与基类 _empty_frame() (5 列) 区别：此方法面向 _standardize 的
        空输入场景，提供与正常 happy-path 一致的 8 列结构，便于单测
        直接断言列名/类型。

        Returns:
            空 DataFrame，列含 timestamp / time_point / settle_day_price /
            settle_rt_price / load_mw / province / source / granularity。
        """
        return pd.DataFrame(
            {
                "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
                "time_point": pd.Series(dtype="Int64"),
                "settle_day_price": pd.Series(dtype="float64"),
                "settle_rt_price": pd.Series(dtype="float64"),
                "load_mw": pd.Series(dtype="float64"),
                "province": pd.Series(dtype="object"),
                "source": pd.Series(dtype="object"),
                "granularity": pd.Series(dtype="object"),
            }
        )


# ═══════════════════════════════════════════════════════════════════
# 数据 schema 扩展 — 5 个新子类 (data-schema-expand 变更)
# ═══════════════════════════════════════════════════════════════════


class ShanxiMonthDealLoader(ShanxiBaseLoader):
    """批发市场中长期成交 — 购方/售方按日的成交电量与价格 (inferred)."""

    _metadata_source = "shanxi-month-deal"
    _granularity = "daily"

    def __init__(self, data_dir: str | None = None) -> None:
        super().__init__(data_prefix="month_deal", data_dir=data_dir)
        self._metadata_version = "month_deal/local-json/v1"

    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        """展开 dateList/energyList/priceList 为长表."""
        if not records:
            return self._empty_deal_frame()
        rows = []
        for r in records:
            side = r.get("type", "")
            dates = r.get("dateList") or []
            energies = r.get("energyList") or []
            prices = r.get("priceList") or []
            n = min(len(dates), len(energies), len(prices))
            for i in range(n):
                try:
                    ts = pd.Timestamp(dates[i], tz="UTC")
                except Exception:
                    continue
                rows.append({
                    "timestamp": ts,
                    "deal_side": side,
                    "deal_energy_mwh": _safe_float(energies[i]),
                    "deal_price": _safe_float(prices[i]),
                })
        if not rows:
            return self._empty_deal_frame()
        df = pd.DataFrame(rows)
        df["load_mw"] = float("nan")
        df["province"] = "shanxi"
        df["source"] = "pxf-phbsx-shop"
        df["granularity"] = "daily"
        return df[["timestamp", "deal_side", "deal_energy_mwh", "deal_price", "load_mw", "province", "source", "granularity"]]

    def _empty_deal_frame(self) -> pd.DataFrame:
        return pd.DataFrame({
            "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "deal_side": pd.Series(dtype="object"),
            "deal_energy_mwh": pd.Series(dtype="float64"),
            "deal_price": pd.Series(dtype="float64"),
            "load_mw": pd.Series(dtype="float64"),
            "province": pd.Series(dtype="object"),
            "source": pd.Series(dtype="object"),
            "granularity": pd.Series(dtype="object"),
        })


class ShanxiUserTransactionLoader(ShanxiBaseLoader):
    """用户侧成交 — 市场主体按日成交电量与价格 (inferred)."""

    _metadata_source = "shanxi-user-transaction"
    _granularity = "daily"

    def __init__(self, data_dir: str | None = None) -> None:
        super().__init__(data_prefix="user_transaction", data_dir=data_dir)
        self._metadata_version = "user_transaction/local-json/v1"

    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        if not records:
            return self._empty_ut_frame()
        rows = []
        for r in records:
            member = r.get("marketMember", "")
            dates = r.get("dateList") or []
            energies = r.get("energyList") or []
            prices = r.get("priceList") or []
            n = min(len(dates), len(energies), len(prices))
            for i in range(n):
                try:
                    ts = pd.Timestamp(dates[i], tz="UTC")
                except Exception:
                    continue
                rows.append({
                    "timestamp": ts,
                    "market_member": member,
                    "deal_energy_mwh": _safe_float(energies[i]),
                    "deal_price": _safe_float(prices[i]),
                })
        if not rows:
            return self._empty_ut_frame()
        df = pd.DataFrame(rows)
        df["load_mw"] = float("nan")
        df["province"] = "shanxi"
        df["source"] = "pxf-phbsx-shop"
        df["granularity"] = "daily"
        return df[["timestamp", "market_member", "deal_energy_mwh", "deal_price", "load_mw", "province", "source", "granularity"]]

    def _empty_ut_frame(self) -> pd.DataFrame:
        return pd.DataFrame({
            "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "market_member": pd.Series(dtype="object"),
            "deal_energy_mwh": pd.Series(dtype="float64"),
            "deal_price": pd.Series(dtype="float64"),
            "load_mw": pd.Series(dtype="float64"),
            "province": pd.Series(dtype="object"),
            "source": pd.Series(dtype="object"),
            "granularity": pd.Series(dtype="object"),
        })


class ShanxiYearTradeFitLoader(ShanxiBaseLoader):
    """年度交易各标的月拟合分时价格曲线 — series_name × time_index × fit_price (inferred)."""

    _metadata_source = "shanxi-year-trade-fit"
    _granularity = "month-curve"

    def __init__(self, data_dir: str | None = None) -> None:
        super().__init__(data_prefix="year_trade_fit", data_dir=data_dir)
        self._metadata_version = "year_trade_fit/local-json/v1"

    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        if not records:
            return self._empty_series_frame("fit_price", "month-curve")
        rows = []
        for r in records:
            name = r.get("seriesName", "")
            data = r.get("seriesData") or []
            for i, v in enumerate(data):
                rows.append({
                    "series_name": name,
                    "time_index": i,
                    "fit_price": _safe_float(v),
                })
        if not rows:
            return self._empty_series_frame("fit_price", "month-curve")
        df = pd.DataFrame(rows)
        df["load_mw"] = float("nan")
        df["province"] = "shanxi"
        df["source"] = "pxf-phbsx-shop"
        df["granularity"] = "month-curve"
        return df[["series_name", "time_index", "fit_price", "load_mw", "province", "source", "granularity"]]

    def _empty_series_frame(self, value_col: str, granularity: str) -> pd.DataFrame:
        return pd.DataFrame({
            "series_name": pd.Series(dtype="object"),
            "time_index": pd.Series(dtype="Int64"),
            value_col: pd.Series(dtype="float64"),
            "load_mw": pd.Series(dtype="float64"),
            "province": pd.Series(dtype="object"),
            "source": pd.Series(dtype="object"),
            "granularity": pd.Series(dtype="object"),
        })


class ShanxiMonthSettle1Loader(ShanxiMonthSettleLoader):
    """月度统一结算点电价(2) — 字段与 month_settle 完全一致, 复用 _standardize."""

    _metadata_source = "shanxi-month-settle1"
    _granularity = "daily-point"

    def __init__(self, data_dir: str | None = None) -> None:
        # 直接调用 ShanxiBaseLoader.__init__, 跳过 ShanxiMonthSettleLoader 默认前缀
        ShanxiBaseLoader.__init__(self, data_prefix="month_settle1", data_dir=data_dir)
        self._metadata_version = "month_settle1/local-json/v1"


class ShanxiTimeDivTrendLoader(ShanxiYearTradeFitLoader):
    """分时价格浮动项历史参考值 — 与 year_trade_fit 同 seriesData 结构, 值列为 trend_value."""

    _metadata_source = "shanxi-time-div-trend"
    _granularity = "time-div"

    def __init__(self, data_dir: str | None = None) -> None:
        ShanxiBaseLoader.__init__(self, data_prefix="time_div_trend", data_dir=data_dir)
        self._metadata_version = "time_div_trend/local-json/v1"

    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        if not records:
            return self._empty_series_frame("trend_value", "time-div")
        rows = []
        for r in records:
            name = r.get("seriesName", "")
            data = r.get("seriesData") or []
            for i, v in enumerate(data):
                rows.append({
                    "series_name": name,
                    "time_index": i,
                    "trend_value": _safe_float(v),
                })
        if not rows:
            return self._empty_series_frame("trend_value", "time-div")
        df = pd.DataFrame(rows)
        df["load_mw"] = float("nan")
        df["province"] = "shanxi"
        df["source"] = "pxf-phbsx-shop"
        df["granularity"] = "time-div"
        return df[["series_name", "time_index", "trend_value", "load_mw", "province", "source", "granularity"]]
