---
author: lmr
created_at: 2026-06-07 23:55:29
id: task-08
title: LangChain Agent
priority: P1
estimated_hours: 1.5
depends_on: [task-07]
blocks: [task-09]
allowed_paths:
  - ellectric/llm/agent.py
---

# task-08: LangChain Agent

## 修改文件

- **新增**: `ellectric/llm/agent.py`

## 实现要求

1. 创建 `ellectric/llm/agent.py`，实现一个 `create_agent()` 工厂函数和一个 `ask_agent(query) → str` 入口函数
2. 使用 langchain `ChatOpenAI` 调用 DeepSeek Chat API（兼容 OpenAI SDK 格式）
3. 挂载 3 个工具（从 `tools.py` import）：`query_forecast`, `run_simulation`, `run_backtest`
4. 系统 prompt 全中文，描述助手身份（Ellectric 电力交易助手）和能力范围
5. `temperature=0.3`：偏低温度保证事实性回答，避免虚构数据
6. 使用 `create_tool_calling_agent` + `AgentExecutor`（verbose=False）
7. 工具调用结果格式异常时，由 agent 自行推理内容，不做外部校验
8. 文件头部：模块 docstring（中文+English）说明用途 + logging 初始化

## 接口定义（pseudocode）

```python
# ellectric/llm/agent.py

"""LangChain Agent 引擎 —— 自然语言电力交易助手。

通过 DeepSeek Chat API + 工具调用实现智能问答。
封装为简单的函数接口，供 CLI/chat.py 调用。

LangChain agent engine for natural language electricity trading assistant.
"""

import logging
import os

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from ellectric.llm.tools import query_forecast, run_simulation, run_backtest

logger = logging.getLogger(__name__)


def create_agent() -> AgentExecutor:
    """创建并返回一个 LangChain AgentExecutor。

    使用 DeepSeek Chat API（兼容 OpenAI SDK 格式）作为 LLM，
    挂载预测/仿真/回测三个工具。系统 prompt 为中文。
    如遇 API Key 缺失，抛出 RuntimeError。

    Returns:
        已装配工具的 AgentExecutor 实例

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

    tools = [query_forecast, run_simulation, run_backtest]

    system_prompt = (
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

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False)


def ask_agent(query: str) -> str:
    """向 agent 发送一条自然语言查询，返回回答文本。

    每次调用创建一个新的 agent 实例（无状态，适合 CLI 单次查询）。

    Args:
        query: 用户的自然语言问题，例如 "昨天峰值负荷是多少？"

    Returns:
        Agent 回答的文本字符串

    Raises:
        RuntimeError: 传播自 create_agent() 的 Key 缺失异常
        Exception: DeepSeek API 调用失败等
    """
    agent = create_agent()
    result = agent.invoke({"input": query})
    output = result.get("output", "")
    if not output:
        logger.warning("Agent 返回空 output，完整 result: %s", result)
        output = "抱歉，我无法回答这个问题。请重试或换个方式提问。"
    return output
```

## 边界处理（必填，≥5）

| # | 场景 | 处理方式 |
|---|------|---------|
| E-01 | `DEEPSEEK_API_KEY` 环境变量未设置 | `create_agent()` 入口立即检查，抛出 `RuntimeError` 附带中英文 setup 指引 |
| E-02 | DeepSeek API 不可达（网络/GFW/服务宕机） | `ChatOpenAI` 调用抛出 `openai.APIConnectionError` / `openai.RateLimitError` / `openai.APIStatusError`；不在此文件做特殊捕获——由 caller（chat.py / cli）统一兜底处理；但 `create_agent()` 的 docstring 标注可能抛出的 exception 类型 |
| E-03 | Agent `invoke()` 返回格式异常（缺少 `output` key） | `ask_agent()` 使用 `.get("output", "")` 安全取值；若空则记录 `logger.warning` + 返回友好 fallback 文本 |
| E-04 | `tools.py` import 失败（task-07 未完成） | 由 Python `ImportError` 自然传播 —— 表明依赖缺失，不在这里静默处理 |
| E-05 | `temperature=0.3` 设置的语义 | 固定参数而非环境变量 —— 不暴露给用户配置，保证事实性回答基调 |
| E-06 | DeepSeek API Key 无效/过期（401） | `openai.AuthenticationError` 由 caller 捕获并输出 `"API Key 认证失败，请检查 DEEPSEEK_API_KEY"` |
| E-07 | Agent 返回内容含工具调用中间步骤（verbose=False） | `AgentExecutor(verbose=False)` 确保 `invoke()` 输出仅含最终回答，不暴露内部 chain 日志 |

