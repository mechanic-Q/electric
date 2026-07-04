---
id: task-02
title: 新增山东 rolling demo 只读 service
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-01]
blocks: [task-03, task-04]
requirement_ids: [FR-04, FR-05, FR-06]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths: [ellectric/service/dashboard.py]
---

goal: >
  Build deterministic Shandong 15min rolling-demo payload from historical data with warnings-based degradation.
implementation:
  - Load Shandong data with forecasts for the requested UTC window, defaulting to 2025-10-01 and max 30 days.
  - Map available load, price, wind, solar, tie line, pumped storage, and forecast columns into aligned arrays.
  - Add lightweight panel summaries, strategy/report evidence when artifacts exist, and warnings for missing optional fields.
acceptance:
  - build_rolling_demo() returns 2880 timestamps and points_per_day=96 by default.
  - Missing optional fields produce warnings, not exceptions.
  - Returned values are JSON-serializable native Python types.
verify:
  - python -m pytest tests/test_dashboard_rolling_demo.py -q -k service
constraints:
  - Read-only: no training, no ASSUME simulation, no file writes.
  - No new dependencies beyond existing project packages.
