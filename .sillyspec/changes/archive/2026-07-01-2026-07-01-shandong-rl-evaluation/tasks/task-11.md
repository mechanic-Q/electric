---
id: task-11
title: 归档阶段同步模块卡片
author: lmr
created_at: 2026-07-01 23:40:18
priority: P2
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06, task-07, task-08, task-09, task-10]
blocks: []
requirement_ids: []
decision_ids: [D-003@v1]
allowed_paths: [.sillyspec/docs/Ellectric/modules/backtester.md, .sillyspec/docs/Ellectric/modules/rl-trainer.md, .sillyspec/docs/Ellectric/modules/trading-env.md]
---
goal: >
  归档阶段同步模块卡片，记录统一评估框架且明确 trading-env 行为不变。
implementation:
  - backtester.md 补充新指标与 evaluation artifacts 职责。
  - rl-trainer.md 补充评估层使用 RLAgentFactory.load 加载 checkpoint。
  - trading-env.md 记录 reward/action/obs 不变，仅作为评估环境。
  - 保留 MANUAL_NOTES 区域原样。
acceptance:
  - 三份模块卡片描述与实现一致。
  - MANUAL_NOTES_START/END 内容未被覆盖。
  - sillyspec modules status 仍可读取模块索引。
verify:
  - sillyspec modules status
constraints:
  - 仅在 archive/文档同步阶段执行。
  - 不改 Python 源码。
  - 不覆盖人工备注。
