---
schema_version: 1
doc_type: module-card
module_id: forecaster
---
# forecaster
## 定位
预测引擎：提供持续法基线预测、XGBoost 负荷预测、模拟 P&L 盈亏计算及 plotly 可视化。边界：纯预测与回测，不做数据清洗或特征工程——上游依赖 cleaner 与 data-loader 产出 `cleaned_load.parquet` 后再进入本模块。
## 契约摘要
- `persistence_forecast(df)` — 持续法基线：`forecast[t] = load_mw[t-24h]`，前 24 点 bfill 补齐
- `calculate_pnl(actual, forecast, price_per_mwh=50)` — `-(|forecast - actual|) * price / 1000` 逐小时 P&L，累计 cumsum
- `plot_pnl(df, forecast, cumulative_pnl, title)` — 双子图 plotly（负荷对比 + P&L 曲线）
- `XGBoostForecaster` 类：
  - `train_evaluate(X, y, n_splits=5, gap=24)` — TimeSeriesSplit, 每 fold 内 StandardScaler fit-on-train-only, XGBRegressor, 返回 `{predictions, actuals, metrics: {mae}, model, feature_importance}`
  - `predict(X)` — 推理
  - `save_model(path)` / `load_model(path)` — joblib 持久化
  - `plot_forecast(df, predictions, title)` — 双子图 plotly（实际vs预测叠加 + 误差分布直方图）
## 关键逻辑
```
forecast = df["load_mw"].shift(24).bfill()        # → 持续法
for train_idx, test_idx in tscv.split(X):          # gap=24 防 lag 泄露
    scaler = StandardScaler().fit(X.iloc[train_idx])  # → 仅在训练集 fit
    X_train = scaler.transform(X.iloc[train_idx])
    model = XGBRegressor(...).fit(...)
    y_pred = model.predict(scaler.transform(X.iloc[test_idx]))
mae = mean_absolute_error(actuals, predictions)    # → 仅 MAE
joblib.dump({"model": model, "feature_cols": cols}, path)  # → 持久化
```
## 注意事项
- **Scaler 绝不 fit 全量数据**：在 TimeSeriesSplit 每 fold 内部单独 fit。
- `calculate_pnl` 返回的 P&L 永远 ≤ 0，仅用于模型间横向对比。
- MAE 是唯一评估指标，符合项目决策 D-14；如需 RMSE/MAPE/R² 在 notebook 中额外计算。
## 变更索引
- ql-20260606-001-a3f2 | gap 0→24, MAE-only, 新增 save_model/load_model/plot_forecast
- ql-20260607-001-3f2a | predict() 支持 scaler 转换: 新增 self._scaler, save/load 包含 scaler
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
