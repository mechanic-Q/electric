---
id: task-09
title: 运行后端 rolling demo 测试和 API smoke check
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-03, task-04, task-05]
blocks: []
requirement_ids: [FR-04, FR-05, FR-06, FR-08]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths: []
---

goal: >
  Verify the backend endpoint and legacy API/static behavior after implementation.
implementation:
  - Run rolling demo tests.
  - Run API catalog and static web tests.
  - Smoke check route registration and default payload shape if needed.
acceptance:
  - Rolling demo tests pass.
  - API catalog and web static tests pass.
  - No backend verification triggers training or heavy simulation.
verify:
  - python -m pytest tests/test_dashboard_rolling_demo.py tests/test_api_catalog.py tests/test_web_static.py -q
constraints:
  - Verification-only; no source edits.
  - test_dashboard_rolling_demo.py must exist before this task runs.
