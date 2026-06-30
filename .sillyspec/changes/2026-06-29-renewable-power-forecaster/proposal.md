---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Proposal: 风/光功率独立预测模块

## 动机

图迹技术画像包含“深度状态空间模型 / 风功率预测”。Ellectric 当前只有负荷预测、电价预测和 weather Tier4 辅助特征；山东数据已经包含 `wind_actual_mw`, `solar_actual_mw`, `wind_forecast_mw`, `solar_forecast_mw`，适合补齐风/光功率预测能力。

本变更用轻量 XGBoost 实现 wind + solar 独立预测模块，先不接入 RL observation space，避免牵动 96 维全量 RL 重训。

## 变更范围

- 新增 `renewable_forecaster.py`，提供 wind/solar 预测器。
- 复用现有 FeatureEngineer Tier1-4，weather 是关键特征。
- 扩展 service/API/CLI 支持 `forecast wind` / `forecast solar`。
- 新增验证脚本输出 JSON/Markdown/log 报告。
- 新增单元测试和模块文档。

## 不在范围内

- 不实现深度状态空间模型。
- 不接入 RL trading_env observation space。
- 不重新跑全量 RL 训练。
- 不新增天气源或外部数据。
- 不做生产级新能源预测服务。

## 成功标准

- `WindPowerForecaster` 和 `SolarPowerForecaster` 可训练并评估 MAE/RMSE/nRMSE。
- `python -m ellectric.cli.main forecast wind 24` 可运行。
- `python -m ellectric.cli.main forecast solar 24` 可运行。
- 验证脚本在山东全量数据上输出真实报告。
- 测试覆盖 wind/solar schema、weather 特征、缺列降级路径。
