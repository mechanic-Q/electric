---
id: task-07
title: 生成 sample output 与模块文档
author: lmr
created_at: 2026-06-30 11:36:18
priority: P2
depends_on: [task-02, task-05]
blocks: []
requirement_ids: [FR-07]
decision_ids: [D-001@v1, D-004@v1]
allowed_paths:
  - docs/Ellectric/modules/recommend.md
  - ellectric/reports/recommend/sample_output.md
---

goal: >
  固化 recommend 工具的使用样例和模块文档。
implementation:
  - 新增 recommend module card
  - 运行一次 sample 输出并保存 markdown
  - 文档说明学习用途和免责声明
acceptance:
  - sample_output.md 含 summary/actions/disclaimer
  - module card 含 MANUAL_NOTES
  - 文档说明不是真实交易建议
verify:
  - rtk pytest tests/test_recommend_handler.py
constraints:
  - 不提交真实 API key
  - 不生成真实交易指令
