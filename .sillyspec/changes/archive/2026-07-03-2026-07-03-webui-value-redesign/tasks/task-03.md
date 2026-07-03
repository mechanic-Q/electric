---
id: task-03
title: 实现 Dashboard-first 页面结构
author: lmr
created_at: 2026-07-03 17:06:03
priority: P0
depends_on: [task-02]
blocks: [task-05]
requirement_ids: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006]
decision_ids: [D-001@v1]
allowed_paths: [ellectric/web/src/App.tsx, ellectric/web/src/styles.css]
---
goal: >
  Make the first screen a value dashboard for data, forecasts, strategy evaluation, explainability, and report traceability.
implementation:
  - Build dashboard sections for Shandong data asset, value chain, Forecast Lab, Strategy Evaluation, Explainability, and Reports/Data.
  - Render existing `/capabilities`, `/datasets`, and `/reports` data through task-02 client.
  - Add responsive styling: desktop dashboard plus side panel, mobile single column.
acceptance:
  - Dashboard content is primary and visible before Copilot.
  - Forecast, strategy, explanation, and report cards include source/status markers.
  - Missing reports or models degrade locally without blanking the page.
verify:
  - cd ellectric/web && npm run build
constraints:
  - No new backend endpoint or `/dashboard-summary`.
  - Mobile must remain readable.
  - Do not add external fonts, icons, UI kits, or state libraries.
