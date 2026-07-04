---
id: task-03
title: 添加后端 rolling demo 测试
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: [task-01, task-02]
blocks: [task-09]
requirement_ids: [FR-04, FR-05, FR-06]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths: [tests/test_dashboard_rolling_demo.py]
---

goal: >
  Prove the rolling demo service and endpoint return the contracted payload without heavy side effects.
implementation:
  - Add tests for default payload shape, 2880 rows, 96 points per day, and Shandong source.
  - Add tests for days bounds and warnings when data/artifacts are missing.
  - Assert the endpoint path is read-only and does not require training or ASSUME calls.
acceptance:
  - Default service/API payload includes all six top-level keys.
  - days=0 fails and days>30 is rejected by validation.
  - Missing-data path returns warnings instead of crashing.
verify:
  - python -m pytest tests/test_dashboard_rolling_demo.py -q
constraints:
  - Tests must stay fast and deterministic.
  - Edit only the new test file.
