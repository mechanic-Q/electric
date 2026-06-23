---
author: lmr
created_at: 2026-06-10 16:25:35
---

# Tasks — Web Chat UI

> 任务细节在 plan 阶段展开。

## 任务列表

| # | 任务 | 涉及文件 |
|---|------|----------|
| 1 | 新增 `chat/streaming.py` — SSE 流式 agent 封装 | `ellectric/chat/__init__.py`, `ellectric/chat/streaming.py` |
| 2 | 修改 `llm/agent.py` — ChatOpenAI 加 streaming=True | `ellectric/llm/agent.py` |
| 3 | 修改 `api/server.py` — 新增 `/chat/stream` SSE 端点 + StaticFiles | `ellectric/api/server.py` |
| 4 | 验证端到端流式对话（手动测试 + curl） | 所有变更文件 |
