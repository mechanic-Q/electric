---
id: task-04
title: 实现 LEAR/DNN/persistence/weekly_avg 统一评估
author: lmr
created_at: 2026-06-30 11:33:15
priority: P0
depends_on: [task-01, task-03]
blocks: [task-05, task-06]
requirement_ids: [FR-02, FR-03, FR-04]
decision_ids: [D-003@v1]
allowed_paths:
  - ellectric/scripts/compare_price_models.py
---

goal: >
  在同一切分上评估四个电价模型并输出可比较 metrics。
implementation:
  - 调用现有 LEAR forecaster
  - 调用 DNNPriceForecaster
  - 实现 persistence 与 weekly_avg baseline
  - 统一计算 MAE/RMSE/MAPE
acceptance:
  - 四模型都有 metrics
  - DNN 不覆盖 LEAR 默认模型
  - MAPE zero-mask 处理一致
verify:
  - rtk pytest tests/test_compare_price_models.py
constraints:
  - 不做超参数搜索
  - 不伪造模型结果
