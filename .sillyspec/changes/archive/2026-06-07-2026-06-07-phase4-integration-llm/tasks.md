---
author: lmr
created_at: 2026-06-07 23:46:10
---

# Tasks: Phase 4 — Integration + LLM Interface

> 任务细节在 plan 阶段展开。此处仅列名称和对应文件。

## Wave 1: Service Layer + Dependencies

| # | 任务 | 文件 |
|---|------|------|
| T-01 | Phase 4 依赖声明 | `ellectric/requirements-phase4.txt` |
| T-02 | Pydantic Schemas | `ellectric/service/schemas.py` |
| T-03 | Handler 函数实现 | `ellectric/service/handlers.py` |

## Wave 2: API + CLI

| # | 任务 | 文件 |
|---|------|------|
| T-04 | FastAPI 服务 | `ellectric/api/server.py` |
| T-05 | CLI 命令工具 | `ellectric/cli/main.py` |
| T-06 | API 启动脚本与验证 | 手动验证 `uvicorn` 启动 + `curl` 测试 |

## Wave 3: LLM Interface

| # | 任务 | 文件 |
|---|------|------|
| T-07 | LangChain Tools | `ellectric/llm/tools.py` |
| T-08 | LangChain Agent | `ellectric/llm/agent.py` |
| T-09 | 交互式对话入口 | `ellectric/llm/chat.py` |
| T-10 | LLM 集成到 CLI | `ellectric/cli/main.py` (追加 `ask` 命令) |

## 依赖关系

```
Wave 1 (T-01 → T-02 → T-03)
         │
         ▼
Wave 2 (T-04 ─┬─ T-05)
              │
              ▼
         T-06 (验证)
              │
              ▼
Wave 3 (T-07 → T-08 → T-09 → T-10)
```