## 非目标（本任务不做的事）

- 不做对话历史管理（`chat_history` 虽在 prompt 中预留 `MessagesPlaceholder` 但保持 `optional=True` —— 无状态，每次查询独立）
- 不实现流式输出（streaming tokens）—— 单次 invoke 返回完整回答
- 不包含 RAG / chromadb / embedding —— 无知识库检索
- 不实现 `chat.py`（task-09 负责交互式循环）
- 不在 agent.py 中处理 DeepSeek API 异常细节 —— 仅标注 exception 类型，由 caller 层（cli/chat.py）统一处理
- 不做 prompt 模板的热更新或版本管理 —— 硬编码在代码中

## TDD 步骤

1. **确认目录**: `ellectric/llm/__init__.py` 存在（task-07 已创建）；不存在则创建空文件
2. **实现 agent.py**: 写入 `create_agent()` + `ask_agent()`
3. **单元测试 - import**:
   ```bash
   python -c "from ellectric.llm.agent import create_agent, ask_agent"
   ```
4. **单元测试 - RuntimeError on missing key**:
   ```bash
   unset DEEPSEEK_API_KEY
   python -c "from ellectric.llm.agent import create_agent; create_agent()"
   ```
   预期抛出 `RuntimeError` 包含 "DEEPSEEK_API_KEY 未设置"
5. **单元测试 - ask_agent fallback on empty output**: mock `agent.invoke` 返回 `{"output": ""}`，验证 `ask_agent` 返回 fallback 字符串 "抱歉，我无法回答..."
6. **集成测试 - 真实 API 调用（可选）**:
   ```bash
   export DEEPSEEK_API_KEY='sk-xxx'
   python -c "from ellectric.llm.agent import ask_agent; print(ask_agent('今天负荷预测是多少？'))"
   ```
   需要 FastAPI 已启动 + 有效 API Key。结果应包含可读中文。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `cat ellectric/llm/agent.py \| head -5` | 文件以模块 docstring（中文+英文三引号）开头 |
| AC-02 | `python -c "from ellectric.llm.agent import create_agent, ask_agent"` | 无 ImportError，两个对象均可 callable |
| AC-03 | `unset DEEPSEEK_API_KEY && python -c "from ellectric.llm.agent import create_agent; create_agent()" 2>&1` | 抛出 `RuntimeError`，stderr 包含 "DEEPSEEK_API_KEY 未设置" |
| AC-04 | `python -c "from ellectric.llm.agent import ask_agent; import inspect; src=inspect.getsource(ask_agent); assert '.get(' in src; assert 'logger.warning' in src"` | `ask_agent()` 内部使用 `.get()` 安全取值 + `logger.warning` 记录异常 |
| AC-05 | `grep -c 'temperature=0.3' ellectric/llm/agent.py` | 返回 `1`（temperature 固定为 0.3） |
| AC-06 | `grep 'system_prompt' ellectric/llm/agent.py && grep '你是 Ellectric 电力交易助手' ellectric/llm/agent.py` | 系统 prompt 包含中文身份描述，不含英文 |
| AC-07 | `grep 'verbose=False' ellectric/llm/agent.py` | `AgentExecutor` 以 `verbose=False` 创建 |
| AC-08 | `git diff --stat ellectric/pipeline/` | 无变更（pipeline 零改动验证） |
