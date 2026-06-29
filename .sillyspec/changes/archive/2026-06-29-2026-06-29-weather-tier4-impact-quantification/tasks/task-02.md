---
id: task-02
title: 扩展 validation metadata 与 JSON 报告结构
author: lmr
created_at: 2026-06-29 20:44:11
priority: P0
depends_on: [task-01]
blocks: [task-04, task-06]
requirement_ids: [FR-03, FR-06]
decision_ids: [D-001@v1, D-003@v1, D-004@v1]
allowed_paths: [ellectric/scripts/validate_weather_tier4.py]
---

goal: >
  run_validation() metadata 增加 data_source, weather_source,
  input_rows, report_scope, log_path，旧字段保留。

implementation:
  - data_source 固定 "shandong"，weather_source 来自 resolve_weather_source()
  - input_rows = len(load_df)，report_scope = full_dataset|custom_range
  - log_path 来自 CLI 或传参（测试场景可为 null）
  - run_validation() 签名不变，JSON _json_serializer 已支持新类型

acceptance:
  - metadata 含 data_source=shandong, weather_source, input_rows, report_scope, log_path
  - 旧字段（generated_at/data_version/time_config/start/end）未删
  - run_validation() 签名兼容旧消费者

verify:
  - rtk pytest tests/test_weather_tier4_validation.py

constraints:
  - 只改 run_validation() 和 report writer，不动 ablation
  - JSON 只增不删，Markdown 只加行不删行
  - 旧参数保持兼容
