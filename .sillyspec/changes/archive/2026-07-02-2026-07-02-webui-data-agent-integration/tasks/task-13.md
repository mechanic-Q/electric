---
id: task-13
title: 运行 targeted verification（FR-01~FR-09, D-001@v1~D-005@v1）
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06, task-07, task-08, task-09, task-10, task-11, task-12]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-005@v1]
allowed_paths:
  - .sillyspec/local.yaml
  - tests/test_service_catalog.py
  - tests/test_api_catalog.py
  - tests/test_chat_streaming_events.py
  - ellectric/api/server.py
---
## goal

Confirm all 12 prior tasks pass via targeted tests and optional smoke.

## acceptance

- 3 new test files pass: catalog service, API endpoints, SSE event contract.
- 2 regression files pass: `test_recommend_handler.py`, `test_time_resolution_15min.py`.
- Optional smoke: `GET /capabilities` and `GET /reports` return 200.

## verify

1. `pytest tests/test_service_catalog.py tests/test_api_catalog.py tests/test_chat_streaming_events.py -v`
2. `pytest tests/test_recommend_handler.py tests/test_time_resolution_15min.py -v`

## constraints

- `test_strategy=skip` means commands must be explicit (no auto-run).
- Changes only within allowed_paths (5 files). Fix failures as blocked on the bug's originating task.
