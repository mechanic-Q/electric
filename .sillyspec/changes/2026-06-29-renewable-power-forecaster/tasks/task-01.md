---
id: task-01
title: 新增 renewable_forecaster.py 基础结构与共享训练评估逻辑
author: lmr
created_at: 2026-06-30 11:29:30
priority: P0
depends_on: []
blocks: [task-02, task-04, task-06]
requirement_ids: [FR-01, FR-02, FR-03]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths:
  - ellectric/pipeline/renewable_forecaster.py
---

goal: >
  新增 wind/solar 预测器基础结构，复用共享 XGBoost 训练评估逻辑。
implementation:
  - 新建 `_BaseRenewableForecaster`，抽取训练、预测、metrics 公共逻辑
  - 新建 `WindPowerForecaster`，target 为 `wind_actual_mw`
  - 新建 `SolarPowerForecaster`，target 为 `solar_actual_mw`
acceptance:
  - 两个 forecaster 暴露 `train_evaluate(X, y)` 与 `predict(X)`
  - metrics 包含 MAE/RMSE/nRMSE
  - 不修改现有 XGBoostForecaster 公开行为
verify:
  - rtk pytest tests/test_renewable_forecaster.py
constraints:
  - 只新增 renewable forecaster 模块
  - 不接入 service/API/CLI
  - 不引入深度学习依赖
