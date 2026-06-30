"""
Phase 4+5 — FastAPI REST API 服务
==================================

5 个 POST 路由包装 Phase 1-5 核心功能：
- /predict    → 负荷/电价预测
- /simulate   → ASSUME 电力市场仿真
- /backtest   → 历史回测
- /explain    → SHAP 模型可解释性
- /chat/stream → SSE 流式对话（Phase 5 Web Chat UI）
- GET /        → 静态聊天界面

~~~~
架构层次
~~~~~~~~

  API 层 (server.py)  → 请求校验 (Pydantic) + 路由分发
  Chat 层              → streaming.py SSE agent 流式封装
  Service 层           → handlers.py 桥接 Pipeline 层
  Pipeline 层          → forecaster / backtester / shap_explainer / ASSUME

~~~~
启动命令
~~~~~~~~

  uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000

"""

import logging
import os

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from ellectric.service.schemas import (
    ForecastRequest,
    ForecastResponse,
    SimulateRequest,
    SimulateResponse,
    BacktestRequest,
    BacktestResponse,
    ExplainRequest,
    ExplainResponse,
    RecommendRequest,
    RecommendResponse,
)
from ellectric.service.handlers import (
    run_forecast,
    run_simulate,
    run_backtest,
    run_explain,
    run_recommend_trade,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 聊天请求/响应模型
# ═══════════════════════════════════════════════════════════════════


class ChatMessage(BaseModel):
    """历史消息。"""
    role: Literal["user", "assistant"] = Field(description="发送者角色")
    content: str = Field(description="消息内容")


class ChatRequest(BaseModel):
    """SSE 流式对话请求。"""
    query: str = Field(description="用户当前输入")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="历史消息列表。客户端维护会话上下文。",
    )


# ═══════════════════════════════════════════════════════════════════
# FastAPI 应用初始化
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Ellectric API",
    description="AI+电力交易技术学习平台 — Phase 4 Integration & Phase 5 Web Chat UI",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ═══════════════════════════════════════════════════════════════════
# 生命周期
# ═══════════════════════════════════════════════════════════════════


@app.on_event("startup")
def _log_startup():
    logger.info("Ellectric API v0.2.0 启动 — 端点: /predict, /simulate, /backtest, /explain, /recommend, /chat/stream")


# ═══════════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════════


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


# ═══════════════════════════════════════════════════════════════════
# 端点：SSE 流式对话（Phase 5）
# ═══════════════════════════════════════════════════════════════════


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """POST /chat/stream — SSE 流式对话。

    Body: {"query": "..., "history": [...]}
    Response: text/event-stream, 每行 data: <JSON>\n\n
    """
    from ellectric.chat.streaming import stream_chat

    return StreamingResponse(
        stream_chat(req.query, [m.model_dump() for m in req.history]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ═══════════════════════════════════════════════════════════════════
# 端点：预测
# ═══════════════════════════════════════════════════════════════════


@app.post("/predict", response_model=ForecastResponse)
def predict(req: ForecastRequest):
    return run_forecast(req)


# ═══════════════════════════════════════════════════════════════════
# 端点：市场仿真
# ═══════════════════════════════════════════════════════════════════


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    return run_simulate(req)


# ═══════════════════════════════════════════════════════════════════
# 端点：历史回测
# ═══════════════════════════════════════════════════════════════════


@app.post("/backtest", response_model=BacktestResponse)
def backtest(req: BacktestRequest):
    return run_backtest(req)


# ═══════════════════════════════════════════════════════════════════
# 端点：模型可解释性
# ═══════════════════════════════════════════════════════════════════


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    return run_explain(req)


# ═══════════════════════════════════════════════════════════════════
# 端点：交易建议
# ═══════════════════════════════════════════════════════════════════


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    return run_recommend_trade(req)


# ═══════════════════════════════════════════════════════════════════
# 静态文件 — 聊天 UI（必须在 API 路由之后注册）
# ═══════════════════════════════════════════════════════════════════

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
else:
    logger.warning("静态目录不存在，跳过挂载: %s", _STATIC_DIR)
