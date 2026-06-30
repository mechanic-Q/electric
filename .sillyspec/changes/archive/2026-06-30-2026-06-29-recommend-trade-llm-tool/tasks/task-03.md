---
id: task-03
title: 新增 recommend handler 单元测试
author: lmr
created_at: 2026-06-30 11:36:18
priority: P0
depends_on: [task-01, task-02]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-06, FR-07, FR-08]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1]
allowed_paths:
  - tests/test_recommend_handler.py
---

goal: >
  覆盖 recommend schema、evidence 降级和 confidence guard。
implementation:
  - mock forecast/backtest/explain evidence
  - 测试 high/medium/low confidence
  - 测试 disclaimer 和 action schema
acceptance:
  - 单测不启动 API server
  - 覆盖低置信保守建议
  - 覆盖缺 evidence 降级
verify:
  - rtk pytest tests/test_recommend_handler.py
constraints:
  - 不调用 LLM API
  - 不读真实数据
