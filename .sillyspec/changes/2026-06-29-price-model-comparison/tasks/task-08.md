---
id: task-08
title: 更新模块文档
author: lmr
created_at: 2026-06-30 11:33:15
priority: P2
depends_on: [task-01, task-06]
blocks: []
requirement_ids: []
decision_ids: [D-001@v1, D-002@v1]
allowed_paths:
  - docs/Ellectric/modules/price-forecaster.md
---

goal: >
  记录 DNN baseline 与山东 price comparison report 的使用边界。
implementation:
  - 更新 price-forecaster 模块卡
  - 标明 DNN 是 PyTorch MLP baseline
  - 列出 comparison report 产物路径
acceptance:
  - 文档保留 MANUAL_NOTES
  - 明确不使用 TensorFlow
  - 明确 LEAR 仍是默认模型
verify:
  - rtk pytest tests/test_price_forecaster_dnn.py tests/test_compare_price_models.py
constraints:
  - 不改无关模块文档
  - 不删除人工备注区域
