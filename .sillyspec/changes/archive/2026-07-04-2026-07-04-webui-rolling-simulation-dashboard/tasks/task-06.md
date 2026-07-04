---
id: task-06
title: 新增前端 rolling dashboard 类型和 fetch 方法
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-01, task-04]
blocks: [task-07]
requirement_ids: [FR-01, FR-04, FR-05, FR-06]
decision_ids: [D-001@v1, D-003@v1, D-004@v1]
allowed_paths: [ellectric/web/src/types.ts, ellectric/web/src/api.ts]
---

goal: >
  Add typed WebUI access to the rolling demo endpoint using canonical Dashboard naming.
implementation:
  - Add TypeScript types mirroring the rolling demo response shape.
  - Add fetchRollingDemo() that calls /dashboard/rolling-demo through existing fetchJson.
  - Preserve existing capability, dataset, report, and chat API helpers.
acceptance:
  - RollingDemoResponse includes meta, series, panels, strategy, reports, warnings.
  - fetchRollingDemo returns Promise<RollingDemoResponse>.
  - No VVB naming appears in new frontend code.
verify:
  - cd ellectric/web && npm run build
constraints:
  - No npm dependencies.
  - Do not implement App rendering or charts in this task.
