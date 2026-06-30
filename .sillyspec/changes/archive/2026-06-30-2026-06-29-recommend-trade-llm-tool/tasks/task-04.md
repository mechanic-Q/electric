---
id: task-04
title: 新增 /recommend FastAPI endpoint
author: lmr
created_at: 2026-06-30 11:36:18
priority: P1
depends_on: [task-01, task-02]
blocks: []
requirement_ids: [FR-05]
decision_ids: [D-001@v1]
allowed_paths:
  - ellectric/api/server.py
---

goal: >
  将 recommend service 暴露为 REST endpoint。
implementation:
  - 新增 POST /recommend
  - 使用 RecommendRequest/RecommendResponse
  - 保持现有 /predict /backtest /explain 不变
acceptance:
  - endpoint 返回固定 schema
  - FastAPI docs 可见 /recommend
  - 旧 endpoint 不受影响
verify:
  - rtk pytest tests/test_recommend_handler.py
constraints:
  - 不新增 auth/session
  - 不改现有 endpoint path
