---
id: task-06
title: 新增 catalog API smoke 测试（FR-01, FR-02, FR-03, FR-09, D-005@v1）
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-04]
blocks: [task-13]
requirement_ids: [FR-01, FR-02, FR-03, FR-09]
decision_ids: [D-005@v1]
allowed_paths: [tests/test_api_catalog.py]
---
## goal
验证 `/capabilities`、`/datasets`、`/reports`、`/reports/{report_id:path}` 返回正确结构与状态码；确认路由未被 StaticFiles 捕获；确认旧路由不变。
## implementation
tests/test_api_catalog.py:
1. **Fixture** — `TestClient(app)` from `ellectric.api.server`。
2. **TestCapabilitiesEndpoint** — 200, list, id/title/category/description/example_questions。
3. **TestDatasetsEndpoint** — 200, list, id/title/description/source/available。
4. **TestReportsEndpoint** — 200, list, id/title/report_type/status/summary。
5. **TestReportDetailEndpoint** — 已知 id → 200 ReportDetail；未知 → 200 status="missing"。
6. **TestRouteOrderGuardsStaticFiles** — `GET /nonexistent-path` 不返回 HTML。
7. **TestOldRoutesUnaffected** — `GET /health` 返回 200 + ok。
## acceptance
- 四端点 200 + body 符合 schema；缺失 report_id → status="missing"
- StaticFiles 未干扰 API 路由；`/health` 不变
## verify
```bash
python -m pytest tests/test_api_catalog.py -q
```
## constraints
- 使用 FastAPI TestClient，不启动 uvicorn
- verify route order before static mount
- 不修改生产代码，不依赖外部网络
