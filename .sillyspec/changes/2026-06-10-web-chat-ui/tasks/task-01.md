---
author: lmr
created_at: 2026-06-10 16:31:10
id: task-01
title: 新增 chat/streaming.py — SSE 流式 agent 封装
priority: P0
estimated_hours: 3
depends_on: []
blocks: [task-03]
allowed_paths:
  - ellectric/chat/
---

# task-01: 新增 chat/streaming.py — SSE 流式 agent 封装

## 修改文件（必填）
- 新增 `ellectric/chat/__init__.py`
- 新增 `ellectric/chat/streaming.py`

## 实现要求

基于 design.md 6.1 节接口定义，在 `ellectric/chat/streaming.py` 中实现 `stream_chat()` async generator。

### 核心逻辑

1. 从环境变量读取 `DEEPSEEK_API_KEY`，未设置时 yield error 事件（不抛异常，保证 API 端点不 crash）
2. 调用 `llm/agent.py` 的 `create_agent_executor()` 获取 CompiledStateGraph 实例
3. 通过 `agent.astream_events()` 遍历 LangChain v2 流式事件
4. 将 `astream_events()` 产出的事件映射为 5 种 SSE 事件类型并 yield

### SSE 事件协议（design.md 4.1 节）

所有 SSE 帧格式：`data: <JSON>\n\n`

| 事件 type | JSON payload | 触发条件 |
|-----------|-------------|----------|
| `token` | `{"type": "token", "content": "文"}` | `on_chat_model_stream` 事件中的 delta token |
| `tool_call` | `{"type": "tool_call", "name": "query_forecast", "args": {...}}` | `on_tool_start` 事件 |
| `tool_result` | `{"type": "tool_result", "name": "query_forecast", "content": "..."}` | `on_tool_end` 事件 |
| `error` | `{"type": "error", "message": "..."}` | 任何异常（API Key 缺失、网络错误、agent 调用失败） |
| `done` | `{"type": "done"}` | 流正常结束 |

### 事件适配层（应对 R-01/R-05 风险）

`astream_events()` 在 DeepSeek 上的事件名称可能与 OpenAI 不同。实现时做适配：

- **token 流**：优先匹配 `on_chat_model_stream`，回退匹配 `on_llm_stream`
- **工具调用**：优先匹配 `on_tool_start` / `on_tool_end`，回退匹配 `on_chat_model_start` 中的 `tool_calls` 增量
- **未识别事件**：debug 日志记录，静默跳过，不中断流

### 前置 spike-01（plan.md 要求，task-01 开始前执行）

在正式编写 `streaming.py` 之前，先写 10 分钟快速验证脚本确认 DeepSeek `ChatOpenAI(streaming=True)` 的 `astream_events()` 实际产出的事件名称和结构：

```python
# spike-01 验证脚本（临时，不提交）
import asyncio, os
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

async def main():
    llm = ChatOpenAI(
        model="deepseek-v4-flash",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
        temperature=0.3,
        streaming=True,
    )
    agent = create_agent(model=llm, tools=[], system_prompt="你是助手")
    async for event in agent.astream_events(
        {"messages": [HumanMessage(content="你好")]},
        version="v2",
    ):
        print(f"[{event['event']}] {list(event.keys())}")
        if event['event'] == 'on_chat_model_stream':
            chunk = event['data']['chunk']
            if hasattr(chunk, 'content') and chunk.content:
                print(f"  → token: {chunk.content}")

asyncio.run(main())
```

验证通过标准：能看见 `on_chat_model_stream` 事件，且 `chunk.content` 有 token 文本。

若 DeepSeek 不产出 `on_chat_model_stream` 事件（降级方案）：改用非流式 tool calling + 仅流式输出最终文本（`agent.astream()` 逐 message 输出）。

## 接口定义（代码类任务必填）

### `ellectric/chat/streaming.py`

```python
"""
SSE 流式 Agent 封装 —— 将 LangChain agent 输出转为 Server-Sent Events 流。
=============================================================

通过 astream_events() 监听 agent 执行过程，逐事件产出
token / tool_call / tool_result / error / done 五种 SSE 帧。

~~~~
架构位置
~~~~~~~~

  API 层 (/chat/stream 端点)
    → chat/streaming.py  (本模块 — async generator)
      → llm/agent.py     (create_agent_executor)
        → llm/tools.py   (三个 tool 函数)

~~~~
SSE 事件协议
~~~~~~~~~~~~

  帧格式: "data: <JSON>\n\n"
  事件类型: token | tool_call | tool_result | error | done

"""
import json
import logging
import os
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage

from ellectric.llm.agent import create_agent_executor

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════════

def _sse_frame(data: dict) -> str:
    """将 dict 编码为单行 SSE 帧。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _validate_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """校验并过滤历史消息，仅保留 role 为 user/assistant 的消息。"""
    ...


# ═══════════════════════════════════════════════════════════════════
# 核心生成器
# ═══════════════════════════════════════════════════════════════════

async def stream_chat(
    query: str,
    history: list[dict[str, str]] | None = None,
) -> AsyncGenerator[str, None]:
    """SSE 流式对话生成器。

    通过 astream_events() 逐事件产出 SSE 格式的 JSON 行。
    事件类型：token / tool_call / tool_result / error / done。

    Args:
        query: 用户当前输入
        history: 历史消息列表 [{"role": "user|assistant", "content": "..."}]

    Yields:
        "data: <JSON>\n\n" 格式的 SSE 帧

    Example:
        async for frame in stream_chat("今天负荷预测"):
            # frame == 'data: {"type":"token","content":"今"}\n\n'
            ...
    """
    ...
```

