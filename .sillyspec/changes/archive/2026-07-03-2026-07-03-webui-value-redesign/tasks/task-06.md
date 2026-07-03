---
id: task-06
title: 接入构建产物与 FastAPI 静态服务兼容验证
author: lmr
created_at: 2026-07-03 17:06:03
priority: P0
depends_on: [task-05]
blocks: [task-07, task-08]
requirement_ids: [FR-008, FR-009]
decision_ids: [D-002@v2, D-005@v1]
allowed_paths: [ellectric/api/static/index.html, ellectric/api/server.py, tests/test_api_catalog.py, tests/test_web_static.py]
---
goal: >
  Verify the built dashboard is served by FastAPI at `/` and does not capture existing REST/SSE API routes.
implementation:
  - Keep `StaticFiles("/")` mounted after API route registration.
  - Add or update web static smoke tests for `GET /` and legacy catalog routes.
  - Confirm generated static output is served without changing business endpoint behavior.
acceptance:
  - `GET /` returns HTML with the React root or built dashboard shell.
  - `/capabilities`, `/datasets`, and `/reports` still return JSON.
  - Catalog routes remain registered before static mount.
verify:
  - python -m pytest tests/test_api_catalog.py tests/test_web_static.py -q
constraints:
  - StaticFiles mount stays after API routes.
  - Do not alter predict/simulate/backtest/explain/recommend/chat request or response semantics.
  - Generated static file may be build output; do not hand-maintain it as source.
