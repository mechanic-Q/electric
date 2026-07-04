---
id: task-10
title: 运行 WebUI build 并确认首屏不调用重型端点
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-07, task-08]
blocks: []
requirement_ids: [FR-02, FR-03, FR-05, FR-07, FR-08]
decision_ids: [D-002@v1, D-003@v1, D-004@v1]
allowed_paths: []
---

goal: >
  Verify the WebUI builds and the first screen uses only fetchRollingDemo as its automatic data source.
implementation:
  - Run the Vite/TypeScript build from ellectric/web.
  - Search App.tsx for fetchRollingDemo usage.
  - Search App.tsx initial load path for predict, simulate, or backtest calls.
acceptance:
  - npm run build exits 0.
  - App imports and calls fetchRollingDemo.
  - App initial render path does not call heavy endpoints.
verify:
  - cd ellectric/web && npm run build
  - rg "fetchRollingDemo|predict|simulate|backtest" ellectric/web/src/App.tsx
constraints:
  - Verification-only; no source edits.
  - Failure means implementation tasks must fix code before completion.
