---
schema_version: 1
doc_type: module-card
module_id: forecaster
---
# forecaster
## 定位
负荷预测引擎 — 持久法基线 + XGBoost 时序回归 + P&L 模拟交易评估
## 契约摘要
- `persistence_forecast(df) -> pd.Series` — t-24h 朴素基线
- `XGBoostForecaster(n_splits=5, gap=24)` — TimeSeriesSplit 交叉验证
- `train_evaluate(X, y) -> dict` — per-fold StandardScaler, MAE/RMSE/MAPE/R²
- `predict(X) -> np.ndarray`, `save_model/load_model(path)`
- `calculate_pnl(df, forecast) -> pd.Series`, `plot_pnl() -> go.Figure`
## 关键逻辑
- gap=24 防止 lag_24h 跨越训练/测试边界
- StandardScaler 仅在当前 fold 训练集 fit，禁止 look-ahead bias
- P&L = (actual - forecast) × price / 1000，累积求和
## 注意事项
- 不处理电价预测（见 price-forecaster）
- 模型持久化使用 joblib，与 LEARForecaster 格式一致
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
