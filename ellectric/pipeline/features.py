"""
特征工程管道 — 从原始时序数据提取机器学习特征
================================================

什么是特征工程？
~~~~~~~~~~~~~~
特征工程 (Feature Engineering) 是将原始数据转换为
机器学习模型可理解的"特征"的过程。

为什么需要特征工程？
~~~~~~~~~~~~~~~~~~
XGBoost (以及所有机器学习模型) 不理解"今天是星期六"或"现在是晚上8点"。
它只理解数字。特征工程的本质是**将领域知识编码为数字**。

例如:
- "现在是几月" → month=6 (6月, 空调季)
- "是不是周末" → is_weekend=1 (工业负荷低)
- "昨天同一时刻的负荷" → lag_24h=45280 (持续法思想)

渐进式特征设计 (Progressive Feature Engineering)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
我们采用三层递进设计，每层增加复杂度:
- **Tier 1 (核心特征)**: hour, day_of_week, month, is_weekend, lag_24h
- **Tier 2 (中级特征)**: is_holiday, lag_168h
- **Tier 3 (高级特征)**: rolling_mean_24h, rolling_std_24h, hour_sin, hour_cos

这样设计的好处:
1. 初学者先用 5 个核心特征跑通管道 ✔
2. 看到效果后再添加特征，对比前后差异 ✔
3. 理解每个特征的贡献，不是黑盒调参 ✔

关键设计决策:
~~~~~~~~~~~~~
- **TimeSeriesSplit**: 时间序列专用交叉验证，保证训练数据都在测试数据之前
  （防止"用未来信息预测过去"的 look-ahead bias）
- **Scaler 封装在 forecaster 中**: 调用者不需要碰 scaler 对象
  （防止误用 fit_transform() 在全量数据上）
"""

import pandas as pd
import numpy as np
import logging

