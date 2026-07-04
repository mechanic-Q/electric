---
id: task-04
title: 注册 GET /dashboard/rolling-demo API route
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-01, task-02]
blocks: [task-05, task-06, task-09]
requirement_ids: [FR-04, FR-05, FR-08]
decision_ids: [D-003@v1]
allowed_paths: [ellectric/api/server.py]
---

goal: >
  Expose the rolling demo builder through FastAPI without changing existing route semantics.
implementation:
  - Import RollingDemoResponse and build_rolling_demo.
  - Register GET /dashboard/rolling-demo before the static mount.
  - Delegate query params to the service without extra business logic.
acceptance:
  - Route returns meta, series, panels, strategy, reports, warnings.
  - days=1 works and invalid days return validation error.
  - Existing API routes and SPA static mount remain reachable.
verify:
  - python -c "from ellectric.api.server import app; assert any(r.path == '/dashboard/rolling-demo' for r in app.routes)"
constraints:
  - Do not call forecast, simulate, backtest, explain, or recommend handlers.
  - Keep route above app.mount('/').
