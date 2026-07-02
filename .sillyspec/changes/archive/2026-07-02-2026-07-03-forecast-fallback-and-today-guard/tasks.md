---
author: lmr
created_at: 2026-07-03 01:16:03
---

# Tasks: Forecast Fallback Metrics + Today Guard

- [ ] task-01: 扩展报告指标元信息 schema
  - 覆盖：D-001@v1, D-004@v1
  - 文件：`ellectric/service/schemas.py`

- [ ] task-02: 修正 Weather Tier4 summary 指标映射
  - 覆盖：D-001@v1, D-002@v1
  - 文件：`ellectric/service/catalog.py`

- [ ] task-03: 修正 forecast fallback degraded 处理
  - 覆盖：D-002@v1
  - 文件：`ellectric/service/handlers.py`

- [ ] task-04: 增加 Agent today guard prompt
  - 覆盖：D-003@v1
  - 文件：`ellectric/llm/agent.py`

- [ ] task-05: 更新 WebUI metrics label/unit 渲染
  - 覆盖：D-004@v1
  - 文件：`ellectric/api/static/index.html`

- [ ] task-06: 更新服务层与 API 测试
  - 覆盖：D-001@v1, D-002@v1, D-004@v1
  - 文件：`tests/test_service_catalog.py`, `tests/test_api_catalog.py`

- [ ] task-07: 更新 SSE payload 与 prompt 契约测试
  - 覆盖：D-003@v1, D-004@v1
  - 文件：`tests/test_chat_streaming_events.py`，可新增 `tests/test_agent_prompt.py`

- [ ] task-08: targeted verification
  - 运行：`PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_service_catalog.py tests/test_api_catalog.py tests/test_chat_streaming_events.py -q`
  - 运行：`./.venv/bin/python -m compileall -q ellectric/service ellectric/llm ellectric/chat`
