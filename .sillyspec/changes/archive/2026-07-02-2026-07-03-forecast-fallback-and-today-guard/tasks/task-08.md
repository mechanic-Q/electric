---
id: task-08
title: targeted verification
author: lmr
created_at: 2026-07-03 01:21:50
priority: P0
depends_on: [task-06, task-07]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1]
allowed_paths:
  - .sillyspec/changes/2026-07-03-forecast-fallback-and-today-guard/verify-result.md
goal: >
  运行 targeted pytest 和 compileall，确认 fallback 修复与 today guard 计划实现可验证。
implementation:
  - 运行 service/API/SSE/prompt targeted tests。
  - 运行 compileall 覆盖 service/llm/chat。
  - 将命令和结果写入 verify-result.md。
acceptance:
  - targeted pytest 全部通过。
  - compileall 通过。
  - verify-result.md 记录命令、结果和剩余风险。
verify:
  - PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_service_catalog.py tests/test_api_catalog.py tests/test_chat_streaming_events.py tests/test_agent_prompt.py -q
  - ./.venv/bin/python -m compileall -q ellectric/service ellectric/llm ellectric/chat
constraints:
  - 不运行长耗时训练/全量 RL 测试。
  - 不提交代码。
