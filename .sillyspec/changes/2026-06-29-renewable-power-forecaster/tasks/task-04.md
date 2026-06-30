---
id: task-04
title: 扩展 service schema/handler 支持 model_type wind|solar
author: lmr
created_at: 2026-06-30 11:29:30
priority: P1
depends_on: [task-01, task-03]
blocks: [task-05]
requirement_ids: [FR-06]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/service/schemas.py
  - ellectric/service/handlers.py
---

goal: >
  让 service 层可通过现有 forecast 请求分派 wind/solar 预测。
implementation:
  - 扩展 forecast request model_type 允许 wind/solar
  - 在 forecast handler 中分派 renewable forecaster
  - 保持 load/price 分支不变
acceptance:
  - load/price forecast 测试仍通过
  - wind/solar 返回 ForecastResponse 兼容结构
  - 缺列时返回清晰错误或 degraded 信息
verify:
  - rtk pytest tests/test_renewable_forecaster.py
constraints:
  - 不新增独立 recommend 或 trading endpoint
  - 不修改 API 路径
