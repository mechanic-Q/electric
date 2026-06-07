"""
预测引擎 — 负荷预测与盈亏计算
==============================

本模块提供两种预测方法:
1. **持续法 (Persistence Forecast)** — 最简单的基线模型
2. **P&L 计算** — 将预测转化为模拟交易的盈亏

为什么先做持续法预测？
~~~~~~~~~~~~~~~~~~~~
在机器学习领域，"基线模型" (Baseline Model) 是用来衡量
后续复杂模型是否真正有效的参照物。

如果 XGBoost 的 MAE 是 500MW，但持续法的 MAE 是 510MW，
说明你花了很多力气，模型比"昨天=今天"就好了一点点——
这时候应该反思特征工程或模型选择是否正确。

持续法 (Persistence Forecast)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
定义: 用昨天的负荷值作为今天的预测值。
     forecast(t) = actual(t - 24h)

为什么是 24 小时？
电力负荷有极强的日周期 (Diurnal Cycle)：
- 早晨↑（人们起床）→ 中午↑（工业/商业高峰）→ 傍晚↑（回家）
- 凌晨↓（大多数人睡觉）→ 循环往复
昨天的同一时刻是今天的最好近似。

这是时序预测的最简单基线，但它出奇地有效——
在电力负荷预测中，持续法通常能做到 MAPE 3%-5%。
如果你的 XGBoost 做不到比这更好，说明还没学到日周期模式。

P&L 计算 (Profit & Loss)
~~~~~~~~~~~~~~~~~~~~~~~~
模拟交易的盈亏：假设你按照预测来"买电"，实际交付时按真实负荷"结算"。
这只是学习用的简化模型，不是真实的电力交易结算逻辑。

简化假设:
- 统一电价 $50/MWh（美国日前市场均价参考）
- 买入量 = 预测负荷
- 结算价 = 实际负荷 × 固定电价
- P&L = 实际收入 - 买入成本
"""

import pandas as pd
import numpy as np
import logging
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def persistence_forecast(df: pd.DataFrame) -> pd.Series:
    """
    持续法预测：用 24 小时前的负荷作为预测。

    算法: forecast[t] = actual[t - 24]

    为什么是 24？
    电力负荷有日周期——昨天下午 3 点的负荷
    是预测今天下午 3 点负荷的最好起点。

    Args:
        df: 包含 timestamp, load_mw 列的 DataFrame

    Returns:
        预测值 Series，索引与 df 相同。
        前 24 小时用后向填充补齐。
    """
    forecast = df["load_mw"].shift(24)

    # 前 24 个值没有"昨天数据"，用后向填充
    # 即用第 25 小时的值回填第 1-24 小时
    forecast = forecast.bfill()

    logger.info(f"持续法预测: 使用 24h 滞后, 共 {len(forecast)} 个预测值")
    return forecast


def calculate_pnl(
    actual: pd.Series,
    forecast: pd.Series,
    price_per_mwh: float = 50.0,
) -> pd.Series:
    """
    计算模拟交易的累计盈亏 (Cumulative P&L)。

    交易模型:
    ~~~~~~~~
    你在每个时间点"买入"预测量的电力，
    实际交付时按真实负荷"结算"。

    P&L = (实际负荷 - 预测负荷) × 电价

    解释:
    - 如果预测偏低 (actual > forecast) → 你少买了 → 需要高价补够 → 亏
    - 如果预测偏高 (actual < forecast) → 你买多了 → 浪费 → 亏
    - 预测完美 → P&L = 0
    - 但这是简化模型，真实市场有更复杂的结算规则

    为什么这里 P&L 永远是负数？
    因为简化假设下，任何偏差都会产生"惩罚"。
    真实市场中，偏差在容忍范围内是不罚的。

    Args:
        actual:   实际负荷 Series
        forecast: 预测负荷 Series
        price_per_mwh: 电价 ($/MWh)，默认 50

    Returns:
        逐小时的累计 P&L Series
    """
    # 偏差 = forecast - actual
    # 负值 = 赔了（预测不准的代价）
    # 取负数让"更准的预测"显示为"更高的 P&L"
    hourly_pnl = -(forecast - actual).abs() * (price_per_mwh / 1000.0)
    # 除以 1000 是为了让数值好看（MW 级别偏差的代价）

    cumulative = hourly_pnl.cumsum()
    logger.info(f"P&L 计算完成: 累计 {cumulative.iloc[-1]:.2f}")
    return cumulative


