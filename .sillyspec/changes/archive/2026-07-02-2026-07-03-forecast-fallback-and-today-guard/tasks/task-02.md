---
id: task-02
title: 修正 Weather Tier4 summary 指标映射
author: lmr
created_at: 2026-07-03 01:21:50
priority: P0
depends_on: [task-01]
blocks: [task-03, task-06]
requirement_ids: [FR-01, FR-02]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths:
  - ellectric/service/catalog.py
goal: >
  让 Weather Tier4 summary 从真实报告字段输出语义化 MAE 指标和 metrics_meta，避免裸 key/错误数字误导。
implementation:
  - 在 _weather_tier4_summary 中输出 mae_baseline_tier3、mae_weather_tier4、mae_delta_pct。
  - 为上述 key 输出 label/unit 元信息。
  - 保留报告原始 status；degraded 时 summary 说明质量限制。
acceptance:
  - list_reports(report_type="weather_tier4") 返回 semantic metrics keys。
  - get_report("weather_tier4/validation") 继承同一 metrics/meta。
  - missing/error 报告仍容错返回，不抛异常。
verify:
  - PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_service_catalog.py -q
constraints:
  - 不修改原始 JSON 报告文件。
  - 不扩大到 price/RL report 全面迁移。
