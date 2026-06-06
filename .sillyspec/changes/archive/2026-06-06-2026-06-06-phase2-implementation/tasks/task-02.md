---
id: task-02
title: 创建 price_forecaster.py — LEARForecaster（Tier 1-3 特征 + train_evaluate + 可视化）
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P0
estimated_hours: 4
depends_on: []
blocks: [task-03]
allowed_paths:
  - ellectric/pipeline/price_forecaster.py
  - ellectric/pipeline/__init__.py
---

# task-02: 创建 price_forecaster.py — LEARForecaster（Tier 1-3 特征 + train_evaluate + 可视化）

## 修改文件

| 操作 | 文件 |
|------|------|
| 新建 | `ellectric/pipeline/price_forecaster.py` |
| 修改 | `ellectric/pipeline/__init__.py`（添加 PriceDataLoader + LEARForecaster 导出） |

## 实现要求

1. **LEAR = Lasso + Lag features + Calendar features + Rolling statistics** — 电价预测的标准方法（Lasso Estimated AutoRegressive），区别于 Phase 1 的 XGBoost 树模型
2. **遵循 Phase 1 forecaster.py 设计惯例**：模块级 docstring（设计理念、LEAR 原理说明、模块职责）、logger 配置、`plotly` 可视化风格（`make_subplots` + `go.Scatter` + `go.Histogram`）、`joblib` 模型持久化
3. **内置特征工程**：`add_price_features()` 方法接受 `price_da, load_mw, wind_mw, solar_mw` 列，生成 Tier 1-3 特征（见接口定义），**scaler fit-on-train-only 在每个 fold 内部**
4. **与 Phase 1 forecaster.py 同构**：`train_evaluate()` → `dict`（predictions, actuals, metrics, model, feature_importance），`save_model()` / `load_model()` 用 joblib
5. **特征列定义与 FeatureEngineer 同风格**：`get_feature_columns(tier)` 返回对应 tier 的列名列表
6. **目标变量是 `price_da`**（日前价格，元/MWh），区别于 Phase 1 的 `load_mw`

### Lasso（L1 正则化线性回归）原理

Lasso（Least Absolute Shrinkage and Selection Operator）在普通线性回归的损失函数上加 L1 惩罚项：

```
Lasso 目标函数: MSE + α × Σ|βᵢ|
```

其中 α（alpha）控制正则化强度：
- α=0 → 普通最小二乘（OLS），可能过拟合
- α 增大 → 更多系数被压缩到零 → 自动特征选择
- α 过大 → 所有系数为零（欠拟合）

LEAR 方法的核心思路：
1. 用大量滞后特征和日历特征构建宽特征矩阵（宽数据）
2. Lasso 的 L1 正则化自动筛选重要特征（稀疏解）
3. 最终模型只保留预测能力最强的几个滞后项
4. 这在电力日前价格预测中表现优异，尤其当特征数量远多于样本数量时

这与 XGBoost 的本质区别：
- XGBoost：树模型，自动捕捉非线性交互
- Lasso：线性模型，可解释性强（系数 = 边际影响）
- 在电价预测中，LEAR 通常优于复杂模型（epftoolbox 论文结论）

## 接口定义

### LEARForecaster 类

