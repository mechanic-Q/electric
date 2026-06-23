---
author: lmr
created_at: 2026-06-10 16:31:10
id: task-03
title: 修改 api/server.py — 新增 /chat/stream 端点 + StaticFiles
priority: P0
estimated_hours: 1
depends_on: [task-01]
blocks: [task-04]
allowed_paths:
  - ellectric/api/server.py
---

# task-03: 修改 api/server.py — 新增 /chat/stream 端点 + StaticFiles

## 修改文件（必填）
- 修改 `ellectric/api/server.py`

## 实现要求

### 3.1 新增导入

```python
import json

from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
```

`stream_chat` 从 `ellectric.chat.streaming` 延迟导入（函数内），与 handlers.py 延迟导入模式一致。

### 3.2 新增 Pydantic 模型（内联于 server.py）

ChatRequest/ChatMessage 模型内联定义在 server.py 中，不修改 schemas.py。

```python
from pydantic import BaseModel, Field
from typing import Literal


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str
    history: list[ChatMessage] = Field(default_factory=list)
```

理由：该模型仅 server.py 使用，放入 schemas.py 会增加不必要的模块触及面。若后续 CLI/LLM tools 也需要该模型，再提取到 schemas.py。

### 3.3 新增 POST /chat/stream SSE 端点

```python
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE 流式对话端点。
    
    接收 ChatRequest {query, history}，返回 text/event-stream。
    通过 stream_chat() async generator 逐帧产出 SSE 事件。
    """
    from ellectric.chat.streaming import stream_chat

    return StreamingResponse(
        stream_chat(query=req.query, history=req.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
```

端点位置：插在 `/explain` 端点之后、`StaticFiles` mount 之前。

### 3.4 新增 StaticFiles 挂载 — 服务 index.html

```python
from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"

app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
```

`html=True` 使 FastAPI 自动 serve index.html 作为目录默认页。

**路由优先级**：FastAPI 先匹配显式注册的路由，再 fallback 到 `app.mount`。因此：
- API 端点（`/predict`、`/simulate`、`/backtest`、`/explain`、`/chat/stream`、`/health`、`/docs`、`/redoc`）优先于 StaticFiles
- `GET /` 无 API 路由匹配 → fallback 到 StaticFiles → 返回 `index.html`

验证路由优先级的方式：

```
注册顺序:
  1. @app.get("/health")          ← 显式路由
  2. @app.post("/predict")         ← 显式路由
  ...
  6. @app.post("/chat/stream")    ← 显式路由（新增）
  7. app.mount("/", StaticFiles)  ← 最后挂载，最低优先级
```

### 3.5 保持现有端点不变

所有现有端点（`/predict`、`/simulate`、`/backtest`、`/explain`、`/health`）不改代码、不改路由、不改签名。仅在它们之后追加新端点。

### 3.6 FastAPI docs_url/redoc_url 保持

`app = FastAPI(docs_url="/docs", redoc_url="/redoc")` 不变。这两个 URL 由 FastAPI 内部注册为显式路由，不会被 StaticFiles 拦截。

## 接口定义（代码类任务必填）

### POST /chat/stream

```
Method:      POST
Path:        /chat/stream
Request:     application/json
Response:    text/event-stream

Request Body:
{
    "query": "今天负荷预测是多少？",
    "history": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！我是 Ellectric 电力交易助手。"}
    ]
}

Response (SSE):
data: {"type":"token","content":"根据"}

data: {"type":"token","content":"最新"}

data: {"type":"token","content":"预测"}

data: {"type":"tool_call","tool":"query_forecast","args":{"model_type":"load","horizon":24}}

data: {"type":"tool_result","tool":"query_forecast","result":"..."}

data: {"type":"done"}
```

### ChatRequest / ChatMessage

```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]   # 消息角色
    content: str                          # 消息文本

class ChatRequest(BaseModel):
    query: str                            # 用户当前输入
    history: list[ChatMessage] = []       # 历史对话（可选，默认空列表）
```

### SSE 事件类型（stream_chat 产出的 JSON 行协议）

| type | data 字段 | 含义 |
|------|-----------|------|
| `token` | `{type, content}` | LLM 逐 token 文本 |
| `tool_call` | `{type, tool, args}` | 工具调用开始 |
| `tool_result` | `{type, tool, result}` | 工具调用完成 |
| `error` | `{type, message}` | 异常/错误 |
| `done` | `{type}` | 流正常结束 |

## 边界处理（必填）

1. **路由优先级 — StaticFiles 不吞 API 路由**：`app.mount` 在所有 `@app` 路由注册之后调用。FastAPI 按注册顺序匹配，显式路由优先级高于 mount。`/docs` `/redoc` 由 FastAPI 构造函数内的 OpenAPI 路由保障。

