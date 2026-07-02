---
id: task-04
title: 增加 Agent today guard prompt
author: lmr
created_at: 2026-07-03 01:21:50
priority: P0
depends_on: []
blocks: [task-07]
requirement_ids: [FR-03, FR-05]
decision_ids: [D-003@v1]
allowed_paths:
  - ellectric/llm/agent.py
goal: >
  让 Agent 不把历史山东数据回答成真实今天预测，遇到今天/实时问题时主动澄清日期口径。
implementation:
  - 在 _SYSTEM_PROMPT 增加山东数据为历史数据的说明。
  - 增加“今天/当前/实时”不能编造真实预测的规则。
  - 要求用户确认使用数据集最新可用日或指定历史日期。
acceptance:
  - Prompt 中含 today guard 关键句。
  - 不影响 create_agent_executor 工具注册。
  - 无 DEEPSEEK_API_KEY 时既有错误提示仍可用。
verify:
  - ./.venv/bin/python -m compileall -q ellectric/llm
constraints:
  - 不改模型训练逻辑。
  - 不把 fallback 说成实时预测。
