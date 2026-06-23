---
author: lmr
created_at: 2026-06-10 16:25:35
---

# Proposal — Web Chat UI (SSE 流式对话)

## 动机

Ellectric 已完成 4 阶段开发，具备负荷预测、电价预测、市场仿真、策略回测、模型解释等核心算法能力，并已通过 FastAPI + LangChain/DeepSeek 对外暴露 API 和 CLI 接口。但当前缺少 Web 图形界面——用户必须通过命令行 `python -m ellectric.cli.main ask` 或直接调用 API 才能使用 AI 电力交易助手。

构建一个 Web 聊天前端，让用户通过浏览器即可自然语言对话，智能调用现有算法与数据，获得数据驱动的交易建议。

## 关键问题

1. **CLI 门槛高**：当前仅 `ellectric cli ask` 支持 LLM 对话，要求用户安装 Python 环境、激活 venv，非技术人员完全无法使用
2. **流式体验缺失**：现有 `ask_agent()` 使用同步 `.invoke()`，用户需等待完整回复（仿真场景可能 30s+），无进度反馈
3. **工具调用不可见**：Agent 调用 `/predict` `/simulate` 等工具时，CLI 用户看不到中间状态，体验像"黑盒等待"

## 变更范围

- 新增 `GET /chat/stream` SSE 流式对话端点
- 新增 `ellectric/chat/streaming.py` — SSE 事件生成器
- 新增 `ellectric/api/static/index.html` — 聊天 UI 单文件
- 修改 `ellectric/api/server.py` — 注册新端点 + 挂载静态文件
- 修改 `ellectric/llm/agent.py` — `ChatOpenAI` 加 `streaming=True`

## 不在范围内（显式清单）

- 不做用户认证/登录
- 不做多轮对话历史持久化（仅客户端内存）
- 不做多用户并发会话隔离
- 不做 WebSocket 双向推送
- 不做文件上传/图表内嵌生成
- 不做对话导出

## 成功标准（可验证）

- 浏览器访问 `http://localhost:8000/` → 显示聊天 UI，欢迎状态可见
- 输入电力问题 → SSE 流式逐字输出，Markdown 渲染正常
- 触发工具调用（仿真/回测）→ 黄色状态标签出现，完成后变绿
- Enter 发送 / Shift+Enter 换行 → 正常
- 现有 API (`/predict` `/simulate` `/backtest` `/explain`) → 行为不变
- 移动端 (375px) → 布局正常
