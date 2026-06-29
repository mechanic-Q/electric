---
id: task-04
title: 更新 Weather Tier4 validation 单元测试
author: lmr
created_at: 2026-06-29 20:44:11
priority: P0
depends_on: [task-01, task-02, task-03]
blocks: [task-06]
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-06]
decision_ids: [D-001@v1, D-002@v1, D-003@v1]
allowed_paths: [tests/test_weather_tier4_validation.py]
---

goal: >
  新增测试覆盖 raw columns 不泄漏、feature_count 关系、
  metadata 新字段、Impact Conclusion。不触网、不写真实 reports。

implementation:
  - raw 泄漏：mock prepare_features，断言 X_weather 不含 rt_price 等
  - feature_count：已知 tier3 + weather count，断言等式
  - metadata schema：断言含 weather_source/input_rows/report_scope/log_path
  - Impact Conclusion：断言 Markdown 含段落及 delta 语义
  - 保持现有测试组不变

acceptance:
  - raw columns leakage 测试通过
  - feature_count 等式通过
  - metadata schema 通过
  - Impact Conclusion 段落通过
  - 全测试不依赖网络、不写真实 reports

verify:
  - rtk pytest tests/test_weather_tier4_validation.py

constraints:
  - mock/stub，不实例化真实 forecaster/loader
  - 伪造 weather 列以 temp_/ghi_/wind_speed_ 结尾
  - 不使用真实山东 parquet，不引入新外部依赖
