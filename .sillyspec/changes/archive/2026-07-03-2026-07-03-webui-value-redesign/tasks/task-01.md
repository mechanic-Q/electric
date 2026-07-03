---
id: task-01
title: 新增 Vite + React + TypeScript 前端工程骨架
author: lmr
created_at: 2026-07-03 17:06:03
priority: P0
depends_on: []
blocks: [task-02]
requirement_ids: [FR-007, FR-008]
decision_ids: [D-002@v2, D-005@v1]
allowed_paths: [ellectric/web/package.json, ellectric/web/vite.config.ts, ellectric/web/tsconfig.json, ellectric/web/index.html, ellectric/web/src/main.tsx, ellectric/web/src/vite-env.d.ts, ellectric/api/static/index.html]
---
goal: >
  Create the minimal React/Vite/TypeScript source tree whose build output replaces the static FastAPI index page.
implementation:
  - Add package scripts and Vite config with outDir `../api/static` and relative asset base.
  - Add TypeScript config, HTML root, React entrypoint, and Vite env types.
  - Keep the scaffold dependency-light: React, React DOM, TypeScript, Vite only.
acceptance:
  - `npm run build` generates `ellectric/api/static/index.html` plus assets.
  - Generated index contains a script reference to built assets.
  - No backend route or API semantics change in this task.
verify:
  - cd ellectric/web && npm run build
  - test -f ellectric/api/static/index.html
constraints:
  - No UI library or state library.
  - Build output must go to `../api/static`.
  - Do not alter FastAPI business API semantics.
