---
schema_version: 1
doc_type: module-card
module_id: price-forecaster
author: lmr
created_at: 2026-06-30 22:16:05
---

# price-forecaster

## 定位

电价预测与模型对比模块。核心默认模型仍是 LEAR（Lasso + 滞后特征 + 日历特征 + 滚动统计），新增 PyTorch MLP DNN baseline 和山东电价模型对比报告能力。

## 契约摘要

- `LEARForecaster(alpha=0.01, max_iter=10000, random_state=42)`
- `DNNPriceForecaster(input_dim=None, hidden_dims=(128, 64), lr=1e-3, epochs=50)`
- `train_evaluate(df, tier) -> dict{predictions, actuals, metrics, model, feature_importance}`
- `DNNPriceForecaster.train_evaluate(X, y, n_splits=5) -> dict{predictions, actuals, metrics, model}`
- `predict(X) -> np.ndarray`, `save_model/load_model(path)`
- `plot_price_forecast(df, preds) -> go.Figure`, `plot_coefficients() -> go.Figure`
- `python -m ellectric.scripts.compare_price_models --dataset shandong` 生成 LEAR/DNN/persistence/weekly_avg 对比报告

## 关键逻辑

- Tier 1-3 渐进式特征 (6/11/14 列)
- TimeSeriesSplit(n_splits=5, gap=24), StandardScaler fit-on-train-only
- LEAR 使用 L1 正则化做特征选择，仍是默认 price forecast
- DNN 是 PyTorch MLP baseline，不使用 TensorFlow / epftoolbox DNN
- Comparison script 统一山东数据切分，输出 MAE/RMSE/MAPE 与 DM/GW pairwise table
- Baseline 指标过滤 NaN/Inf actual-prediction pairs，适配山东日前价格大量缺失场景
- 报告产物：`comparison.json`, `comparison.md`, `residuals.html`, `comparison.log`

## 注意事项

- 目标变量为 `price_da`（日前价格），不是 `load_mw`
- 不处理 `price_rt`（实时价格预测不在范围内）
- `price` 默认仍走 LEAR；`price_dnn` 必须显式 opt-in
- DNN 不调参刷榜，只用于教学和基线比较
- 缺少 epftoolbox 时 DM/GW 输出 MOCK 标注，metrics 不被阻断

## 变更索引

- ql-20260607-001-3f2a | predict() 支持 scaler 转换: 新增 self._scaler, save/load 包含 scaler
- archive-20260630-price-model-comparison | 新增 PyTorch DNN baseline 与山东四模型对比报告

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
