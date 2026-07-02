---
id: task-03
title: 修正 forecast fallback degraded 处理
author: lmr
created_at: 2026-07-03 01:21:50
priority: P0
depends_on: [task-02]
blocks: [task-06]
requirement_ids: [FR-02, FR-05]
decision_ids: [D-002@v1, D-003@v1]
allowed_paths:
  - ellectric/service/handlers.py
goal: >
  允许 ok/degraded Weather Tier4 报告作为负荷预测 fallback，并在 payload/note 中明确报告状态。
implementation:
  - 将 build_forecast_fallback 的 status 过滤改为 ok/degraded allowlist。
  - 在返回 dict 中加入 report_status 和 metrics_meta。
  - degraded 时 note 追加“离线报告降级，指标可能不完整”。
acceptance:
  - FileNotFoundError 缺模型时返回 status=fallback。
  - degraded report 不被误判为 error。
  - missing/error report 仍返回 None。
verify:
  - PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_service_catalog.py -q
constraints:
  - 不吞掉非模型缺失异常。
  - 不改变 fallback_reason=model_missing 语义。
