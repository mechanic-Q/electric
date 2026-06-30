---
id: task-07
title: 新增模块文档 renewable-forecaster.md
author: lmr
created_at: 2026-06-30 11:29:30
priority: P2
depends_on: [task-01, task-02]
blocks: []
requirement_ids: [FR-01, FR-02]
decision_ids: [D-002@v1]
allowed_paths:
  - docs/Ellectric/modules/renewable-forecaster.md
---

goal: >
  记录 wind/solar forecaster 的定位、契约、关键逻辑和边界。
implementation:
  - 新建 module card，说明 wind/solar targets
  - 记录 Tier1-4 特征与 weather 降级行为
  - 明确本轮不接入 RL observation space
acceptance:
  - 文档含 MANUAL_NOTES 标记
  - 文档列出 validation report 路径
  - 文档说明不修改 trading_env
verify:
  - rtk pytest tests/test_renewable_forecaster.py
constraints:
  - 不改其他模块卡
  - 不删除人工备注区域