2. **DEEPSEEK_API_KEY 未配置**：`stream_chat()` 内部 `create_agent_executor()` 抛出 `RuntimeError`，streaming.py 捕获后 yield `{"type": "error", "message": "DEEPSEEK_API_KEY 未设置。请通过...获取"}` + `{"type": "done"}`。前端显示红色错误卡片，不 crash。

3. **stream_chat 模块缺失（task-01 未完成）**：延迟导入 `from ellectric.chat.streaming import stream_chat`，若模块不存在则抛出 `ImportError`，FastAPI 返回 500。仅在 task-01 完成后才启动服务，不是运行时边界。

4. **static/ 目录不存在**：`StaticFiles(directory=...)` 在启动时检查，若 `ellectric/api/static/` 不存在则 uvicorn 启动失败。需在 task-01 完成前先创建 `static/` 目录（至少放一个占位 index.html）。**本 task-03 不负责创建 index.html** — index.html 在 task-04 或由 frontend-design skill 产出。可先用占位文件 `static/index.html`（内容 `Chat UI loading...`）占位，使服务可启动。

5. **请求体校验失败**：Pydantic 自动校验 `ChatRequest`，若 `query` 缺失或类型错误，FastAPI 返回 422 Unprocessable Entity + JSON 错误详情，不会进入 SSE 流。

6. **SSE 连接中断（客户端断开）**：`stream_chat()` 的 `async for` 循环通过 `asyncio.CancelledError` 感知客户端断开，清理资源后正常退出。FastAPI `StreamingResponse` 原生支持此行为。

7. **并发请求**：每个 `POST /chat/stream` 创建独立的 agent 实例，无共享状态，天然支持并发。每个请求的 SSE 流独立。

## 非目标（本任务不做的事）

- 不创建 `ellectric/api/static/index.html`（由 task-04 或 frontend-design skill 负责）
- 不修改 `ellectric/service/schemas.py`（ChatRequest 内联在 server.py）
- 不修改 `ellectric/service/handlers.py`（chat 不经过 handler 层，直接在 server.py 调用 stream_chat）
- 不添加 CORS 中间件（不跨域，同源访问）
- 不实现 GET /chat/stream（SSE 用 POST 携带 JSON body）
- 不添加登录/鉴权中间件

## 参考

- design.md section 6.2 — `ellectric/api/server.py` 新增端点定义
- design.md section 7 — 兼容策略（路由优先级、API Key 缺失处理）
- design.md section 4 — SSE 事件协议（token / tool_call / tool_result / error / done）
- CONVENTIONS.md section 2.1 — 段落分隔符 `# ═══════════════════`
- CONVENTIONS.md section 2.3 — `logger = logging.getLogger(__name__)`
- CONVENTIONS.md section 2.2 — 所有函数签名完整类型标注
- handlers.py line 1-12 — 延迟导入模式（函数内 import pipeline 模块）
- agent.py line 57-62 — ChatOpenAI 当前参数（参考 streaming=True 新增位置，实际修改在 task-02）

## TDD 步骤

> 注：本项目无自动化测试框架。以下为手动验证步骤。

1. **写测试（curl 脚本）** → 启动 uvicorn 后执行 curl 验证
2. **确认失败** → task-03 代码写入前，`POST /chat/stream` 返回 404
3. **写代码** → 新增 ChatRequest 模型 + `/chat/stream` 端点 + StaticFiles mount
4. **确认通过** → curl 各端点 + 浏览器验证
5. **回归** → 旧端点 `/predict` `/simulate` `/backtest` `/explain` `/health` curl 验证不变

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| 1 | `curl -X POST http://localhost:8000/chat/stream -H "Content-Type: application/json" -d '{"query":"你好"}'` | 返回 `text/event-stream`，包含 `data:` 行（含 token 事件或 error 事件） |
| 2 | `curl http://localhost:8000/health` | 返回 `{"status":"ok","version":"0.1.0"}`（不变） |
| 3 | `curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"model_type":"load","horizon":24}'` | 返回 `ForecastResponse` JSON（不变） |
| 4 | `curl http://localhost:8000/docs` | 返回 Swagger UI HTML（不变） |
| 5 | `curl http://localhost:8000/redoc` | 返回 ReDoc HTML（不变） |
| 6 | `curl http://localhost:8000/` | 返回 `index.html`（若 static/ 有占位文件）或 404（若 static/ 不存在） |
| 7 | 发送 `POST /chat/stream` 不带 `query` 字段 | 返回 422 Unprocessable Entity |
| 8 | 未设置 `DEEPSEEK_API_KEY` 时请求 | SSE 返回 `{"type":"error","message":"DEEPSEEK_API_KEY 未设置..."}` + `{"type":"done"}`，不 crash |
