---
id: task-05
title: 新增 CLI recommend 子命令
author: lmr
created_at: 2026-06-30 11:36:18
priority: P1
depends_on: [task-01, task-02]
blocks: []
requirement_ids: [FR-05]
decision_ids: [D-001@v1]
allowed_paths:
  - ellectric/cli/main.py
---

goal: >
  让用户可从 CLI 获取结构化交易建议。
implementation:
  - 新增 recommend 命令
  - 参数包含 date、horizon、risk_preference
  - 用 Rich 或 JSON 输出 summary/actions
acceptance:
  - `recommend 2026-01-15 --horizon 24` 可运行
  - 输出含 disclaimer
  - 旧 CLI 命令不变
verify:
  - python -m ellectric.cli.main recommend 2026-01-15 --horizon 24
constraints:
  - 不调用 LLM
  - 不做真实交易下单
