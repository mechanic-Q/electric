---
schema_version: 1
doc_type: module-card
module_id: renewable-forecaster
author: lmr
created_at: 2026-06-30 04:11:00
---

# renewable-forecaster

## 定位

风/光功率独立预测模块。使用 XGBoost 预测山东 15min 数据中的 wind_actual_mw 和 solar_actual_mw。复用 FeatureEngineer Tier1-4 特征，weather 作为可选增强层。

## 契约摘要

### WindPowerForecaster
- target: `wind_actual_mw`
- baseline: `wind_forecast_mw`（如存在，自动计算 baseline metrics）
- 对外方法: `train_evaluate(X, y)` → `predict(X)`

### SolarPowerForecaster
- target: `solar_actual_mw`
- baseline: `solar_forecast_mw`（如存在，自动计算 baseline metrics）
- 对外方法: `train_evaluate(X, y)` → `predict(X)`

### BaseRenewableForecaster
- 共享训练、预测、metrics 逻辑
- `_compute_metrics()` 提供 MAE/RMSE/nRMSE

## 关键逻辑

- 特征使用 Tier1-3 + 可选 Tier4 weather；weather 缺失时降级
- 评估使用 TimeSeriesSplit (5-fold, gap=points_per_day)
- nRMSE = RMSE / (max - min)，分母为 0 时返回 None
- 本轮不接入 RL observation space

## 注意事项

- 光伏出力夜间为 0，不影响 MAE 计算
- nRMSE 适合跨类型对比（风电 vs 光伏）
- Solar 列存在时方可用 SolarPowerForecaster

## 人工备注

<!-- MANUAL_NOTES_START -->
- 验证报告在 ellectric/reports/renewable_forecaster/
- 验证命令: python -m ellectric.scripts.validate_renewable_forecaster
<!-- MANUAL_NOTES_END -->
