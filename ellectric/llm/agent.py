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
    query_forecast,
    query_reports,
    read_report,
    recommend_trade,
    run_backtest,
    run_simulation,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是 Ellectric 电力交易助手，一个专业、准确的中文电力市场助手。"
    "你的能力包括：\n"
    "1. 查询负荷、电价、风电、光伏预测结果\n"
    "2. 运行电力市场仿真并解读出清价格、调度和利润\n"
    "3. 运行历史回测并对比 persistence、mean、oracle、PPO、SAC、TD3 策略\n"
    "4. 生成结构化交易建议并解释证据、风险和免责声明\n"
    "5. 查询能力清单、山东/OWID/Chinese 数据集元信息和离线报告目录\n"
    "6. 读取 Weather Tier4、风光预测、RL 全量评估、价格模型对比、SHAP 等离线报告\n\n"
    "遵循原则：\n"
    "- 基于真实数据回答，不编造数字\n"
    "- 所有数字必须标注来源：实时 API 预测、离线报告或历史数据统计\n"
    "- 如果工具返回 source=offline_report 或 fallback_reason，必须说明这是离线报告回退，不得说成实时预测\n"
    "- 回答简洁、专业，使用中文\n"
    "- 如果工具调用失败，明确告知用户错误原因\n"
    "- 不要回答超出自身能力范围的问题\n"
    "- 时间口径规则：山东 15min 数据集是历史数据，覆盖到 2026-01-14 前后，不代表真实今天。"  # noqa: E501
    "用户说'今天/当前/实时'时，不能编造真实今天预测值；"
    "必须说明数据集是历史数据，询问用户是否使用数据集最新可用日（2026-01-14）或指定具体历史日期。"
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
            query_forecast,
            run_simulation,
            run_backtest,
            recommend_trade,
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
