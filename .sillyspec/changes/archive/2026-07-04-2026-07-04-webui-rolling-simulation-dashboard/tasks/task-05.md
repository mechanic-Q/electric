---
id: task-05
title: 验证现有 API route 和 static mount 兼容
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-04]
blocks: [task-09]
requirement_ids: [FR-08]
decision_ids: [D-003@v1]
allowed_paths: [tests/test_web_static.py, tests/test_api_catalog.py]
---

goal: >
  Confirm the new dashboard route does not regress legacy API routes or static SPA serving.
implementation:
  - Run existing web static and API catalog tests after route registration.
  - Extend route presence assertions only if the new route belongs in legacy route coverage.
  - Leave application route behavior to task-04.
acceptance:
  - Existing web static tests pass.
  - Existing API catalog tests pass.
  - /dashboard/rolling-demo is not captured by static mount.
verify:
  - python -m pytest tests/test_web_static.py tests/test_api_catalog.py -q
constraints:
  - Do not modify ellectric/api/server.py in this task.
  - Do not change catalog response-shape assertions.
