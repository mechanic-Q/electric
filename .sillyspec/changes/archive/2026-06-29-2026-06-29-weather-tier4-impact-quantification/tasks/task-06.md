---
id: task-06
title: 运行 targeted tests 与 full-run 生成报告证据
author: lmr
created_at: 2026-06-29 20:44:11
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05]
blocks: []
requirement_ids: [FR-05]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths:
  - ellectric/reports/weather_tier4/weather_tier4_validation.json
  - ellectric/reports/weather_tier4/weather_tier4_validation.md
  - ellectric/reports/weather_tier4/weather_tier4_impact.log
---

goal: >
  全量山东 15min 数据产生真实报告证据，非 degraded/fake-scale，
  日志留 reports 目录。

implementation:
  - 确认本地 weather cache 存在
  - rtk pytest 通过后 --no-fetch full-run，tee 日志到 reports
  - 确认 JSON/MD/log 三产物存在且内容真实

acceptance:
  - rtk pytest exits 0
  - JSON metadata.input_rows ≈ 71520, report_scope=full_dataset, weather_source 非 degraded
  - weather_columns 为真实 weather 列，MD 含 Impact Conclusion
  - 产物均在 ellectric/reports/weather_tier4/

verify:
  - rtk pytest tests/test_weather_tier4_validation.py
  - python ellectric/scripts/validate_weather_tier4.py --no-fetch --output-dir ellectric/reports/weather_tier4 2>&1 | tee ellectric/reports/weather_tier4/weather_tier4_impact.log

constraints:
  - 必须 --no-fetch，日志 tee 到 reports，不入 /tmp
  - 不提交 degraded/fake-scale 产物
  - 测试失败或 full-run 报错先修复，不跳过
  - 不修改代码（task-01~05 已完成）
