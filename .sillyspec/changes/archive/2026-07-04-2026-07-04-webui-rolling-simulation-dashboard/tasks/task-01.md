---
id: task-01
title: 新增 rolling dashboard Pydantic schema
author: lmr
created_at: 2026-07-04 08:34:54
priority: P0
depends_on: []
blocks: [task-02, task-04, task-06]
requirement_ids: [FR-04, FR-06]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths: [ellectric/service/schemas.py]
---

goal: >
  Define Pydantic DTOs for the read-only rolling dashboard payload without changing existing schemas.
implementation:
  - Add request, meta, series, panel, strategy, report evidence, and response models.
  - Default start to 2025-10-01 and constrain days to 1..30.
  - Use list defaults for aligned timestamps, numeric arrays, reports, and warnings.
acceptance:
  - RollingDemoResponse exposes meta, series, panels, strategy, reports, warnings.
  - RollingDemoRequest rejects days below 1 or above 30.
  - Existing schema classes stay unchanged.
verify:
  - python -m pytest tests/test_dashboard_rolling_demo.py -q -k schema
constraints:
  - Pydantic v2 BaseModel only.
  - No service, API, loader, or training imports in schemas.py.
