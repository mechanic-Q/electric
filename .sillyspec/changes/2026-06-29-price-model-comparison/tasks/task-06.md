---
id: task-06
title: 生成 JSON/MD/HTML/log 报告
author: lmr
created_at: 2026-06-30 11:33:15
priority: P0
depends_on: [task-04, task-05]
blocks: []
requirement_ids: [FR-06, FR-07]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/scripts/compare_price_models.py
  - ellectric/reports/price_comparison/
---

goal: >
  输出完整电价模型对比报告和残差可视化。
implementation:
  - 写 comparison.json 和 comparison.md
  - 用 Plotly 生成 residuals.html
  - tee full-run 日志到 comparison.log
acceptance:
  - 四个报告产物存在
  - Markdown 含 metrics 和 DM/GW 表
  - HTML 含 residual plots
verify:
  - python -m ellectric.scripts.compare_price_models --dataset shandong
constraints:
  - 报告写入 reports/price_comparison
  - 不写 /tmp 作为最终证据
