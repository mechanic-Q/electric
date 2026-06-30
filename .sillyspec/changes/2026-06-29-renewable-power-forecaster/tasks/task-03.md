---
id: task-03
title: 新增 renewable forecaster 单元测试骨架与 fake data
author: lmr
created_at: 2026-06-30 11:29:30
priority: P0
depends_on: [task-01]
blocks: [task-04, task-06]
requirement_ids: [FR-08]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths:
  - tests/test_renewable_forecaster.py
---

goal: >
  建立快速单元测试覆盖 wind/solar forecaster 的基础契约。
implementation:
  - 新建 fake 15min DataFrame，含 wind/solar actual 与 forecast 列
  - 测试 wind/solar target 列识别与 metrics schema
  - 测试 nRMSE 分母为 0 的边界
acceptance:
  - 测试不依赖真实山东 CSV
  - 测试不触网
  - `rtk pytest tests/test_renewable_forecaster.py` 可运行
verify:
  - rtk pytest tests/test_renewable_forecaster.py
constraints:
  - 不写真实 reports
  - 不训练重模型