### `ellectric/chat/__init__.py`

```python
"""
Chat 包 —— Web 聊天 UI 后端支持。
==============================

streaming.py — SSE 流式 agent 封装
"""
```

## 边界处理（必填）

| # | 边界场景 | 输入 | 预期行为 |
|---|---------|------|----------|
| 1 | query 为空字符串 | `query=""` | yield `{"type": "error", "message": "查询不能为空"}`，不调用 agent |
| 2 | DEEPSEEK_API_KEY 未设置 | 环境变量缺失 | yield `{"type": "error", "message": "DEEPSEEK_API_KEY 未设置..."}`，不 crash |
| 3 | history 为 None | `history=None` | 默认 `[]`，正常执行 |
| 4 | history 含非法 role | `[{"role": "system", "content": "x"}]` | 过滤掉非 user/assistant 的消息，debug 日志记录 |
| 5 | history 含空 content | `[{"role": "user", "content": ""}]` | 保留消息（空 content 合法），不特殊处理 |
| 6 | astream_events() 产出未识别事件类型 | 未知 event name | `logger.debug()` 记录，静默跳过，不中断流 |
| 7 | DeepSeek API 调用中途异常 | 网络断开 / 超时 | catch Exception，yield `{"type": "error", "message": "..."}`，流结束 |
| 8 | agent 返回空 messages | `result["messages"]` 为空列表 | yield error 事件 "Agent 返回空响应" |
| 9 | token content 为空字符串 | chunk.content == "" | 跳过该帧，不 yield token 事件 |
| 10 | 同一 tool 多次调用 | agent 连续调用 query_forecast 两次 | 每次独立产出 tool_call + tool_result 事件对 |

## 非目标（本任务不做的事）

- 不修改 `ellectric/llm/agent.py` — 那是 task-02
- 不创建 FastAPI 端点 — 那是 task-03
- 不做前端 HTML/CSS/JS — 那是 task-03 的 StaticFiles 部分
- 不引入新 Python 依赖（零新包）
- 不做对话历史持久化（纯内存）
- 不做多用户并发会话隔离

## 参考

- design.md 6.1 节 — `stream_chat()` 接口定义
- design.md 6.3 节 — `create_agent_executor()` 修改预览（task-02 执行）
- design.md 8 节 — R-01/R-05 风险应对策略
- plan.md Spike 前置验证 — spike-01 验证脚本
- `ellectric/llm/agent.py` — 现有 agent 实现，`create_agent_executor()` 返回 CompiledStateGraph
- `ellectric/llm/tools.py` — 三个 tool 函数签名
- `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md` — 模块 docstring 格式、logger 标准化、段落分隔符

## TDD 步骤

1. **写验证脚本** `ellectric/chat/_verify_stream.py`：创建 agent → `astream_events()` → 打印事件名列表
2. **确认失败**：当前不存在 `chat/` 目录，脚本报 ImportError
3. **写代码**：创建 `__init__.py` + `streaming.py`，实现 `stream_chat()`
4. **确认通过**：运行 `_verify_stream.py`，观察实际事件名，确认 `stream_chat()` 产出正确的 5 种 SSE 事件
5. **回归**：确认 `ellectric/llm/agent.py` 无任何修改（task-02 的范围），确认 `ellectric/` 其他模块不受影响

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| 1 | 创建 `ellectric/chat/` 目录，含 `__init__.py` 和 `streaming.py` | 文件存在，`python -c "import ellectric.chat.streaming"` 无报错 |
| 2 | 执行 spike-01 验证脚本 | 确认 DeepSeek `astream_events()` 实际事件名，记录在 task-01 关闭注释中 |
| 3 | `stream_chat("你好", history=[])` 直接调用（不经过 HTTP） | 逐 token yield SSE 帧，最后 yield `done` 事件 |
| 4 | `stream_chat("仿真夏季高峰7天")` 触发 tool calling | 产出 `tool_call` → `tool_result` → token → `done` 事件序列 |
| 5 | `stream_chat("", history=[])` 空查询 | 仅产出单条 `error` 事件，不调用 agent |
| 6 | 临时 `unset DEEPSEEK_API_KEY` 后调用 `stream_chat()` | 产出 `error` 事件，不抛异常 |
| 7 | 模块 docstring 符合 CONVENTIONS.md | `=====` 下划线分隔标题，`~~~~` 波浪线分隔段落，中英双语 |
| 8 | `logger = logging.getLogger(__name__)` 存在于 streaming.py | getLogger 调用存在 |