def plot_pnl(
    df: pd.DataFrame,
    forecast: pd.Series,
    cumulative_pnl: pd.Series,
    title: str = "端到端基线 — 持续法预测 vs 实际",
) -> go.Figure:
    """
    绘制端到端管道结果图。

    包含两个子图:
    1. 上: 负荷预测 vs 实际（时间序列叠加图）
    2. 下: 累计 P&L（盈亏曲线）

    为什么用 Plotly 而不是 matplotlib？
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Plotly 是**交互式**的——你可以：
    - 悬停查看精确数值
    - 框选放大某个时间段
    - 双击重置视图
    这对学习过程中的数据探索非常有价值。

    Args:
        df:             原始数据（含 timestamp, load_mw）
        forecast:       预测值
        cumulative_pnl: 累计盈亏
        title:          图表标题

    Returns:
        plotly Figure 对象（在 Jupyter 中自动渲染）
    """
    # 创建两个子图，共享 X 轴
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("负荷预测 vs 实际", "累计模拟盈亏"),
        row_heights=[0.6, 0.4],
    )

    # ── 子图 1: 负荷预测 vs 实际 ─────────────────
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["load_mw"],
            mode="lines",
            name="实际负荷",
            line=dict(color="#1f77b4", width=2),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=forecast,
            mode="lines",
            name="持续法预测 (t-24h)",
            line=dict(color="#ff7f0e", width=1.5, dash="dash"),
        ),
        row=1, col=1,
    )

    # ── 子图 2: 累计 P&L ─────────────────────────
    color = "#2ca02c" if cumulative_pnl.iloc[-1] >= cumulative_pnl.iloc[0] else "#d62728"
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=cumulative_pnl,
            mode="lines",
            name="累计 P&L",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=f"rgba({','.join(map(str, [44, 160, 44, 0.2]) if color == '#2ca02c' else [214, 39, 40, 0.2])})",
        ),
        row=2, col=1,
    )

    # ── 布局设置 ─────────────────────────────────
    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        height=700,
        hovermode="x unified",  # 悬停时显示同一时间点的所有值
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="时间", row=2, col=1)
    fig.update_yaxes(title_text="负荷 (MW)", row=1, col=1)
    fig.update_yaxes(title_text="盈亏 ($)", row=2, col=1)

    return fig


# ═══════════════════════════════════════════════════════
# XGBoost 预测器 — 负荷预测核心引擎
# ═══════════════════════════════════════════════════════


