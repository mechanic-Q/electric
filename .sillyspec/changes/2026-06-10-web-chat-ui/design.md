---
author: lmr
created_at: 2026-06-10T12:00:00+08:00
---

# Design — Web Chat UI (SSE 流式对话)

## 1. 背景

Ellectric 已完成 Phase 1-4：数据接入 → 预测 → 市场仿真 → API/CLI/LLM。当前 LLM agent（DeepSeek + LangChain）已能调用 `/predict`、`/simulate`、`/backtest` 三个核心能力，但用户只能通过 CLI `python -m ellectric.cli.main ask` 交互。

**问题**：缺少 Web 聊天界面，非技术人员无法便捷访问 AI 电力交易助手。

**目标**：零新 Python 依赖，构建 SSE 流式对话前端，复用现有 FastAPI + LangChain Agent。

## 2. 设计目标

- 纯 HTML/CSS/JS 单页聊天 UI，FastAPI `StaticFiles` 直接 serve
- SSE 流式逐 token 输出，工具调用状态实时可见
- 复用现有 `llm/agent.py`（ChatOpenAI）和 `llm/tools.py`（三个 tool），不重写
- 零新 Python 依赖包
- 移动端响应式适配

## 3. 非目标（YAGNI）

- 用户认证/登录
- 多轮对话历史持久化（仅内存）
- 多用户并发会话隔离
- WebSocket 双向推送
- 文件上传/图表内嵌生成
- 对话导出

## 4. 总体方案

### 架构

```
浏览器 (index.html)  ─POST /chat/stream─▶  FastAPI server.py
  fetch + ReadableStream                        │
  SSE text/event-stream                         ▼
                                         chat/streaming.py
                                         stream_chat(query, history)
                                           │
                                           ▼
                                         llm/agent.py
                                         create_agent_executor()
                                         ChatOpenAI(streaming=True)
                                           │
                                           ▼ astream_events()
                                         token → tool_call → tool_result → done
```

### SSE 事件协议

| 事件 type | 触发时机 | 前端处理 |
|-----------|----------|----------|
| `token` | LLM 逐 token 产出 | Markdown 渲染追加到气泡，闪烁光标 |
| `tool_call` | Agent 开始调用工具 | 显示黄色 spinner 状态标签 |
| `tool_result` | 工具调用完成 | 标签变绿 "完成" |
| `error` | 异常 | 红色错误卡片 |
| `done` | 流结束 | 移除光标，最终渲染 |

### 通信细节

- **请求**：`POST /chat/stream`，body `{ query: str, history: [{role, content}] }`
- **响应**：`text/event-stream`，每行 `data: <JSON>\n\n`
- **历史消息**：客户端管理 → 每次请求带完整上下文，服务端无状态

## 5. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| **新增** | `ellectric/chat/__init__.py` | 包标记 |
| **新增** | `ellectric/chat/streaming.py` | SSE 流式 agent 封装：`stream_chat()` async generator |
| **新增** | `ellectric/api/static/index.html` | 聊天 UI 单文件（CSS + JS 内联），电网调度终端风格 |
| **修改** | `ellectric/api/server.py` | 新增 `POST /chat/stream` SSE 端点 + `StaticFiles` mount `/` |
| **修改** | `ellectric/llm/agent.py` | `ChatOpenAI` 加 `streaming=True`，`create_agent_executor()` 参数化 model/temperature |

## 6. 接口定义

### 6.1 `ellectric/chat/streaming.py`

```python
from collections.abc import AsyncGenerator


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
    """
```

### 6.2 `ellectric/api/server.py` 新增端点

```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """POST body: {"query": str, "history": [...]}
    返回: text/event-stream"""
```

```python
# 新增请求模型 (在 schemas.py 或 server.py 内联)
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    query: str
    history: list[ChatMessage] = Field(default_factory=list)
```

### 6.3 `ellectric/llm/agent.py` 修改

```python
# 修改前
llm = ChatOpenAI(model="deepseek-v4-flash", ...)

# 修改后
llm = ChatOpenAI(
    model=os.environ.get("ELLECTRIC_LLM_MODEL", "deepseek-v4-flash"),
    api_key=api_key,
    base_url="https://api.deepseek.com/v1",
    temperature=0.3,
    streaming=True,  # 新增
)
```

## 7. 兼容策略（Brownfield）

