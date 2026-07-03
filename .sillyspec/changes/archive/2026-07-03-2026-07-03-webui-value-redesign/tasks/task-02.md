---
id: task-02
title: 实现前端 API/SSE 类型与 fetch client
author: lmr
created_at: 2026-07-03 17:06:03
priority: P0
depends_on: [task-01]
blocks: [task-03, task-04]
requirement_ids: [FR-002, FR-004, FR-006, FR-009, FR-010, FR-013]
decision_ids: [D-004@v1, D-005@v1]
allowed_paths: [ellectric/web/src/types.ts, ellectric/web/src/api.ts]
---
goal: >
  Provide typed frontend access to existing catalog/report endpoints and `/chat/stream` without changing backend JSON contracts.
implementation:
  - Define loose TS mirror types for capabilities, datasets, reports, report detail, and chat events.
  - Implement fetch helpers for `/capabilities`, `/datasets`, `/reports`, `/reports/{id}`.
  - Implement chunked SSE parsing for token/tool_call/tool_result/error/done events.
acceptance:
  - `ReportSummary.status` includes `ok`, `missing`, `error`, and `degraded`.
  - Fetch helpers accept `AbortSignal` and tolerate optional/extra fields.
  - `streamChat` dispatches each complete SSE `data:` line to a typed callback.
verify:
  - cd ellectric/web && npm run build
constraints:
  - Mirror backend JSON loosely, not as a new backend schema.
  - Preserve `/chat/stream` event protocol: token/tool_call/tool_result/error/done.
  - Do not modify backend Python code.
