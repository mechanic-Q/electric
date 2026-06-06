---
schema_version: 1
doc_type: module-card
module_id: price-forecaster
---
# price-forecaster
## 定位
LEAR 电价预测器 — Lasso + 滞后特征 + 日历特征 + 滚动统计
## 契约摘要
- `LEARForecaster(alpha=0.01, max_iter=10000, random_state=42)`
- `train_evaluate(df, tier) -> dict{predictions, actuals, metrics, model, feature_importance}`
- `predict(X) -> np.ndarray`, `save_model/load_model(path)`
- `plot_price_forecast(df, preds) -> go.Figure`, `plot_coefficients() -> go.Figure`
## 关键逻辑
- Tier 1-3 渐进式特征 (6/11/14 列)
- TimeSeriesSplit(n_splits=5, gap=24), StandardScaler fit-on-train-only
- L1 正则化自动特征选择
- 与 XGBoostForecaster 同构接口
## 注意事项
- 目标变量为 price_da（日前价格），不是 load_mw
- 不处理 price_rt（实时价格预测不在范围内）
