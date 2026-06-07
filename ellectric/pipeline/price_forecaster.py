"""
LEAR 电价预测器 — Lasso + 滞后特征 + 日历特征 + 滚动统计
==========================================================

什么是 LEAR？
~~~~~~~~~~~~~
LEAR = Lasso Estimated AutoRegressive，由 epftoolbox 论文
(Lago et al., 2021) 提出的日前电价预测标准方法。

核心思想：
1. 用大量滞后特征和日历特征构建宽特征矩阵
2. Lasso 的 L1 正则化自动筛选重要特征（稀疏解）
3. 最终模型只保留预测能力最强的几个滞后项
4. 在电力日前价格预测中，LEAR 通常优于复杂深度学习模型

Lasso 原理
~~~~~~~~~~
损失函数 = MSE + α × Σ|βᵢ|

其中 α (alpha) 控制正则化强度：
- α=0 → 普通最小二乘，可能过拟合
- α 越大 → 更多系数被压缩到零（自动特征选择）
- α 过大 → 所有系数为零（欠拟合）

为什么用 Lasso 而不是 XGBoost？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- XGBoost: 树模型，自动捕捉非线性交互，但黑盒
- Lasso: 线性模型，系数 = 边际影响，可解释性强
- 在电价预测中，LEAR 通常达到或超过复杂模型的精度
- 两者对比本身就是重要的学习目标

渐进式特征设计 (Tier 1-3)
~~~~~~~~~~~~~~~~~~~~~~~~~~
- Tier 1 (核心): 日历 + 价格滞后（快速验证管道）
- Tier 2 (中级): 引入相关变量 + 价格波动性
- Tier 3 (高级): 循环时间编码 + 价格趋势
"""

import pandas as pd
import numpy as np
import logging
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

# ── Tier 特征列名定义 ─────────────────────────────────────────
# 分层累积: tier2 = tier1 + tier2 增量; tier3 = tier1 + tier2 + tier3 增量

_TIER1_COLS = [
    "hour", "day_of_week", "month", "is_weekend",
    "lag_24h_price", "lag_168h_price",
]

_TIER2_COLS = _TIER1_COLS + [
    "lag_24h_load", "lag_24h_wind", "lag_24h_solar",
    "rolling_mean_24h_price", "rolling_std_24h_price",
]

_TIER3_COLS = _TIER2_COLS + [
    "hour_sin", "hour_cos", "price_trend_7d",
]

_FEATURE_MAP = {
    "tier1": _TIER1_COLS,
    "tier2": _TIER2_COLS,
    "tier3": _TIER3_COLS,
}


