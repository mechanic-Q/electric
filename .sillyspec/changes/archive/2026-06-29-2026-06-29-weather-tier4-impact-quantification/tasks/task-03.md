---
id: task-03
title: 增强 Markdown Impact Conclusion
author: lmr
created_at: 2026-06-29 20:44:11
priority: P0
depends_on: [task-02]
blocks: [task-04, task-06]
requirement_ids: [FR-04]
decision_ids: [D-001@v1]
allowed_paths: [ellectric/scripts/validate_weather_tier4.py]
---

goal: >
  _write_markdown_report() 新增 Impact Conclusion 段落：
  delta 负→weather 改善，正→退化；report-only 无硬阈值；
  degraded 时说明不可用但 baseline 可读。

implementation:
  - 在 Delta 与 Interpretation 间插入 Impact Conclusion
  - 可用：输出 delta 正负语义，引用 hard_threshold_applied=false
  - degraded：说明特征不可用，baseline 仍可信

acceptance:
  - Markdown 含 Impact Conclusion 段落
  - weather 可用：说明 delta 含义、report-only
  - weather degraded：说明不可用、baseline 可读
  - 不硬编码阈值

verify:
  - rtk pytest tests/test_weather_tier4_validation.py

constraints:
  - 不改 run_validation()/run_ablation_experiment() 签名
  - 不改 JSON schema（Impact Conclusion 仅 Markdown）
  - 只改 validate_weather_tier4.py
