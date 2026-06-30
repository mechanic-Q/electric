---
id: task-06
title: 新增 LangChain recommend_trade tool 并注册到 agent
author: lmr
created_at: 2026-06-30 11:36:18
priority: P1
depends_on: [task-02, task-04]
blocks: []
requirement_ids: [FR-05]
decision_ids: [D-003@v1]
allowed_paths:
  - ellectric/llm/tools.py
  - ellectric/llm/agent.py
---

goal: >
  让 LLM 助手可通过 HTTP 调用 /recommend 并解释结构化结果。
implementation:
  - 新增 `@tool recommend_trade`
  - 注册到 agent tools 列表
  - docstring 明确 LLM 只能转述 evidence
acceptance:
  - tool 调用 /recommend
  - 网络失败返回中文错误
  - agent tools 包含 recommend_trade
verify:
  - rtk pytest tests/test_recommend_handler.py
constraints:
  - 不让 LLM 自行生成核心数值
  - 不新增外部 API key
