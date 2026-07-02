---
id: task-07
title: 更新 SSE payload 与 prompt 契约测试
author: lmr
created_at: 2026-07-03 01:21:50
priority: P1
depends_on: [task-04, task-05]
blocks: [task-08]
requirement_ids: [FR-03, FR-04]
decision_ids: [D-003@v1, D-004@v1]
allowed_paths:
  - tests/test_chat_streaming_events.py
  - tests/test_agent_prompt.py
goal: >
  用测试锁定 fallback payload 的 metrics_meta/report_status，以及 Agent prompt 的 today guard 文案。
implementation:
  - 更新 fake tool_result payload 增加 metrics_meta 和 report_status。
  - 断言 SSE payload 原样透传新增字段。
  - 新增 prompt static test，断言今天/实时/数据集最新可用日规则。
acceptance:
  - SSE 测试覆盖 new payload fields。
  - Prompt 测试无需调用真实 LLM。
  - 所有测试可离线运行。
verify:
  - PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_chat_streaming_events.py tests/test_agent_prompt.py -q
constraints:
  - 不请求 DeepSeek API。
  - 不把 prompt 测试写成脆弱的整段字符串匹配。
