---
id: task-08
title: 执行验证并记录结果
author: lmr
created_at: 2026-07-03 17:06:03
priority: P0
depends_on: [task-06]
blocks: []
requirement_ids: [FR-007, FR-008, FR-009, FR-010, FR-011, FR-013]
decision_ids: [D-002@v2, D-003@v1, D-004@v1, D-005@v1]
allowed_paths:
  - ellectric/web/package.json
  - tests/test_api_catalog.py
  - tests/test_chat_streaming_events.py
  - tests/test_web_static.py
  - .sillyspec/changes/2026-07-03-webui-value-redesign/plan.md
---
## goal
- Verify full change: frontend build (FR-007), static page (FR-008), legacy routes (FR-009), SSE protocol (FR-010), risk copy (FR-011), degraded display (FR-013). Block merge on P0 failure.
## implementation
1. `cd ellectric/web && npm run build`; confirm exit 0 and `api/static/index.html` generated.
2. Run pytest on 3 test files; confirm all pass.
3. Manual: start FastAPI, `GET /` inspects Dashboard UI, check legacy routes registered, confirm no 实盘/下单/收益 copy.
4. Record pass/fail per check in plan.md or validation log.
## acceptance
- Build outputs `api/static/index.html`. `GET /` returns Dashboard-first page.
- Legacy routes (`/predict`, `/simulate`, `/backtest`, `/explain`, `/chat/stream`, `/capabilities`, `/datasets`, `/reports`) registered before StaticFiles.
- SSE events (`token`/`tool_call`/`tool_result`/`error`/`done`) handled.
- Dashboard shows Shandong data, forecast, strategy eval, explanation, report trace.
- No 实盘/下单/收益/交易建议 copy. Each P0 check listed pass/fail.
## verify
- `cd ellectric/web && npm run build`
- `python -m pytest tests/test_api_catalog.py tests/test_chat_streaming_events.py tests/test_web_static.py -q`
## constraints
- Execute commands, do not claim pass without running.
- Record failures with exact command and error summary.
- Do not modify application code — read-only verification.
