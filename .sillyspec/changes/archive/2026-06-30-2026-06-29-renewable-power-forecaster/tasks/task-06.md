---
id: task-06
title: 新增 validate_renewable_forecaster.py 与报告产物
author: lmr
created_at: 2026-06-30 11:29:30
priority: P0
depends_on: [task-01, task-02, task-03]
blocks: []
requirement_ids: [FR-05, FR-07]
decision_ids: [D-001@v1, D-004@v1]
allowed_paths:
  - ellectric/scripts/validate_renewable_forecaster.py
  - ellectric/reports/renewable_forecaster/
---

goal: >
  在山东全量数据上生成 wind/solar 预测验证报告和日志证据。
implementation:
  - 新增 validation CLI，支持 --no-fetch 与 output-dir
  - 运行 wind/solar full-run，记录 metrics 和 degraded notes
  - 写 JSON/Markdown/log 三产物
acceptance:
  - JSON 含 wind/solar metrics 与 metadata.input_rows
  - Markdown 说明 weather 是否可用
  - log 写入 reports 目录，不写 /tmp
verify:
  - python -m ellectric.scripts.validate_renewable_forecaster --no-fetch
constraints:
  - 不伪造 full-run 指标
  - 不触网作为最终验证默认路径
