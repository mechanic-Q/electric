"""LangChain Agent 引擎 —— 自然语言电力交易助手。

通过 DeepSeek Chat API + 工具调用实现智能问答。
封装为简单的函数接口，供 CLI/chat.py 调用。

LangChain agent engine for natural language electricity trading assistant.
"""

import logging
import os

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ellectric.llm.tools import query_forecast, run_simulation, run_backtest

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是 Ellectric 电力交易助手，一个专业、准确的中文电力市场助手。"
    "你的能力包括：\n"
    "1. 查询负荷预测和电价预测结果\n"
    "2. 运行电力市场仿真并解读结果\n"
    "3. 运行历史回测并对比交易策略表现\n\n"
    "遵循原则：\n"
    "- 基于真实数据回答，不编造数字\n"
    "- 回答简洁、专业，使用中文\n"
    "- 如果工具调用失败，明确告知用户错误原因\n"
    "- 不要回答超出自身能力范围的问题"
)


def create_agent_executor():
    """创建并返回一个 LangChain agent（CompiledStateGraph）。

    使用 DeepSeek Chat API（兼容 OpenAI SDK 格式）作为 LLM，
    挂载预测/仿真/回测三个工具。系统 prompt 为中文。
    如遇 API Key 缺失，抛出 RuntimeError。

    Returns:
        已装配工具的 CompiledStateGraph 实例

    Raises:
        RuntimeError: DEEPSEEK_API_KEY 未设置
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY 未设置。\n"
            "请通过 https://platform.deepseek.com 获取 API Key，然后设置环境变量：\n"
            "  export DEEPSEEK_API_KEY='your-key-here'\n"
            "或在 .env 文件中添加：\n"
            "  DEEPSEEK_API_KEY=your-key-here"
        )

    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        temperature=0.3,
    )

    return create_agent(
        model=llm,
        tools=[query_forecast, run_simulation, run_backtest],
        system_prompt=_SYSTEM_PROMPT,
    )


def ask_agent(query: str) -> str:
    """向 agent 发送一条自然语言查询，返回回答文本。

    每次调用创建一个新的 agent 实例（无状态，适合 CLI 单次查询）。

    Args:
        query: 用户的自然语言问题，例如 "昨天峰值负荷是多少？"

    Returns:
        Agent 回答的文本字符串

    Raises:
        RuntimeError: 传播自 create_agent_executor() 的 Key 缺失异常
        Exception: DeepSeek API 调用失败等
    """
    agent = create_agent_executor()
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    messages = result.get("messages", [])
    if not messages:
        logger.warning("Agent 返回空 messages，完整 result: %s", result)
        return "抱歉，我无法回答这个问题。请重试或换个方式提问。"
    output = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
    if not output:
        logger.warning("Agent 最后一条消息内容为空，完整 messages: %s", messages)
        return "抱歉，我无法回答这个问题。请重试或换个方式提问。"
    return output
