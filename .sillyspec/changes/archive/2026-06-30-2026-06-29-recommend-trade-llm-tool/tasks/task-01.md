---
id: task-01
title: 新增 recommend request/response schema
author: lmr
created_at: 2026-06-30 11:36:18
priority: P0
depends_on: []
blocks: [task-02, task-04, task-05]
requirement_ids: [FR-01, FR-02, FR-03]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths:
  - ellectric/service/schemas.py
---

goal: >
  定义可测试的交易建议请求、响应和 TradeAction schema。
implementation:
  - 新增 RecommendRequest
  - 新增 RecommendResponse
  - 新增 TradeAction 子结构
acceptance:
  - schema 包含 actions/confidence/evidence/disclaimer
  - action 支持 buy/sell/hold
  - price_limit 与 quantity_mwh 可为 None
verify:
  - rtk pytest tests/test_recommend_handler.py
constraints:
  - 不改现有 ForecastResponse
  - 不移除旧字段