class LEARForecaster:
    """
    LEAR 电价预测器 — sklearn Lasso 实现。

    使用方法:
        >>> forecaster = LEARForecaster(alpha=0.01)
        >>> df_feat = forecaster.add_price_features(df, "tier3")
        >>> result = forecaster.train_evaluate(df_feat, "tier3")
        >>> fig = forecaster.plot_price_forecast(df_feat, result["predictions"])
        >>> forecaster.save_model("model.joblib")

    Lasso 模型特性:
        - 系数正值 → 特征增加时价格上涨
        - 系数负值 → 特征增加时价格下跌
        - 系数为零 → 该特征被 L1 正则化剔除
    """

    def __init__(
        self,
        alpha: float = 0.01,
        max_iter: int = 10000,
        random_state: int = 42,
    ) -> None:
        """
        Args:
            alpha:       L1 正则化强度 (默认 0.01)
            max_iter:    最大迭代次数 (默认 10000)
            random_state: 随机种子，保证可复现
        """
        self.alpha = alpha
        self.max_iter = max_iter
        self.random_state = random_state
        self._model = None
        self._feature_cols = None
        self._scaler = None

    # ════════════════════════════════════════════════════════════
    # 特征工程
    # ════════════════════════════════════════════════════════════

    def add_price_features(
        self,
        df: pd.DataFrame,
        tier: str = "tier1",
    ) -> pd.DataFrame:
        """
        添加电价预测特征（Tier 1-3 渐进式）。

        自动补全低 tier 缺失特征: 调用 add_price_features(df, "tier2")
        时会检查 Tier 1 特征是否存在，不存在则先添加。

        Args:
            df:   包含 timestamp, price_da 的 DataFrame
                  （Tier 2 需要 load_mw, wind_mw, solar_mw）
            tier: 特征层级 'tier1' | 'tier2' | 'tier3'

        Returns:
            新增特征列的 DataFrame（不修改原 df）
        """
        df = df.copy()

        # ── 校验必要列（至少需要 timestamp + price_da） ─────
        _validate_required_columns(df, {"timestamp", "price_da"}, "add_price_features")

        # ── 级联补齐低 tier 特征 ────────────────────────────
        if tier in ("tier1", "tier2", "tier3") and "hour" not in df.columns:
            df = self._add_tier1_price_features(df)
        if tier in ("tier2", "tier3") and "lag_24h_load" not in df.columns:
            df = self._add_tier2_price_features(df)
        if tier == "tier3" and "hour_sin" not in df.columns:
            df = self._add_tier3_price_features(df)

        # ── 添加目标 tier（如果之前的级联未包含） ──────────
        if tier == "tier1" and "hour" not in df.columns:
            df = self._add_tier1_price_features(df)
        elif tier == "tier2" and "lag_24h_load" not in df.columns:
            df = self._add_tier2_price_features(df)
        elif tier == "tier3" and "hour_sin" not in df.columns:
            df = self._add_tier3_price_features(df)

        logger.info(
            f"price_features({tier}) 完成: {len(df)} 行, "
            f"{len(self.get_feature_columns(tier))} 个特征"
        )
        return df

    def _add_tier1_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加 Tier 1 核心特征 (6 个): 日历特征 + 价格滞后。"""
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["month"] = df["timestamp"].dt.month
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["lag_24h_price"] = df["price_da"].shift(24).bfill()
        df["lag_168h_price"] = df["price_da"].shift(168).bfill()
        logger.info("Tier 1 特征: hour, day_of_week, month, is_weekend, lag_24h_price, lag_168h_price")
        return df

    def _add_tier2_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加 Tier 2 中级特征 (+5 = 11 个): 相关变量滞后 + 滚动统计。"""
        _validate_required_columns(
            df, {"load_mw", "wind_mw", "solar_mw"}, "_add_tier2_price_features"
        )
        df["lag_24h_load"] = df["load_mw"].shift(24).bfill()
        df["lag_24h_wind"] = df["wind_mw"].shift(24).bfill()
        df["lag_24h_solar"] = df["solar_mw"].shift(24).bfill()
        df["rolling_mean_24h_price"] = df["price_da"].rolling(24, min_periods=1).mean()
        df["rolling_std_24h_price"] = (
            df["price_da"].rolling(24, min_periods=1).std().fillna(0)
        )
        logger.info("Tier 2 特征: lag_24h_load, lag_24h_wind, lag_24h_solar, rolling_mean_24h_price, rolling_std_24h_price")
        return df

    def _add_tier3_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加 Tier 3 高级特征 (+3 = 14 个): 循环编码 + 价格趋势。"""
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["price_trend_7d"] = df["price_da"].rolling(168, min_periods=1).mean()
        logger.info("Tier 3 特征: hour_sin, hour_cos, price_trend_7d")
        return df

    def get_feature_columns(self, tier: str = "tier1") -> list:
        """
        返回指定 tier 的特征列名列表（累积）。

        - tier1: 6 列 (hour...lag_168h_price)
        - tier2: 11 列 (tier1 + lag_24h_load...rolling_std_24h_price)
        - tier3: 14 列 (tier2 + hour_sin...price_trend_7d)

        Args:
            tier: 特征层级

        Returns:
            特征列名列表
        """
        if tier not in _FEATURE_MAP:
            valid = list(_FEATURE_MAP.keys())
            logger.warning(f"未知 tier '{tier}', 回退到 tier1. 有效值: {valid}")
            tier = "tier1"
        return list(_FEATURE_MAP[tier])

    # ════════════════════════════════════════════════════════════
    # 训练与评估
    # ════════════════════════════════════════════════════════════

    def train_evaluate(
        self,
        df: pd.DataFrame,
        tier: str = "tier1",
        n_splits: int = 5,
        gap: int = 24,
    ) -> dict:
        """
        TimeSeriesSplit + StandardScaler(fit-on-train) + Lasso 训练评估。

        Args:
            df:       含特征列和目标列 (price_da) 的 DataFrame
            tier:     特征层级（特征列由 get_feature_columns 确定）
            n_splits: TimeSeriesSplit 折数
            gap:      训练/测试间隔（小时），防 look-ahead bias

        Returns:
            dict:
              - predictions:        np.ndarray  所有 fold 预测值拼接
              - actuals:            np.ndarray  对应实际值
              - metrics:            dict        {mae: float, rmse: float}
              - model:              Lasso       最后 fold 训练的模型
              - feature_importance: dict        特征系数绝对值 |βᵢ|
        """
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        from sklearn.linear_model import Lasso

        # ── 校验必要列 ──────────────────────────────────────
        _validate_required_columns(df, {"price_da"}, "train_evaluate")

        # ── 确定特征列 ──────────────────────────────────────
        feature_cols = self.get_feature_columns(tier)
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            raise ValueError(
                f"缺少特征列: {missing}。请先调用 add_price_features() 添加特征。"
            )

        X_raw = df[feature_cols].copy()
        y = df["price_da"].copy()

        # ── 处理 NaN/Inf ────────────────────────────────────
        X_raw, y = _filter_nan_inf(X_raw, y, "price_da", logger)

        # 也检查特征列中的 NaN
        nan_mask = X_raw.isna().any(axis=1) | np.isinf(X_raw).any(axis=1)
        if nan_mask.any():
            logger.warning(f"特征列含 {nan_mask.sum()} 行 NaN/Inf，已丢弃")
            X_raw = X_raw[~nan_mask]
            y = y[~nan_mask]

        # ── 检查数据量 ──────────────────────────────────────
        if len(X_raw) < n_splits + gap + 10:
            raise ValueError(
                f"数据量不足: {len(X_raw)} 行 (至少需要 {n_splits + gap + 10} 行 "
                f"才能进行 {n_splits}-fold TimeSeriesSplit, gap={gap})"
            )

        self._feature_cols = feature_cols
        tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)

        all_predictions = []
        all_actuals = []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X_raw)):
            X_train_raw = X_raw.iloc[train_idx]
            X_test_raw = X_raw.iloc[test_idx]
            y_train = y.iloc[train_idx]
            y_test = y.iloc[test_idx]

            # CRITICAL: Scaler fit on TRAIN only
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train_raw)
            X_test = scaler.transform(X_test_raw)
            self._scaler = scaler  # save last fold's scaler for predict()

            model = Lasso(
                alpha=self.alpha,
                max_iter=self.max_iter,
                random_state=self.random_state,
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            all_predictions.extend(y_pred.tolist())
            all_actuals.extend(y_test.tolist())

            fold_mae = mean_absolute_error(y_test, y_pred)
            logger.info(
                f"  Fold {fold + 1}: MAE={fold_mae:.2f}, "
                f"训练 {len(train_idx)} 行 → 测试 {len(test_idx)} 行"
            )

        predictions = np.array(all_predictions)
        actuals = np.array(all_actuals)

        mae = mean_absolute_error(actuals, predictions)
        rmse = float(np.sqrt(mean_squared_error(actuals, predictions)))

        # Lasso 特征重要性 = 系数绝对值
        importance = {
            name: abs(coef)
            for name, coef in zip(self._feature_cols, model.coef_)
        }

        # 检查零系数
        nonzero = sum(1 for v in importance.values() if v > 0)
        if nonzero == 0:
            logger.warning(
                "Lasso 所有系数为零（alpha 过大或数据异常）。"
                "请检查特征数据或降低 alpha 值。"
            )

        self._model = model

        result = {
            "predictions": predictions,
            "actuals": actuals,
            "metrics": {"mae": mae, "rmse": rmse},
            "model": model,
            "feature_importance": importance,
        }

        logger.info(f"LEAR 训练完成: MAE={mae:.2f}, RMSE={rmse:.2f}")
        return result

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        用训练好的模型预测。

        Args:
            X: 特征 DataFrame (必须包含 train_evaluate 时的所有特征列)

        Returns:
            预测值数组
        """
        if self._model is None:
            raise RuntimeError("模型尚未训练。请先调用 train_evaluate()。")

        missing = [c for c in self._feature_cols if c not in X.columns]
        if missing:
            raise ValueError(
                f"输入数据缺少特征列: {missing}。请确保包含 {self._feature_cols}。"
            )

        X_scaled = X[self._feature_cols].copy()
        if self._scaler is not None:
            X_scaled = pd.DataFrame(
                self._scaler.transform(X_scaled),
                columns=self._feature_cols,
                index=X_scaled.index,
            )
        return self._model.predict(X_scaled)

    # ════════════════════════════════════════════════════════════
    # 模型持久化
    # ════════════════════════════════════════════════════════════

    def save_model(self, path: str) -> None:
        """
        持久化模型到磁盘 (joblib)。

        Args:
            path: 保存路径（.joblib 或 .pkl）
        """
        import joblib

        if self._model is None:
            raise RuntimeError("模型尚未训练。请先调用 train_evaluate()。")
        joblib.dump(
            {"model": self._model, "feature_cols": self._feature_cols, "scaler": self._scaler},
            path,
        )
        logger.info(f"LEAR 模型已保存到 {path}")

    def load_model(self, path: str) -> None:
        """
        从磁盘加载模型 (joblib)。

        Args:
            path: 模型文件路径（.joblib 或 .pkl）
        """
        import joblib

        data = joblib.load(path)
        self._model = data["model"]
        self._feature_cols = data["feature_cols"]
        self._scaler = data.get("scaler", None)
        logger.info(f"LEAR 模型已从 {path} 加载")

    # ════════════════════════════════════════════════════════════
    # 可视化
    # ════════════════════════════════════════════════════════════

    def plot_price_forecast(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,
        title: str = "LEAR 电价预测 vs 实际",
    ) -> go.Figure:
        """
        绘制预测对比图：实际 vs 预测叠加 + 误差分布直方图。

        与 Phase 1 XGBoost plot_forecast 同风格。

        Args:
            df:          含 timestamp, price_da 的 DataFrame
            predictions: 预测值数组
            title:       图表标题

        Returns:
            plotly Figure 对象
        """
        actuals = df["price_da"].values[-len(predictions):]
        errors = actuals - predictions

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("实际 vs 预测（LEAR）", "预测误差分布"),
            row_heights=[0.6, 0.4],
        )

        fig.add_trace(
            go.Scatter(
                x=df["timestamp"].values[-len(predictions):],
                y=actuals,
                mode="lines",
                name="实际价格",
                line=dict(color="#1f77b4", width=2),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"].values[-len(predictions):],
                y=predictions,
                mode="lines",
                name="LEAR 预测",
                line=dict(color="#ff7f0e", width=1.5, dash="dash"),
            ),
            row=1, col=1,
        )

        fig.add_trace(
            go.Histogram(
                x=errors,
                nbinsx=30,
                name="误差分布",
                marker=dict(color="#2ca02c"),
            ),
            row=2, col=1,
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=18)),
            height=700,
            hovermode="x unified",
            showlegend=True,
        )
        fig.update_xaxes(title_text="时间", row=1, col=1)
        fig.update_xaxes(title_text="预测误差 (元/MWh)", row=2, col=1)
        fig.update_yaxes(title_text="价格 (元/MWh)", row=1, col=1)
        fig.update_yaxes(title_text="频次", row=2, col=1)

        return fig

    def plot_coefficients(
        self,
        top_n: int = 15,
        title: str = "LEAR 特征系数 (Lasso L1 正则化)",
    ) -> go.Figure:
        """
        绘制 Lasso 特征系数条状图。

        系数绝对值 = 特征对价格的边际影响。
        - 正系数 (蓝色): 特征值 ↑ → 价格 ↑
        - 负系数 (红色): 特征值 ↑ → 价格 ↓
        - 未显示的特征: 系数为零（被 L1 正则化剔除）

        Args:
            top_n: 显示系数绝对值最大的 top N 个特征
            title: 图表标题

        Returns:
            plotly Figure 对象
        """
        if self._model is None or self._feature_cols is None:
            raise RuntimeError("模型尚未训练。请先调用 train_evaluate()。")

        coefs = self._model.coef_
        names = self._feature_cols

        # 按系数绝对值排序，取 top N
        sorted_idx = np.argsort(np.abs(coefs))[::-1][:top_n]
        top_names = [names[i] for i in sorted_idx]
        top_coefs = [coefs[i] for i in sorted_idx]
        colors = ["#1f77b4" if c >= 0 else "#d62728" for c in top_coefs]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=top_names,
                y=top_coefs,
                marker_color=colors,
                name="特征系数",
                text=[f"{c:.2f}" for c in top_coefs],
                textposition="outside",
            )
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            height=500,
            xaxis=dict(title="特征", tickangle=45),
            yaxis=dict(title="系数值"),
            hovermode="x unified",
            showlegend=False,
        )

        return fig


# ════════════════════════════════════════════════════════════════
# 内部辅助函数
# ════════════════════════════════════════════════════════════════


def _validate_required_columns(
    df: pd.DataFrame,
    required: set,
    context: str = "",
) -> None:
    """校验 DataFrame 包含必要列，缺失则抛出 ValueError。"""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{context}] 缺少必要列: {missing}。"
            f" 当前列: {list(df.columns)}"
        )


def _filter_nan_inf(
    X: pd.DataFrame,
    y: pd.Series,
    target_name: str = "price_da",
    logger_obj: logging.Logger = None,
) -> tuple:
    """
    过滤目标变量中的 NaN/Inf 行。

    Returns:
        (X_filtered, y_filtered)
    """
    if logger_obj is None:
        logger_obj = logger

    bad_mask = y.isna() | np.isinf(y)
    n_bad = bad_mask.sum()
    if n_bad > 0:
        logger_obj.warning(
            f"{target_name} 含 {n_bad} 行 ({n_bad / len(y) * 100:.1f}%) "
            f"NaN/Inf 值，已丢弃"
        )
        X = X[~bad_mask]
        y = y[~bad_mask]

    return X, y
