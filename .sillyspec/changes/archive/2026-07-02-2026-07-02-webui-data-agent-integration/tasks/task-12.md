---
id: task-12
title: 更新 README Web Chat 使用说明
author: lmr
created_at: 2026-07-02 17:02:04
priority: P1
depends_on:
  - task-11
blocks:
  - task-13
requirement_ids:
  - FR-08
decision_ids:
  - D-002@v1
  - D-004@v1
allowed_paths:
  - README.md
---

## goal
Document upgraded Web Chat (two-panel UI + data catalog) in README.md: capabilities, example questions by category, startup instructions. Reinforce learning-platform scope.

## implementation
1. Table row for Web Chat UI: list example questions grouped by category (forecast, evaluation, trading, explain, data)
2. Architecture diagram: add `/capabilities`, `/datasets`, `/reports` to FastAPI endpoints
3. Quick start: note WebUI now shows capability catalog on startup
4. Any mention of "trading" or "交易" must carry educational-scope disclaimer; do not claim production or real-trading capability

## acceptance
README.md accurately reflects new Web Chat UX, example question categories, catalog API endpoints, and educational-only scope.

## verify
python -m pytest tests/test_api_catalog.py tests/test_chat_streaming_events.py -q

## constraints
- document learning-platform scope throughout; never claim production trading
- only edit README.md; leave source code untouched