| 维度 | 策略 |
|------|------|
| **新增端点不影响现有** | `/predict` `/simulate` `/backtest` `/explain` `/health` 代码不变，路由不变 |
| **agent.py 向后兼容** | `create_agent_executor()` 签名不变，`ask_agent()` 行为不变，仅内部加 `streaming=True`（非流式调用 `.invoke()` 不受影响） |
| **tools.py 不改** | 三个 tool 函数无任何修改 |
| **handlers.py 不改** | 业务 handler 无任何修改 |
| **静态文件不冲突** | `GET /` mount `StaticFiles`，API 路由在前，静态文件在后，API 优先匹配 |
| **未配置 API Key** | `/chat/stream` 返回 SSE error 事件 + 友好错误信息，不 crash |
| **回退** | 删除 `chat/` 目录 + server.py 新增行即可完全移除，零副作用 |

## 8. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|----------|
| R-01 | LangChain `astream_events()` 在 DeepSeek 上的兼容性（事件格式可能不同于 OpenAI） | P1 | 写 `streaming.py` 时做事件格式适配层，兼容 `on_chat_model_stream` 和 `on_llm_stream` 两种事件名 |
| R-02 | SSE 流中断时前端消息不完整（网络断开/API 超时） | P2 | 前端 `catch` 块显示错误卡片 + 保留已接收的 tokens，不清空 |
| R-03 | `marked.js` CDN 加载失败导致 Markdown 不渲染 | P2 | 检测 `typeof marked === 'undefined'`，fallback 为纯文本显示 |
| R-04 | FastAPI `StaticFiles` 与 API 路由优先级冲突 | P1 | API 路由先注册，`StaticFiles` 后注册。`/docs` `/redoc` 显式保留 |
| R-05 | DeepSeek API 流式响应的 `tool_calls` 增量事件格式 | P1 | 先以 `astream_events()` v2 API 实现，捕获 `on_tool_start` / `on_tool_end`。如不兼容，降级为非流式 tool calling + stream 输出文本 |

## 9. 自审

### 9.1 需求覆盖

| 需求 | 覆盖 | 说明 |
|------|------|------|
| 前端网页直接对话 | ✅ | `index.html` 单文件聊天 UI |
| 智能调用现有算法与数据 | ✅ | 复用三个 tool 不变，agent 自动决策调用 |
| 流式输出 | ✅ | SSE `text/event-stream` + `astream_events()` |
| 给出回答与建议 | ✅ | DeepSeek agent system prompt 已定义专业回答原则 |

### 9.2 约束一致性

- CONVENTIONS.md 模块级 docstring ✅ — `streaming.py` 将使用中英双语 docstring + `=====` 分隔
- CONVENTIONS.md logger 标准化 ✅ — `logger = logging.getLogger(__name__)`
- CONVENTIONS.md 类型标注 ✅ — 所有函数签名完整标注
- ARCHITECTURE.md 三明治架构 ✅ — API → Service → Pipeline，新增 chat 层在 API 和 LLM 之间，不破坏现有层次
- 数据合约 ✅ — 不涉及 DataFrame 列名变更

### 9.3 真实性

- `llm/agent.py:57` `ChatOpenAI` 类名正确 ✅
- `llm/tools.py:19` `_API_BASE` 变量名正确 ✅
- `api/server.py` FastAPI `app` 对象名正确 ✅
- 文件路径全部基于实际目录结构 ✅

### 9.4 YAGNI

- 无 WebSocket ✅
- 无数据库 ✅
- 无用户系统 ✅
- 无文件上传 ✅

### 9.5 验收标准（具体可测试）

1. 浏览器访问 `http://localhost:8000/` → 显示聊天 UI，欢迎状态 + 建议快捷按钮
2. 输入 "今天负荷预测" → SSE 流式输出 token，逐字渲染，带 Markdown 格式化
3. 输入 "仿真夏季高峰7天" → 工具调用时显示黄色标签，完成后变绿，随后输出分析文本
4. Enter 发送，Shift+Enter 换行 → 正常
5. `curl -X POST http://localhost:8000/predict ...` → 不受影响，返回不变
6. 移动端（375px 宽）→ 布局正常，输入框全宽

### 9.6 非目标清晰 ✅

明确列出 6 项不做的事。

### 9.7 兼容策略 ✅

7 项兼容检查全部可回退，零副作用。

### 9.8 风险识别 ✅

5 项风险 (P0/P1/P2)，每项有应对策略。最高风险是 DeepSeek streaming 兼容性（R-01/R-05），在代码实现阶段优先验证。

---

**自审结论：通过。** 设计覆盖全部需求，与现有架构和规范一致，风险可控。
