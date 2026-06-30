---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Requirements: 风/光功率独立预测模块

## 功能需求

- [ ] **FR-01**: 新增 `WindPowerForecaster`，target=`wind_actual_mw`。
- [ ] **FR-02**: 新增 `SolarPowerForecaster`，target=`solar_actual_mw`。
- [ ] **FR-03**: 两个预测器共享基础训练/评估逻辑，接口兼容 `train_evaluate(X, y)` / `predict(X)`。
- [ ] **FR-04**: 特征使用 Tier1-3 + Tier4 weather，缺 weather 时降级为 Tier1-3。
- [ ] **FR-05**: 输出 MAE/RMSE/nRMSE，nRMSE 以目标序列 max-min 或装机代理归一化。
- [ ] **FR-06**: service/API/CLI 支持 `model_type="wind"|"solar"`。
- [ ] **FR-07**: 验证脚本输出 `ellectric/reports/renewable_forecaster/{validation.json,validation.md,validation.log}`。
- [ ] **FR-08**: 测试覆盖 wind/solar 列存在、缺列降级、weather 特征、报告 schema。

## 数据列

- `wind_actual_mw`: 风电实际出力。
- `solar_actual_mw`: 光伏实际出力。
- `wind_forecast_mw`: 风电预测出力，可作为 baseline 对照。
- `solar_forecast_mw`: 光伏预测出力，可作为 baseline 对照。

## 验收命令

- `rtk pytest tests/test_renewable_forecaster.py`
- `python -m ellectric.scripts.validate_renewable_forecaster --no-fetch`
- `python -m ellectric.cli.main forecast wind 24`
- `python -m ellectric.cli.main forecast solar 24`
