"""
数据清洗管道 — 电力时序数据预处理
=================================

为什么需要数据清洗？
~~~~~~~~~~~~~~~~~~
电力数据来自各种不同的来源（传感器、API、手动录入），天然含有：
1. 缺失值 — 传感器故障、网络中断、节假日停机
2. 异常值 — 传感器读数错误、极端天气事件、数据录入错误
3. 时区混乱 — 来源渠道多，有的用北京时间有的用UTC

清洗后的数据是**下游所有模块的合约 (Contract)**：
特征工程、模型训练、可视化都假设数据是干净的。
如果脏数据漏下去，会导致整个管道出问题——
这叫做 Garbage-In-Garbage-Out (GIGO) 原则。

关键设计决策：IQR 异常值**只报告不删除**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
电力数据中，异常高的负荷往往是真实的：
- 夏季极端高温导致空调全开（制冷负荷峰值）
- 冬季寒潮导致取暖负荷飙升
- 重大活动/节假日导致的负荷变化
如果盲目删除这些"异常值"，你就丢掉了最有价值的信号！

这就是研究报告中强调的 "spike-as-noise" 反模式：
别把尖峰当噪声——尖峰就是信号。

处理策略:
  1. IQR 检测异常值 → 记录日志（让你知道有哪些异常）
  2. 不删除任何行 → 保留全部信号给模型学习
  3. 缺失值用前向填充 (ffill) → 电力数据有强时间连续性
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# 数据清洗后的标准 schema
# 这是 Phase 1 的数据合约 — 下游所有模块依赖此 schema
REQUIRED_COLUMNS = {"timestamp", "load_mw"}
OPTIONAL_COLUMNS = {"region", "year", "generation_twh", "demand_twh",
                    "solar_twh", "wind_twh", "coal_twh", "source"}


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗电力数据的主入口。

    处理流程 (Pipeline):
    1. 验证必需列存在 → 列缺失直接报错
    2. 缺失值处理 → 前向填充 + 后向填充
    3. IQR 异常值检测 → 记录日志但不删除
    4. 时区标准化 → 统一为 UTC

    Args:
        df: 原始 DataFrame（来自 DataLoader）

    Returns:
        清洗后的 DataFrame，schema 保证一致
    """
    df = df.copy()

    # ── 1. 验证必需列 ──────────────────────────────
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"数据缺少必需列: {missing_cols}。\n"
            f"现有列: {list(df.columns)}\n"
            f"请检查数据源格式。期望格式: CSV/Excel，包含 timestamp, load_mw 列"
        )
    logger.info(f"列验证通过: {len(df.columns)} 列, {len(df)} 行")

    # ── 2. 缺失值处理 ──────────────────────────────
    # 为什么用前向填充 (forward fill)？
    # 电力负荷有强时间连续性——上一时刻的负荷通常是下一时刻的最好估计。
    # 比填 0 或填均值靠谱得多。
    before = df["load_mw"].isna().sum()
    if before > 0:
        logger.warning(f"发现 {before} 个负荷缺失值，使用前向填充 (ffill)")
        df["load_mw"] = df["load_mw"].ffill()  # 前向填充
        df["load_mw"] = df["load_mw"].bfill()  # 后向填充（处理开头几个缺失）
        after = df["load_mw"].isna().sum()
        logger.info(f"缺失值填充: {before} → {after}")

    # ── 3. IQR 异常值检测（只报告不删除）───────────
    # IQR = Interquartile Range (四分位距)
    # Q1 = 第25百分位数, Q3 = 第75百分位数
    # IQR = Q3 - Q1
    # 异常值边界: [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
    #
    # 1.5 倍 IQR 是一个经典的经验法则 (Tukey's fences)。
    # 对于正态分布，约 0.7% 的数据落在这个范围之外。
    # 但电力负荷不是正态分布——它有明显的日/周周期和季节性波动。
    # 所以这里的"异常值"只是统计上的，不一定是错误的。
    q1 = df["load_mw"].quantile(0.25)
    q3 = df["load_mw"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outliers = df[(df["load_mw"] < lower_bound) | (df["load_mw"] > upper_bound)]
    if len(outliers) > 0:
        outlier_pct = len(outliers) / len(df) * 100
        logger.warning(
            f"检测到 {len(outliers)} 个统计异常值 ({outlier_pct:.1f}%)\n"
            f"  IQR 范围: [{lower_bound:.0f}, {upper_bound:.0f}] MW\n"
            f"  最大负荷: {df['load_mw'].max():.0f} MW\n"
            f"  最小负荷: {df['load_mw'].min():.0f} MW\n"
            f"  注意: 异常值未被删除——电力尖峰是重要信号，不是噪声。\n"
            f"        XGBoost 模型会自动学习这些尖峰模式。"
        )
    else:
        logger.info("未检测到 IQR 异常值")

    # ── 4. 时区标准化 ──────────────────────────────
    if df["timestamp"].dt.tz is None:
        # 默认假设为 UTC（如果没有时区信息）
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        logger.info("时区: 未指定 → 默认为 UTC")
    elif str(df["timestamp"].dt.tz) != "UTC":
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")
        logger.info("时区: 已转换为 UTC")

    logger.info(f"数据清洗完成: {len(df)} 行")
    return df


def validate_schema(df: pd.DataFrame) -> dict:
    """
    验证 DataFrame 的 schema 是否符合数据合约。

    这是数据管道中的"类型检查"步骤。
    类似于 TypeScript/MyPy 的类型检查，
    但在运行时验证数据而不是源代码。

    Returns:
        dict with keys:
        - valid: bool — schema 是否有效
        - issues: list[str] — 发现的问题列表
        - summary: dict — 数据概况
    """
    issues = []

    # 检查必需列
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        issues.append(f"缺少必需列: {missing}")

    # 检查数据类型
    if "timestamp" in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            issues.append("timestamp 列不是 datetime 类型")
        elif df["timestamp"].dt.tz is None:
            issues.append("timestamp 列缺少时区信息")

    if "load_mw" in df.columns:
        if not pd.api.types.is_numeric_dtype(df["load_mw"]):
            issues.append("load_mw 列不是数值类型")
        elif df["load_mw"].isna().any():
            issues.append(f"load_mw 列仍有 {df['load_mw'].isna().sum()} 个缺失值")

    # 统计概况
    summary = {
        "rows": len(df),
        "columns": list(df.columns),
        "start": str(df["timestamp"].min()) if "timestamp" in df.columns else None,
        "end": str(df["timestamp"].max()) if "timestamp" in df.columns else None,
        "load_min": float(df["load_mw"].min()) if "load_mw" in df.columns else None,
        "load_max": float(df["load_mw"].max()) if "load_mw" in df.columns else None,
    }

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "summary": summary,
    }


