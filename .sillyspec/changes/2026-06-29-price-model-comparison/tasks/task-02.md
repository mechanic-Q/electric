---
id: task-02
title: 新增 DNN forecaster 单元测试
author: lmr
created_at: 2026-06-30 11:33:15
priority: P0
depends_on: [task-01]
blocks: []
requirement_ids: [FR-08]
decision_ids: [D-001@v1]
allowed_paths:
  - tests/test_price_forecaster_dnn.py
---

goal: >
  快速验证 DNNPriceForecaster 的训练、预测和 metrics schema。
implementation:
  - 构造小型 synthetic price dataset
  - 测试 train_evaluate 返回 metrics/predictions
  - 测试 predict 输入输出 shape
acceptance:
  - 测试 CPU 下快速通过
  - 不读真实山东数据
  - 不触发长训练
verify:
  - rtk pytest tests/test_price_forecaster_dnn.py
constraints:
  - 不写报告产物
  - 不调参
