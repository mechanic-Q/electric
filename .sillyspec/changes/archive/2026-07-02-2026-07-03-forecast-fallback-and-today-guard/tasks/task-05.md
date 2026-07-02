---
id: task-05
title: 更新 WebUI metrics label/unit 渲染
author: lmr
created_at: 2026-07-03 01:21:50
priority: P1
depends_on: [task-01, task-03]
blocks: [task-07]
requirement_ids: [FR-04]
decision_ids: [D-004@v1]
allowed_paths:
  - ellectric/api/static/index.html
goal: >
  让 result card 使用 metrics_meta 渲染可读指标名和单位，同时兼容旧 payload。
implementation:
  - 将 renderMetrics 扩展为接收 metricsMeta。
  - 有 meta 时显示 label 和 unit；没有 meta 时保留现有 key/value。
  - result card 显示 report_status/degraded 提示。
acceptance:
  - payload.metrics_meta 存在时 UI 文案不裸露 raw key。
  - 没有 metrics_meta 的旧报告不报错。
  - source=offline_report 仍显示。
verify:
  - PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_chat_streaming_events.py -q
constraints:
  - 不重做 WebUI 布局。
  - 不引入前端框架或构建步骤。
