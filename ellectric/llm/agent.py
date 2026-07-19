"""LangChain Agent 引擎 —— 自然语言电力交易助手。

通过 DeepSeek Chat API + 工具调用实现智能问答。
封装为简单的函数接口，供 CLI/chat.py 调用。

LangChain agent engine for natural language electricity trading assistant.
"""

import json
import logging
import os
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ellectric.llm.tools import (
    query_capabilities,
    query_datasets,
    query_reports,
    read_report,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是 Ellectric 展示型解说员，面向第一次接触 AI + 电力交易的访问者。"
    "这个网页是展示性 WebUI，不是生产交易系统，也不实时运行预测、仿真、回测或交易。"
    "它播放的是已预先生成的山东 15min 历史数据与离线报告结果。\n\n"
    "你要用通俗易懂的中文解释页面内容和术语，像给技术小白做展厅讲解。"
    "可以解释 XGBoost、LEAR、电价预测、负荷预测、PPO/SAC/TD3、SHAP、日前/实时电价、"
    "风电光伏出力、策略回放、离线报告等概念。\n\n"
    "可用工具只用于查询能力清单、数据集信息、离线报告目录和报告详情。"
    "如果用户问具体报告结论，优先用工具读取离线报告后回答，并说明来源是离线报告。"
    "如果用户要求你现场运行预测、市场仿真、回测或交易推荐，必须说明展示模式不运行实时计算，"
    "可以改为解释这些功能的原理、页面中预生成数据的含义，或查询离线报告。\n\n"
    "回答规则：\n"
    "- 不编造实时数据、今天数据或未在报告中出现的数字\n"
    "- 山东 15min 数据集是历史数据，不代表真实今天或实时市场\n"
    "- 解释术语时先用一句话讲清楚，再补充它在本项目里上下游怎么用\n"
    "- 对普通访问者友好，避免堆砌公式；必要时用类比\n"
    "- 保持专业边界：这是学习展示，不是投资或交易建议"
)


def _resolve_deepseek_key() -> str | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    auth_path = Path.home() / ".local" / "share" / "opencode" / "auth.json"
    if not auth_path.exists():
        return None
    try:
        data = json.loads(auth_path.read_text())
    except Exception as exc:  # noqa: BLE001
        logger.debug("读取 opencode auth.json 失败: %s", exc)
        return None
    provider = data.get("deepseek") or {}
    return provider.get("key")


def create_agent_executor():
    """创建并返回一个 LangChain agent（CompiledStateGraph）。"""
    api_key = _resolve_deepseek_key()
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY 未设置。\n"
            "请通过 https://platform.deepseek.com 获取 API Key，然后设置环境变量：\n"
            "  export DEEPSEEK_API_KEY='your-key-here'\n"
            "或在 .env 文件中添加：\n"
            "  DEEPSEEK_API_KEY=your-key-here"
        )

    model_name = os.environ.get("ELLECTRIC_LLM_MODEL", "deepseek-v4-flash")
    base_url = os.environ.get("ELLECTRIC_LLM_BASE_URL", "https://api.deepseek.com/v1")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,  # type: ignore[arg-type]
        base_url=base_url,
        temperature=0.3,
        streaming=True,
    )

    return create_agent(
        model=llm,
        tools=[
            query_capabilities,
            query_datasets,
            query_reports,
            read_report,
        ],
        system_prompt=_SYSTEM_PROMPT,
    )


def ask_agent(query: str) -> str:
    """向 agent 发送一条自然语言查询，返回回答文本。"""
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
