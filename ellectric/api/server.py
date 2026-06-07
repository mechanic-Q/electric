"""
Phase 4 — FastAPI REST API 服务
=================================

4 个 POST 路由包装 Phase 1-3 核心功能：
- /predict  → 负荷/电价预测
- /simulate → ASSUME 电力市场仿真
- /backtest → 历史回测
- /explain  → SHAP 模型可解释性

~~~~
架构层次
~~~~~~~~

  API 层 (server.py)  → 请求校验 (Pydantic) + 路由分发
  Service 层           → handlers.py 桥接 Pipeline 层
  Pipeline 层          → forecaster / backtester / shap_explainer / ASSUME

~~~~
启动命令
~~~~~~~~

  uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000

"""

import logging

from fastapi import FastAPI

from ellectric.service.schemas import (
    ForecastRequest,
    ForecastResponse,
    SimulateRequest,
    SimulateResponse,
    BacktestRequest,
    BacktestResponse,
    ExplainRequest,
    ExplainResponse,
)
from ellectric.service.handlers import (
    run_forecast,
    run_simulate,
    run_backtest,
    run_explain,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# FastAPI 应用初始化
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Ellectric API",
    description="AI+电力交易技术学习平台 — Phase 4 Integration & LLM Interface",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ═══════════════════════════════════════════════════════════════════
# 生命周期
# ═══════════════════════════════════════════════════════════════════


@app.on_event("startup")
def _log_startup():
    logger.info("Ellectric API v0.1.0 启动 — 端点: /predict, /simulate, /backtest, /explain")


# ═══════════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════════


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


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
