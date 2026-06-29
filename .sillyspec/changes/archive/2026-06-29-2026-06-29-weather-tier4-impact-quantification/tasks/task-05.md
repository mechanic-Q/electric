---
id: task-05
title: 更新 feature-engineer 模块文档
author: lmr
created_at: 2026-06-29 20:44:11
priority: P1
depends_on: [task-01, task-03]
blocks: []
requirement_ids: [FR-04, FR-05]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [docs/Ellectric/modules/feature-engineer.md]
---

goal: >
  更新 Weather Tier4 验证段落说明 ablation 隔离 weather
  特征不混 raw columns；产物路径；report-only 语义。

implementation:
  - 替换现有 Weather Tier4 验证段落
  - 对比 baseline (T1-3) vs weather (T1-3 + weather-only)
  - 产物路径：JSON/MD/log
  - 保留 hard_threshold_applied=false 及 MANUAL_NOTES

acceptance:
  - 说明 ablation 隔离天气特征而非 raw columns
  - 产物路径列出三条
  - 明确 report-only、无硬阈值
  - frontmatter 和 MANUAL_NOTES 完整保留

verify:
  - rtk pytest tests/test_weather_tier4_validation.py

constraints:
  - 只改 feature-engineer.md，新内容 ≤10 行
  - 不删 frontmatter/MANUAL_NOTES，不加代码示例