class XGBoostForecaster:
    """
    XGBoost 负荷预测器 — 带 TimeSeriesSplit 防泄露和时间序列扩展。

    为什么用 XGBoost？
    ~~~~~~~~~~~~~~~~
    XGBoost (eXtreme Gradient Boosting) 是梯度提升树的工程优化实现。
    在电力负荷预测领域，XGBoost 是公认的最佳起步模型，原因有:

    1. **内置特征重要性** — 训练完就知道哪些特征有效
    2. **处理缺失值** — 电力数据常有缺失，XGBoost 原生支持
    3. **抗过拟合** — 正则化 (L1/L2) 内置于损失函数
    4. **速度快** — CPU 优化，不需要 GPU
    5. **工业验证** — 在 Kaggle 能源预测竞赛中长期霸榜

    梯度提升 (Gradient Boosting) 原理（简化版）:
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. 从最简单的预测开始（比如均值）
    2. 计算当前预测的残差 (实际值 - 预测值)
    3. 训练一棵新的决策树来**预测这些残差**
    4. 把新树的预测加到原来的预测上
    5. 重复步骤 2-4，每次新树都修正前一轮的错误

    最终预测 = 第一棵树 + 第二棵树 + 第三棵树 + ... + 第 N 棵树

    这就像:
    - 第一棵树: "全年均值大约是 50000MW"
    - 第二棵树: "夏天多加 10000MW"
    - 第三棵树: "周末减 5000MW"
    - ...每棵树学习一部分规律，最终组合起来形成完整预测。

    TimeSeriesSplit 为什么重要？
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    普通交叉验证 (KFold) 会随机分割数据:
        [2020, 2023, 2021, 2022] → 训练: [2020, 2023], 测试: [2021, 2022]
    这导致**用 2023 年的数据预测 2021 年**——现实不可行！

    TimeSeriesSplit 保证时序:
        训练: [2015, 2016, 2017] → 测试: [2018]
        训练: [2015, ..., 2018] → 测试: [2019]
        ...
    永远是过去预测未来，杜绝 look-ahead bias。

    另外 gap=24 参数保证了 lag_24h 特征不会"偷看"测试集:
        训练: [t=0, ..., t=1000] → gap=24 → 测试: [t=1025, ...]
    这额外的 24 小时间隔防止 lag 特征跨越训练/测试边界。
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        random_state: int = 42,
    ):
        """
        Args:
            n_estimators: 树的数量（迭代次数），默认 100
                          太多→过拟合、慢；太少→欠拟合
            max_depth:    每棵树的最大深度，默认 6
                          太深→过拟合；太浅→学不到复杂模式
            learning_rate: 学习率，默认 0.1
                          小值→更稳但需要更多树；大值→更快但可能过冲
            random_state:  随机种子，保证结果可复现
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.random_state = random_state
        self._model = None
        self._feature_cols = None
        self._scaler = None

    def train_evaluate(
        self,
        X: "pd.DataFrame",
        y: "pd.Series",
        n_splits: int = 5,
        gap: int = 24,
    ) -> dict:
        """
        用 TimeSeriesSplit 训练和评估 XGBoost 模型。

        CRITICAL: StandardScaler 在每次 fold 内部 fit——
        永远不会在全量数据上调 fit_transform()！

        这防止了 look-ahead bias（#1 反模式）。

        为什么 scaler 要封装在 fold 内部？
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        如果用 scaler.fit_transform(X) 在全量数据上:
        - Scaler 看到了测试集的分布
        - 训练时的特征值被测试集"污染"了
        - 模型指标虚高，但实际预测时不如预期

        正确做法 (本方法):
        - 每个 fold 内: scaler.fit(X_train) → transform(X_test)
        - Scaler 只学习训练集的分布
        - 测试集用训练集的 scaler 来变换
        - 这模拟了真实场景——你训练时不知道未来的数据分布

        Args:
            X:       特征 DataFrame
            y:       目标值 Series (load_mw)
            n_splits: TimeSeriesSplit 的分割数，默认 5
            gap:     训练/测试间的间隔（小时数），默认 24
                     防止 lag_24h 特征跨越训练/测试边界

        Returns:
            dict with:
            - predictions: 所有 fold 的预测值拼接 (np.array)
            - actuals:     对应的实际值 (np.array)
            - metrics:     {mae} — MAE 是唯一评估指标
            - model:       最后训练的模型 (可用于 predict())
            - feature_importance: 特征重要性 (dict)
        """
        import numpy as np
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import mean_absolute_error
        import xgboost as xgb

        self._feature_cols = list(X.columns)
        tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)

        all_predictions = []
        all_actuals = []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
            X_train_raw = X.iloc[train_idx]
            X_test_raw = X.iloc[test_idx]
            y_train = y.iloc[train_idx]
            y_test = y.iloc[test_idx]

            # CRITICAL: Scaler fit on TRAIN only
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train_raw)
            X_test = scaler.transform(X_test_raw)
            self._scaler = scaler  # save last fold's scaler for predict()

            # XGBoost 核心参数说明:
            # n_estimators: 树的数量 — 相当于"专家"的数量
            # max_depth:    树深度 — 每棵"专家"最多问几个问题
            # learning_rate: 学习率 — 每个"专家"的贡献有多大胆
            # subsample:    随机采样比例 — 每棵树只用 80% 数据 → 防过拟合
            # colsample_bytree: 随机特征比例 — 每棵树只用 80% 特征 → 防过拟合
            model = xgb.XGBRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=self.random_state,
                objective="reg:squarederror",
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            all_predictions.extend(y_pred.tolist())
            all_actuals.extend(y_test.tolist())

            fold_mae = mean_absolute_error(y_test, y_pred)
            logger.info(f"  Fold {fold + 1}: MAE={fold_mae:.0f}, "
                        f"训练集 {len(train_idx)} 行 → 测试集 {len(test_idx)} 行")

        predictions = np.array(all_predictions)
        actuals = np.array(all_actuals)

        mae = mean_absolute_error(actuals, predictions)

        importance = model.get_booster().get_score(importance_type="gain")
        importance = {k: float(v) for k, v in importance.items()}

        self._model = model

        result = {
            "predictions": predictions,
            "actuals": actuals,
            "metrics": {"mae": mae},
            "model": model,
            "feature_importance": importance,
        }

        logger.info(f"XGBoost 训练完成: MAE={mae:.0f}")
        return result

    def predict(self, X: "pd.DataFrame") -> "np.ndarray":
        """
        用训练好的模型预测新数据。

        Args:
            X: 特征 DataFrame (必须包含 train_evaluate 时的所有特征列)

        Returns:
            预测值数组
        """
        if self._model is None:
            raise RuntimeError("模型尚未训练。请先调用 train_evaluate()。")
        X_scaled = X[self._feature_cols].copy()
        if self._scaler is not None:
            X_scaled = pd.DataFrame(
                self._scaler.transform(X_scaled),
                columns=self._feature_cols,
                index=X_scaled.index,
            )
        return self._model.predict(X_scaled)

    def save_model(self, path: str) -> None:
        """
        持久化模型到磁盘。

        Args:
            path: 保存路径（.joblib 或 .pkl）
        """
        import joblib
        if self._model is None:
            raise RuntimeError("模型尚未训练。请先调用 train_evaluate()。")
        joblib.dump({
            "model": self._model,
            "feature_cols": self._feature_cols,
            "scaler": self._scaler,
        }, path)
        logger.info(f"模型已保存到 {path}")

    def load_model(self, path: str) -> None:
        """
        从磁盘加载模型。

        Args:
            path: 模型文件路径（.joblib 或 .pkl）
        """
        import joblib
        data = joblib.load(path)
        self._model = data["model"]
        self._feature_cols = data["feature_cols"]
        self._scaler = data.get("scaler", None)
        logger.info(f"模型已从 {path} 加载")

    def plot_forecast(
        self,
        df: "pd.DataFrame",
        predictions: "np.ndarray",
        title: str = "XGBoost 负荷预测 vs 实际",
    ) -> "go.Figure":
        """
        绘制预测对比图：实际 vs 预测叠加 + 误差分布直方图。

        Args:
            df:          原始数据（含 timestamp, load_mw）
            predictions: 预测值数组
            title:       图表标题

        Returns:
            plotly Figure 对象
        """
        actuals = df["load_mw"].values[-len(predictions):]
        errors = actuals - predictions

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("实际 vs 预测", "预测误差分布"),
            row_heights=[0.6, 0.4],
        )

        fig.add_trace(
            go.Scatter(
                x=df["timestamp"].values[-len(predictions):],
                y=actuals,
                mode="lines",
                name="实际负荷",
                line=dict(color="#1f77b4", width=2),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"].values[-len(predictions):],
                y=predictions,
                mode="lines",
                name="XGBoost 预测",
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
        fig.update_xaxes(title_text="预测误差 (MW)", row=2, col=1)
        fig.update_yaxes(title_text="负荷 (MW)", row=1, col=1)
        fig.update_yaxes(title_text="频次", row=2, col=1)

        return fig