from ellectric.config import TimeConfig

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    电力负荷时序特征工程器。

    使用方式:
        >>> engineer = FeatureEngineer()
        >>> df_feat = engineer.add_tier1_features(df)  # 先加核心特征
        >>> # 验证模型有效后...
        >>> df_feat = engineer.add_tier2_features(df_feat)  # 再加中级
        >>> df_feat = engineer.add_tier3_features(df_feat)  # 最后加高级
    """

    def __init__(self):
        self._features_added = []

    def add_tier1_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加 Tier 1 核心特征（最基础，先跑通）。

        Tier 1 包含 5 个特征:
        1. hour          — 小时 (0-23)
        2. day_of_week   — 星期几 (0=周一)
        3. month         — 月份 (1-12)
        4. is_weekend    — 是否周末 (0/1)
        5. lag_24h       — 24 小时前负荷

        为什么选这 5 个？
        ~~~~~~~~~~~~~~~
        - hour/day_of_week: 捕捉日周期（凌晨低谷→中午高峰）
        - month: 捕捉季节模式（夏季制冷、冬季取暖）
        - is_weekend: 工业负荷周末明显下降
        - lag_24h: 昨天的同时刻是最好的起点（持续法思想）

        对年级数据: hour/day_of_week/month 无意义但仍保留
        （当切换到日/小时数据后这些特征立即可用）
        """
        df = df.copy()

        # 时间特征 — 从 timestamp 列提取
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["month"] = df["timestamp"].dt.month
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        # 滞后特征 — 昨天同时刻的负荷
        df["lag_24h"] = df["load_mw"].shift(TimeConfig.points_per_day)
        # bfill: 前24个没有"昨天"的点用后续值填充
        df["lag_24h"] = df["lag_24h"].bfill()

        self._features_added.append("tier1")
        logger.info(f"Tier 1 特征已添加: hour, day_of_week, month, is_weekend, lag_24h ({len(df)} 行)")
        return df

    def add_tier2_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加 Tier 2 中级特征（Tier 1 跑通后再加）。

        Tier 2:
        1. is_holiday    — 是否节假日 (0/1)
        2. lag_168h      — 168 小时前负荷（一周前同时刻）

        为什么加这些？
        ~~~~~~~~~~~~~
        - is_holiday: 节假日工业负荷断崖式下跌，不标记的话模型很难学好
        - lag_168h: 一周前的同时刻——如果今天是周三下午3点，
                    上周三下午3点的负荷也很有参考价值

        注意: 年级数据中 is_holiday 无意义（都是全年平均），
        但代码保留此特征以备日/小时级数据。
        """
        df = df.copy()

        # 节假日标记 — 使用中国法定节假日
        try:
            import holidays
            cn_holidays = holidays.China()
            df["is_holiday"] = df["timestamp"].apply(
                lambda t: 1 if t.date() in cn_holidays else 0
            )
        except ImportError:
            logger.warning("holidays 包未安装，is_holiday 设为 0")
            df["is_holiday"] = 0

        # 168 小时滞后 — 一周前同时刻
        df["lag_168h"] = df["load_mw"].shift(TimeConfig.points_per_week)
        df["lag_168h"] = df["lag_168h"].bfill()

        self._features_added.append("tier2")
        logger.info(f"Tier 2 特征已添加: is_holiday, lag_168h")
        return df

    def add_tier3_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加 Tier 3 高级特征（优化阶段使用）。

        Tier 3:
        1. rolling_mean_24h  — 过去24小时滚动均值
        2. rolling_std_24h   — 过去24小时滚动标准差
        3. hour_sin          — 小时的正弦编码
        4. hour_cos          — 小时的余弦编码

        为什么需要滚动统计？
        ~~~~~~~~~~~~~~~~~~
        - rolling_mean: 近期的平均负荷水平（消除短期波动）
        - rolling_std: 近期的负荷波动性（波动大=系统不稳定）

        为什么用 sin/cos 编码小时？
        ~~~~~~~~~~~~~~~~~~~~~~~~~~
        数值 0 (午夜) 和 23 (晚上11点) 在数学上隔得很远 (23-0=23)，
        但实际上它们是相邻的时间! 用 sin/cos 编码能捕获这种周期性:
        - hour_sin = sin(2π × hour / 24)
        - hour_cos = cos(2π × hour / 24)
        这样 23:00 和 00:00 在向量空间里就是相邻的。

        这在数学上称为**循环特征编码 (Cyclic Feature Encoding)**，
        是处理周期性变量（时间、角度、季节）的标准方法。
        """
        df = df.copy()

        # 滚动统计 — 窗口 24 小时
        df["rolling_mean_24h"] = df["load_mw"].rolling(window=24, min_periods=1).mean()
        df["rolling_std_24h"] = df["load_mw"].rolling(window=24, min_periods=1).std().fillna(0)

        # 循环编码 — 将小时映射到单位圆上
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

        self._features_added.append("tier3")
        logger.info(f"Tier 3 特征已添加: rolling_mean, rolling_std, hour_sin, hour_cos")
        return df

    def get_feature_columns(self, tier: str = "tier1") -> list:
        """
        返回指定 tier 的特征列名列表。

        这很重要——模型训练时只取特征列，不包括 timestamp 和 load_mw。
        """
        feature_map = {
            "tier1": ["hour", "day_of_week", "month", "is_weekend", "lag_24h"],
            "tier2": ["hour", "day_of_week", "month", "is_weekend", "lag_24h",
                      "is_holiday", "lag_168h"],
            "tier3": ["hour", "day_of_week", "month", "is_weekend", "lag_24h",
                      "is_holiday", "lag_168h",
                      "rolling_mean_24h", "rolling_std_24h", "hour_sin", "hour_cos"],
        }
        return feature_map.get(tier, feature_map["tier1"])


def prepare_features(
    df: pd.DataFrame,
    tiers: list = None,
) -> pd.DataFrame:
    """
    便捷函数：一次性准备所有特征。

    Args:
        df: 原始 DataFrame（timestamp, load_mw）
        tiers: 要添加的特征层列表，默认 ['tier1']

    Returns:
        包含原始列 + 特征列的 DataFrame

    Example:
        >>> df_feat = prepare_features(df, tiers=['tier1', 'tier2'])
    """
    if tiers is None:
        tiers = ["tier1"]

    engineer = FeatureEngineer()
    for tier in tiers:
        if tier == "tier1":
            df = engineer.add_tier1_features(df)
        elif tier == "tier2":
            df = engineer.add_tier2_features(df)
        elif tier == "tier3":
            df = engineer.add_tier3_features(df)

    return df
