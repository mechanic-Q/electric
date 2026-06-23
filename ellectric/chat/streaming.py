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

~~~~
事件适配层
~~~~~~~~~~

  astream_events() 在 DeepSeek 上的事件名称可能与 OpenAI 不同，
  token 流优先匹配 on_chat_model_stream，回退匹配 on_llm_stream。
  工具调用优先匹配 on_tool_start / on_tool_end，回退匹配
  on_chat_model_start 中的 tool_calls 增量。

"""
import json
import logging
import os
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage

from ellectric.llm.agent import create_agent_executor

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════════

def _sse_frame(data: dict) -> str:
    """将 dict 编码为单行 SSE 帧。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _validate_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """校验并过滤历史消息，仅保留 role 为 user/assistant 的消息。

    Args:
        history: 原始历史消息列表

    Returns:
        过滤后的历史消息列表，非法 role 被移除并记录 debug 日志
    """
    if not history:
        return []
    valid: list[dict[str, str]] = []
    for msg in history:
        role = msg.get("role", "")
        if role in ("user", "assistant"):
            valid.append(msg)
        else:
            logger.debug("过滤非法历史消息 role=%s, content=%s", role, msg.get("content", "")[:50])
    return valid


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
            # frame == 'data: {"type":"token","content":"今"}\\n\\n'
            ...
    """

    # ── 边界: query 为空 ──
    if not query or not query.strip():
        yield _sse_frame({"type": "error", "message": "查询不能为空"})
        return

    # ── 边界: API Key 缺失 ──
    if not os.environ.get("DEEPSEEK_API_KEY"):
        yield _sse_frame({
            "type": "error",
            "message": "DEEPSEEK_API_KEY 未设置，请先配置环境变量",
        })
        return

    # ── 校验历史消息 ──
    validated_history = _validate_history(history)

    try:
        agent = create_agent_executor()

        # ── 构建消息列表 ──
        messages = []
        for msg in validated_history:
            role = msg["role"]
            if role == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif role == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=query))

        # ── 通过 astream_events() 遍历 LangChain v2 流式事件 ──
        async for event in agent.astream_events(
            {"messages": messages},
            version="v2",
        ):
            event_name = event.get("event", "")

            # ── token 流: on_chat_model_stream 优先，on_llm_stream 回退 ──
            if event_name in ("on_chat_model_stream", "on_llm_stream"):
                chunk = event.get("data", {}).get("chunk")
                if chunk is not None and hasattr(chunk, "content"):
                    content = chunk.content
                    # 边界: token content 为空则跳过
                    if content:
                        yield _sse_frame({"type": "token", "content": content})

            # ── 工具调用开始: on_tool_start ──
            elif event_name == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                yield _sse_frame({
                    "type": "tool_call",
                    "name": tool_name,
                    "args": tool_input,
                })

            # ── 工具调用结束: on_tool_end ──
            elif event_name == "on_tool_end":
                tool_name = event.get("name", "unknown")
                tool_output = event.get("data", {}).get("output", "")
                # output 可能是 ToolMessage，取 content
                if hasattr(tool_output, "content"):
                    tool_output = tool_output.content
                yield _sse_frame({
                    "type": "tool_result",
                    "name": tool_name,
                    "content": str(tool_output),
                })

            # ── 未识别事件: debug 日志，静默跳过 ──
            else:
                logger.debug("跳过未识别事件: event=%s, keys=%s", event_name, list(event.keys()))

        # ── 流正常结束 ──
        yield _sse_frame({"type": "done"})

    except Exception as exc:
        # ── 边界: 任何异常 → yield error，不抛出 ──
        logger.error("stream_chat 异常: %s", exc)
        yield _sse_frame({"type": "error", "message": str(exc)})