```python
class LEARForecaster:
    def __init__(
        self,
        alpha: float = 0.01,
        max_iter: int = 10000,
        random_state: int = 42,
    ) -> None:
        """
        Args:
            alpha:       L1 正则化强度（默认 0.01）
            max_iter:    最大迭代次数（默认 10000）
            random_state: 随机种子（保证可复现）
        """

    def add_price_features(
        self,
        df: pd.DataFrame,
        tier: str = "tier1",
    ) -> pd.DataFrame:
        """
        添加电价预测特征。

        Tier 1 (核心, 6 个特征):
          hour, day_of_week, month, is_weekend,
          lag_24h_price, lag_168h_price
          — 快速搭建基线，验证预测流程

        Tier 2 (中级, 在 Tier 1 基础上 + 5 个特征 = 11 个):
          lag_24h_load, lag_24h_wind, lag_24h_solar,
          rolling_mean_24h_price, rolling_std_24h_price
          — 引入相关变量（负荷、新能源）和价格波动性

        Tier 3 (高级, 在 Tier 2 基础上 + 3 个特征 = 14 个):
          hour_sin, hour_cos, price_trend_7d
          — 循环时间编码 + 价格趋势

        Args:
            df:   包含 timestamp, price_da, load_mw, wind_mw, solar_mw 的 DataFrame
            tier: 特征层级，'tier1' | 'tier2' | 'tier3'

        Returns:
            新增特征列的 DataFrame（不修改原 df）
        """

    def train_evaluate(
        self,
        df: pd.DataFrame,
        tier: str = "tier1",
        n_splits: int = 5,
        gap: int = 24,
    ) -> dict:
        """
        TimeSeriesSplit + StandardScaler(fit-on-train-only) + Lasso 训练评估。

        Args:
            df:       含特征列和目标列 (price_da) 的 DataFrame
            tier:     特征层级
            n_splits: TimeSeriesSplit 折数
            gap:      训练/测试间隔（小时）

        Returns:
            dict:
              - predictions:        np.ndarray  所有 fold 预测值拼接
              - actuals:            np.ndarray  对应实际值
              - metrics:            dict        {mae: float, rmse: float}
              - model:              Lasso       最后 fold 训练的模型
              - feature_importance: dict        特征系数绝对值 |βᵢ| (Lasso 无内置 importance, 用系数绝对值替代)
        """

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """用训练好的模型预测。"""

    def save_model(self, path: str) -> None:
        """joblib 持久化 model + feature_cols。"""

    def load_model(self, path: str) -> None:
        """从 joblib 文件加载模型。"""

    def get_feature_columns(self, tier: str = "tier1") -> list:
        """返回指定 tier 的特征列名列表。"""

    def plot_price_forecast(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,
        title: str = "LEAR 电价预测 vs 实际",
    ) -> go.Figure:
        """
        绘制预测对比图（与 Phase 1 plot_forecast 同风格）:
          子图 1: 实际 vs 预测叠加（时序线图）
          子图 2: 预测误差分布（直方图）

        Args:
            df:          含 timestamp, price_da 的 DataFrame
            predictions: 预测值数组
            title:       图表标题

        Returns:
            plotly Figure
        """

    def plot_coefficients(
        self,
        top_n: int = 15,
        title: str = "LEAR 特征系数 (Lasso L1 正则化)",
    ) -> go.Figure:
        """
        绘制 Lasso 特征系数条状图（可选）。

        Lasso 的优势: 系数绝对值 = 该特征对价格的边际影响。
        正系数 → 特征值增加时价格上涨。
        负系数 → 特征值增加时价格下跌。
        系数为零 → 该特征被 L1 正则化剔除（未选中）。

        Args:
            top_n: 显示 top N 个系数的特征
            title: 图表标题

        Returns:
            plotly Figure
        """
```

### 特征列名定义

| Tier | 特征 | 来源 |
|------|------|------|
| 1 | hour | `df["timestamp"].dt.hour` |
| 1 | day_of_week | `df["timestamp"].dt.dayofweek` |
| 1 | month | `df["timestamp"].dt.month` |
| 1 | is_weekend | `day_of_week.isin([5, 6])` |
| 1 | lag_24h_price | `df["price_da"].shift(24).bfill()` |
| 1 | lag_168h_price | `df["price_da"].shift(168).bfill()` |
| 2 | lag_24h_load | `df["load_mw"].shift(24).bfill()` |
| 2 | lag_24h_wind | `df["wind_mw"].shift(24).bfill()` |
| 2 | lag_24h_solar | `df["solar_mw"].shift(24).bfill()` |
| 2 | rolling_mean_24h_price | `df["price_da"].rolling(24, min_periods=1).mean()` |
| 2 | rolling_std_24h_price | `df["price_da"].rolling(24, min_periods=1).std().fillna(0)` |
| 3 | hour_sin | `np.sin(2 * np.pi * hour / 24)` |
| 3 | hour_cos | `np.cos(2 * np.pi * hour / 24)` |
| 3 | price_trend_7d | `df["price_da"].rolling(168, min_periods=1).mean()` |

`get_feature_columns()` 的 tier 累积规则：
- `tier1`: 仅 Tier 1 特征（6 列）
- `tier2`: Tier 1 + Tier 2 特征（11 列）
- `tier3`: Tier 1 + Tier 2 + Tier 3 特征（14 列）

## 边界处理

