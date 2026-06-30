---
id: task-03
title: 新增 compare_price_models.py 脚本骨架与统一数据切分
author: lmr
created_at: 2026-06-30 11:33:15
priority: P0
depends_on: []
blocks: [task-04, task-05, task-06]
requirement_ids: [FR-02, FR-03]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/scripts/compare_price_models.py
---

goal: >
  新增山东电价模型对比脚本，统一加载数据和时间切分。
implementation:
  - 加载 ShandongDataLoader price columns
  - 构建统一 train/test split
  - 定义 comparison result schema
acceptance:
  - 脚本支持 --dataset shandong
  - 四模型共享同一测试区间
  - 可 dry-run 输出 metadata
verify:
  - rtk pytest tests/test_compare_price_models.py
constraints:
  - 不引入海外数据集
  - 不改变 price_loader 行为
