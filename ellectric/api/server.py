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
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ellectric.service.schemas import (
    CapabilityItem,
    DatasetInfo,
    ForecastRequest,
    ForecastResponse,
    ReportDetail,
    ReportSummary,
    RollingDemoResponse,
    SimulateRequest,
    SimulateResponse,
    BacktestRequest,
    BacktestResponse,
    ExplainRequest,
    ExplainResponse,
    RecommendRequest,
    RecommendResponse,
)
from ellectric.service.dashboard import build_rolling_demo
from ellectric.service.handlers import (
    get_report,
    list_capabilities,
    list_datasets,
    list_reports,
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


class _ReplayContextModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ReplayMarketContext(_ReplayContextModel):
    realtime_settlement_price: float
    realtime_price_measure: Literal["exact", "mean"]
    realtime_price_min: float
    realtime_price_max: float
    daily_backtest_baseline_price: float
    spread: float
    day_ahead_hourly_price: float | None = None
    load_actual_mw: float
    historical_published_load_forecast_mw: float
    load_measure: Literal["exact", "mean", "peak"]
    wind_mw: float
    solar_mw: float
    renewable_measure: Literal["exact", "mean"]


class ReplayStrategyContext(_ReplayContextModel):
    simulated_spread_value: float
    contribution: Literal["positive", "negative", "none"]
    reconstructed_position_pct: float | None = Field(default=None, ge=-100.1, le=100.1)
    position_state: Literal["long", "short", "approximately_flat", "indeterminate"] | None = None
    long_periods: int = Field(ge=0, le=96)
    short_periods: int = Field(ge=0, le=96)
    approximately_flat_periods: int = Field(ge=0, le=96)
    indeterminate_periods: int = Field(ge=0, le=96)
    mean_absolute_position_pct: float | None = Field(default=None, ge=0, le=100.1)


class ReplayStrategiesContext(_ReplayContextModel):
    td3: ReplayStrategyContext
    ppo: ReplayStrategyContext
    sac: ReplayStrategyContext
    trend: ReplayStrategyContext


class ReplaySnapshotContext(_ReplayContextModel):
    generated_at: str = Field(max_length=40)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReplayContext(_ReplayContextModel):
    scene: Literal["shandong-2025-10-30d"]
    window_start: Literal["2025-10-01T00:00:00+08:00"]
    window_end: Literal["2025-10-30T23:45:00+08:00"]
    timezone: Literal["Asia/Shanghai (UTC+8)"]
    granularity: Literal["daily", "hourly", "15-minute"]
    period_start: str = Field(pattern=r"^2025-10-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:00\+08:00$")
    period_end: str = Field(pattern=r"^2025-10-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:00\+08:00$")
    period_points: int = Field(ge=1, le=96)
    baseline_initialization: bool
    market: ReplayMarketContext
    strategies: ReplayStrategiesContext
    snapshot: ReplaySnapshotContext

    @model_validator(mode="after")
    def validate_selection(self):
        start = datetime.fromisoformat(self.period_start)
        end = datetime.fromisoformat(self.period_end)
        scene_start = datetime(2025, 10, 1, tzinfo=timezone(timedelta(hours=8)))
        scene_end = datetime(2025, 10, 30, 23, 45, tzinfo=timezone(timedelta(hours=8)))
        expected_points = {"daily": 96, "hourly": 4, "15-minute": 1}[self.granularity]
        if start.utcoffset() != timedelta(hours=8) or end.utcoffset() != timedelta(hours=8):
            raise ValueError("period timestamps must use UTC+8")
        if not scene_start <= start <= end <= scene_end:
            raise ValueError("period must stay within the 30-day replay window")
        if self.period_points != expected_points:
            raise ValueError("period_points does not match granularity")
        if end != start + timedelta(minutes=15 * (self.period_points - 1)):
            raise ValueError("period timestamps do not match period_points")
        for name in ("td3", "ppo", "sac", "trend"):
            strategy = getattr(self.strategies, name)
            counted = (
                strategy.long_periods
                + strategy.short_periods
                + strategy.approximately_flat_periods
                + strategy.indeterminate_periods
            )
            if counted != self.period_points:
                raise ValueError(f"{name} period counts do not match period_points")
        return self


class ChatRequest(BaseModel):
    """SSE 流式对话请求。"""
    query: str = Field(description="用户当前输入")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="历史消息列表。客户端维护会话上下文。",
    )
    replay_context: ReplayContext | None = Field(
        default=None,
        description="当前屏幕的紧凑30天历史回放事实，不写入聊天历史。",
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
        stream_chat(
            req.query,
            [m.model_dump() for m in req.history],
            replay_context=req.replay_context.model_dump(mode="json") if req.replay_context else None,
        ),
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
# 端点：能力目录（Capabilities / Datasets / Reports）
# 必须在 app.mount("/") 之前注册，避免被 StaticFiles 捕获。
# ═══════════════════════════════════════════════════════════════════


@app.get("/capabilities", response_model=list[CapabilityItem])
def capabilities():
    """返回能力目录：预测、仿真、回测、解释、交易建议、报告、数据集。"""
    return list_capabilities()


@app.get("/datasets", response_model=list[DatasetInfo])
def datasets():
    """返回数据源元信息：山东、OWID、Chinese Hourly。"""
    return list_datasets()


@app.get("/reports", response_model=list[ReportSummary])
def reports(report_type: str | None = None):
    """返回离线报告清单，可选按 report_type 过滤。"""
    return list_reports(report_type=report_type)


@app.get("/reports/{report_id:path}", response_model=ReportDetail)
def report_detail(report_id: str):
    """按稳定 ID 读取报告详情；未知 ID 返回 status='missing'。"""
    return get_report(report_id)


# ═══════════════════════════════════════════════════════════════════
# 端点：滚动仿真看板
# ═══════════════════════════════════════════════════════════════════


@app.get("/dashboard/rolling-demo", response_model=RollingDemoResponse)
def rolling_demo(start: str = "2025-10-01", days: int = 30):
    """GET /dashboard/rolling-demo — 构建滚动仿真看板数据。

    Query params:
        start (str, default="2025-10-01"): 起始日期 YYYY-MM-DD。
        days  (int, default=30): 滚动窗口天数。
    """
    return build_rolling_demo(start=start, days=days)


# ═══════════════════════════════════════════════════════════════════
# 静态文件 — 聊天 UI（必须在 API 路由之后注册）
# ═══════════════════════════════════════════════════════════════════

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
else:
    logger.warning("静态目录不存在，跳过挂载: %s", _STATIC_DIR)
