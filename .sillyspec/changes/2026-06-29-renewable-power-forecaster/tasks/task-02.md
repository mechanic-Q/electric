---
id: task-02
title: 实现 Tier1-4 特征构建与缺 weather 降级
author: lmr
created_at: 2026-06-30 11:29:30
priority: P0
depends_on: [task-01]
blocks: [task-06]
requirement_ids: [FR-04]
decision_ids: [D-004@v1]
allowed_paths:
  - ellectric/pipeline/renewable_forecaster.py
---

goal: >
  让 wind/solar forecaster 可复用 Tier1-3 与可选 Tier4 weather 特征。
implementation:
  - 调用 FeatureEngineer 构建 Tier1-3 基础特征
  - 优先加入 Tier4 weather columns
  - weather 不可用时保留 Tier1-3 并返回 degraded notes
acceptance:
  - weather cache 存在时 feature columns 含 weather 列
  - weather cache 缺失且 no-fetch 时不抛异常
  - degraded notes 能进入 validation report
verify:
  - rtk pytest tests/test_renewable_forecaster.py
constraints:
  - 不改 FeatureEngineer 公开签名
  - 不触网作为单元测试前提
  - 缺 weather 不阻塞 wind/solar baseline 训练
