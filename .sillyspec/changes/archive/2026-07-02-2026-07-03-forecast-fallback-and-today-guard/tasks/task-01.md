---
id: task-01
title: 扩展报告指标元信息 schema
author: lmr
created_at: 2026-07-03 01:21:50
priority: P0
depends_on: []
blocks: [task-02, task-03, task-05, task-06]
requirement_ids: [FR-01, FR-04]
decision_ids: [D-001@v1, D-004@v1]
allowed_paths:
  - ellectric/service/schemas.py
goal: >
  为 ReportSummary/ReportDetail 增加可选 metrics_meta，使指标能携带 label/unit 且保持旧 metrics 兼容。
implementation:
  - 在 ReportSummary 增加 metrics_meta 默认空 dict。
  - 类型保持宽松为 dict[str, dict[str, str]] 或等价 Pydantic 可序列化结构。
  - 确保 ReportDetail 继承字段，无需重复定义。
acceptance:
  - 旧 reports 不传 metrics_meta 时 API 仍返回空对象或默认值。
  - JSON schema 中可见 metrics_meta 字段。
  - 不改变 ForecastResponse 或 /predict schema。
verify:
  - PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_api_catalog.py -q
constraints:
  - 不把单位塞进 metrics value。
  - 不重命名已有 ReportSummary 必填字段。
