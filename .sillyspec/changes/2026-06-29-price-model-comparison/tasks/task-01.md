---
id: task-01
title: 新增 PyTorch DNN 电价预测器
author: lmr
created_at: 2026-06-30 11:33:15
priority: P0
depends_on: []
blocks: [task-02, task-04]
requirement_ids: [FR-01]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths:
  - ellectric/pipeline/price_forecaster_dnn.py
---

goal: >
  新增轻量 PyTorch MLP 电价预测器，作为 DNN baseline。
implementation:
  - 新建 DNNPriceForecaster 类
  - 实现 train_evaluate/predict 与 metrics
  - 固定小模型配置，不做调参
acceptance:
  - 可在小样本上完成一次训练预测
  - 输出 MAE/RMSE/MAPE
  - 不依赖 TensorFlow
verify:
  - rtk pytest tests/test_price_forecaster_dnn.py
constraints:
  - 不改变现有 PriceForecaster
  - 不引入新重依赖
