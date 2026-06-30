---
id: task-07
title: 可选扩展 service/CLI 支持 price DNN model_type
author: lmr
created_at: 2026-06-30 11:33:15
priority: P2
depends_on: [task-01]
blocks: []
requirement_ids: []
decision_ids: [D-004@v1]
allowed_paths:
  - ellectric/service/schemas.py
  - ellectric/service/handlers.py
  - ellectric/cli/main.py
---

goal: >
  在不改变 LEAR 默认行为的前提下暴露 price_dnn 可选路径。
implementation:
  - 扩展 model_type enum 或 CLI 参数帮助
  - handler 分派 price_dnn 到 DNN forecaster
  - 保持 price 默认仍为 LEAR
acceptance:
  - 默认 price forecast 仍走 LEAR
  - price_dnn 为 opt-in
  - CLI 帮助文本说明差异
verify:
  - python -m ellectric.cli.main forecast price 24
constraints:
  - 若集成风险高可跳过并记录在 plan/verify
  - 不改 `/predict` 路径