def detect_timezone(df: pd.DataFrame) -> str:
    """
    检测 DataFrame 的时区信息。

    Returns:
        'UTC', 'unknown', 或其他 IANA 时区名
    """
    if "timestamp" not in df.columns:
        return "unknown"
    tz = df["timestamp"].dt.tz
    if tz is None:
        return "no_timezone"
    return str(tz)


def standardize_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测并规范化时间频率。

    检查 timestamp 的实际间隔，若不均匀则通过 resample 对齐到最可能的小时间隔。
    """
    if "timestamp" not in df.columns:
        return df
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        return df

    df = df.set_index("timestamp").sort_index()
    freq = pd.infer_freq(df.index[:100])
    if freq is None:
        logger.warning("无法推断时间频率，已跳过规范化")
        return df.reset_index()
    if freq != "h" and freq != "60min":
        logger.info(f"数据频率为 {freq}，重采样为小时级 (h)")
        df = df.resample("h").mean().bfill()
    return df.reset_index()


def get_data_quality_score(df: pd.DataFrame) -> dict:
    """
    计算数据质量评分（0-100）。

    评分维度:
    - 缺失率 (40 分)
    - 时间连续性 (30 分)
    - 异常值比例 (30 分)
    """
    score = 100
    details = {}

    n = len(df)
    missing_rate = df["load_mw"].isna().sum() / n if n > 0 else 1.0
    missing_score = max(0, 40 - int(missing_rate * 100))
    score -= (40 - missing_score)
    details["missing_rate"] = f"{missing_rate:.2%}"
    details["missing_score"] = f"{missing_score}/40"

    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        gaps = df["timestamp"].diff().dropna()
        expected_gaps = gaps.mode()
        if len(expected_gaps) > 0:
            consistent_rate = (gaps == expected_gaps[0]).sum() / len(gaps)
            time_score = int(consistent_rate * 30)
            score -= (30 - time_score)
            details["time_consistency"] = f"{consistent_rate:.2%}"
            details["time_score"] = f"{time_score}/30"

    q1 = df["load_mw"].quantile(0.25)
    q3 = df["load_mw"].quantile(0.75)
    iqr = q3 - q1
    if iqr > 0:
        outlier_rate = ((df["load_mw"] < q1 - 1.5 * iqr) | (df["load_mw"] > q3 + 1.5 * iqr)).sum() / n
        outlier_score = max(0, 30 - int(outlier_rate * 100))
        score -= (30 - outlier_score)
        details["outlier_rate"] = f"{outlier_rate:.2%}"
        details["outlier_score"] = f"{outlier_score}/30"

    return {"quality_score": score, "details": details}
