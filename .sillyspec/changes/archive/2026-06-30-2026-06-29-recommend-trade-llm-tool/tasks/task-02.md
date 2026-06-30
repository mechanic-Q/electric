---
id: task-02
title: 实现 run_recommend_trade service handler
author: lmr
created_at: 2026-06-30 11:36:18
priority: P0
depends_on: [task-01]
blocks: [task-03, task-04, task-05, task-06]
requirement_ids: [FR-04, FR-06, FR-07]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths:
  - ellectric/service/handlers.py
---

goal: >
  聚合 forecast/backtest/explain evidence，生成结构化交易建议。
implementation:
  - 调用或复用现有 forecast/backtest/explain handler
  - 生成 actions、summary、confidence、evidence
  - 实现 low confidence 保守输出与 disclaimer
acceptance:
  - 缺 evidence 时不崩溃
  - low confidence 输出 hold 或 reduced-size
  - disclaimer 始终存在
verify:
  - rtk pytest tests/test_recommend_handler.py
constraints:
  - 不调用真实交易接口
  - LLM 不参与核心计算
