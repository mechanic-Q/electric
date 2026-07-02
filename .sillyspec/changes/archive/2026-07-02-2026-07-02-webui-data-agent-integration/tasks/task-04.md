---
id: task-04
title: "新增 capabilities/datasets/reports API 路由（覆盖：FR-01, FR-02, FR-03, FR-09, D-002@v1, D-005@v1）"
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-03]
blocks: [task-06, task-07, task-11]
requirement_ids: [FR-01, FR-02, FR-03, FR-09]
decision_ids: [D-002@v1, D-005@v1]
allowed_paths:
  - ellectric/api/server.py
---

## goal
在 `ellectric/api/server.py` 新增 4 个只读 GET 路由：`/capabilities`、`/datasets`、`/reports`、`/reports/{report_id:path}`。所有新路由注册在 `app.mount("/")` 之前。

## implementation
1. Import task-03 handlers: `list_capabilities`、`list_datasets`、`list_reports`、`get_report`。
2. `app.mount("/")` 前插入 4 个路由，调用对应 handler。`/reports/{report_id:path}` 使用 path converter 支持含 `/` 的 ID；不存在的 ID 返回 404。
3. 更新 startup log 和 docstring 囊括新端点。

## acceptance
- 4 个端点返回正确状态码和 JSON 结构，OpenAPI docs 可见。
- 现有 POST 路由和 `GET /` 不变。路由注册顺序保证 catalog API 不被 StaticFiles 捕获。

## verify
`python -m pytest tests/test_api_catalog.py -q`

## constraints
- 新路由注册必须在 `app.mount("/", StaticFiles(...))` 之前。
- `/reports/{report_id:path}` 使用 FastAPI path converter。
- 仅改 `ellectric/api/server.py`，不动 handlers/schemas/tools/frontend。
