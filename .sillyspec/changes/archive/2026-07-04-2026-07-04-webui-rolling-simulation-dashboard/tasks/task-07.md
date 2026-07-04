---
id: task-07
title: 重构 WebUI 首屏为 rolling data theater
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-06]
blocks: [task-08, task-10]
requirement_ids: [FR-02, FR-03, FR-05, FR-08]
decision_ids: [D-002@v1, D-003@v1]
allowed_paths: [ellectric/web/src/App.tsx]
---

goal: >
  Replace the current directory-style dashboard with a rolling data theater driven by one read-only payload.
implementation:
  - Fetch rolling demo on mount and render loading, error, and degraded states.
  - Add frontend-only current tick, playing, speed, and progress state.
  - Lay out stage, modular panels, and the existing Copilot sidebar.
acceptance:
  - App initial data path calls fetchRollingDemo only.
  - Playback can pause, resume, change speed, and wrap through the window.
  - Copilot sidebar remains available.
verify:
  - rg "fetch(Capabilities|Datasets|Reports)|predict|simulate|backtest" ellectric/web/src/App.tsx
constraints:
  - No automatic /predict, /simulate, or /backtest calls.
  - Chart polish belongs to task-08.
