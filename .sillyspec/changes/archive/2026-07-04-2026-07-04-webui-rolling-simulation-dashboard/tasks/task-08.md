---
id: task-08
title: 实现原生 SVG/CSS 图表和响应式样式
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-07]
blocks: [task-10]
requirement_ids: [FR-02, FR-03, FR-07]
decision_ids: [D-002@v1, D-004@v1]
allowed_paths: [ellectric/web/src/App.tsx, ellectric/web/src/styles.css, ellectric/web/package.json]
---

goal: >
  Render line, heatmap, area, and ranking visuals with native SVG/CSS and responsive layout.
implementation:
  - Add minimal SVG/CSS chart components fed by the shared playhead.
  - Style rolling stage, panels, warnings, heatmap, bars, and mobile layout.
  - Check package.json remains dependency-unchanged.
acceptance:
  - Load, price, renewable, strategy, and evidence panels render without TypeScript errors.
  - Playhead visually drives all panels.
  - Mobile layout keeps Copilot from covering the stage.
verify:
  - cd ellectric/web && npm run build
constraints:
  - Do not add Plotly, ECharts, Recharts, or any chart dependency.
  - package.json is read-only unless build scripts already require no change.