| # | 场景 | 处理方法 |
|---|------|----------|
| 1 | DF 缺少必要列（如 price_da / load_mw） | `raise ValueError`，列出缺少的列名 |
| 2 | price_da 含 NaN 或无穷值 | `logger.warning` 统计 NaN 比例，`df.dropna(subset=["price_da"])` 丢弃 |
| 3 | 特征列全部为零（数据异常） | Lasso 系数全为零 → `logger.warning` 提示检查数据 |
| 4 | Tier 选择 `add_price_features(df, "tier2")` 但 Tier 1 特征未先调用 | `add_price_features` 内部检查 `hour` 列是否存在，不存在则先添加低 tier |
| 5 | 预测时传入的 X 缺少 `_feature_cols` 中记录的列 | `raise ValueError`，给出友好提示 |
| 6 | 1900-01-01 等占位日期导致的极端时间戳 | 允许通过，不强制校验时间范围 |
| 7 | 数据行数 < gap + 特征窗口（如 < 200 行） | `TimeSeriesSplit` 自动报错，捕获后包装为友好 `ValueError` |
| 8 | `price_trend_7d` 计算在数据不足 168 行时 | 使用 `rolling(168, min_periods=1)` 不抛异常，`logger.info` 说明填补策略 |

## 非目标

- 不继承 XGBoostForecaster（模型类型不同，算法差异大）
- 不做特征选择以外的模型调优（如 GridSearch on alpha — Wave 2 再考虑）
- 不支持多步预测（仅输出单步，即下一小时）
- 不做概率预测（不输出置信区间）
- 不处理 price_rt 列（实时价格预测不是 LEAR 的目标）
- 不自动下载数据（依赖 task-01 的 PriceDataLoader）

## 参考

- Phase 1 `forecaster.py`（XGBoostForecaster）：`train_evaluate` 签名、`plot_forecast` plotly 风格、`save_model` / `load_model` joblib 用法、`__init__.py` 导出模式
- Phase 1 `features.py`（FeatureEngineer）：`add_tier*_features` 渐进式风格、`get_feature_columns` 分层规则
- Phase 2 `design.md § Wave 1 详细设计 > 新增模块：price_forecaster.py` + `LEAR 模型设计`
- Phase 2 `plan.md § Wave 1` + 全局验收标准第 3 条
- epftoolbox 论文（LEAR 方法原始出处）：Lasso Estimated AutoRegressive 的结构说明

## TDD 步骤

```
 1. [NEW] tests/pipeline/test_price_forecaster.py + test_lear_init (默认参数)
 2. [NEW] test_lear_add_price_features_tier1 (Tier 1 特征列前/后对比)
 3. [NEW] test_lear_add_price_features_tier2 (Tier 2 包含 Tier 1 + 增量)
 4. [NEW] test_lear_add_price_features_tier3 (Tier 3 包含全部 14 列)
 5. [NEW] test_lear_train_evaluate (端到端训练，验证输出 dict 结构)
 6. [NEW] test_lear_train_evaluate_mae (训练后 MAE 是正数)
 7. [NEW] test_lear_predict (predict 方法返回正确形状)
 8. [NEW] test_lear_save_load_model (joblib 持久化 + 加载)
 9. [NEW] test_lear_missing_column (缺少 price_da 时 ValueError)
10. [NEW] test_lear_get_feature_columns (各 tier 列数正确)
```

## 验收标准

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | `from ellectric.pipeline import LEARForecaster` 可导入 | `pytest tests/pipeline/test_price_forecaster.py::test_lear_init` 通过 |
| 2 | `LEARForecaster().add_price_features(df, "tier1")` 返回含 6 个新增特征列的 DataFrame | 测试验证列名精确匹配 |
| 3 | `LEARForecaster().add_price_features(df, "tier3")` 返回含 14 个新增特征列的 DataFrame | 测试验证列数 |
| 4 | `train_evaluate()` 返回的 dict 含 predictions, actuals, metrics（mae + rmse）, model, feature_importance | 验证 dict keys |
| 5 | predictions 和 actuals 长度相等 | `len(result["predictions"]) == len(result["actuals"])` |
| 6 | `result["metrics"]["mae"]` 是正数 | `assert result["metrics"]["mae"] > 0` |
| 7 | `save_model()` + `load_model()` 可正确恢复 `predict()` | 保存加载后预测 vs 原始预测一致 |
| 8 | 缺少 price_da 列时 `raise ValueError` | `pytest.raises(ValueError)` |
| 9 | `get_feature_columns("tier1")` 返回 6 列 | `len(cols) == 6` |
| 10 | `get_feature_columns("tier3")` 返回 14 列 | `len(cols) == 14` |
| 11 | `plot_price_forecast()` 返回 `plotly.graph_objects.Figure` | `isinstance(fig, go.Figure)` |
| 12 | scaler 未通过 `fit_transform` 在全量数据上调用 | 代码审查确认 scaler.fit 在 fold 循环内 |
