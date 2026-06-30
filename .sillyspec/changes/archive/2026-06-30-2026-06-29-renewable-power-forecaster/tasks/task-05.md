---
id: task-05
title: 扩展 API/CLI/LLM forecast 查询入口
author: lmr
created_at: 2026-06-30 11:29:30
priority: P1
depends_on: [task-04]
blocks: []
requirement_ids: [FR-06]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/api/server.py
  - ellectric/cli/main.py
  - ellectric/llm/tools.py
---

goal: >
  将 wind/solar 预测暴露给 REST、CLI 和 LLM forecast 工具。
implementation:
  - 确认 `/predict` 自动接收扩展 schema
  - 扩展 CLI forecast 参数帮助文本
  - 更新 `query_forecast` docstring 说明 wind/solar 可选
acceptance:
  - `forecast wind 24` 和 `forecast solar 24` 可调用
  - `/predict` 旧 load/price 请求不变
  - LLM tool 描述包含 wind/solar
verify:
  - python -m ellectric.cli.main forecast wind 24
  - python -m ellectric.cli.main forecast solar 24
constraints:
  - 不新增 LLM agent 工具，只扩展已有 query_forecast
  - 不改变 `/predict` 路径
