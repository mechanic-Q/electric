"""
Phase 4 — Pydantic v2 请求/响应 Schemas
=========================================

定义 4 组 API 数据契约，被 handler / FastAPI / CLI / LLM tools 共用。

~~~~
Schema 分组
~~~~~~~~~~~~

  Forecast:  ForecastRequest → ForecastMetrics → ForecastResponse
  Simulate:  SimulateRequest → SimulateResponse
  Backtest:  BacktestRequest → BacktestResponse
  Explain:   ExplainRequest  → FeatureImportance → ExplainResponse

~~~~
设计决策
~~~~~~~~

为什么用 Pydantic v2 (pydantic-core / pydantic 2.13.4)？
  - pydantic-core 使用 Rust 后端，序列化/校验速度比 v1 快 5-50 倍
  - FastAPI 原生集成 Pydantic v2，自动生成 OpenAPI 文档
  - model_validator mode="after" 提供比 v1 @validator 更清晰的跨字段校验
  - Python 3.10+ 原生类型标注 (list[float], dict[str, float]) 可直接使用
    无需 typing.List / typing.Dict 等兼容写法

注意：本项目不使用 pydantic v1 兼容 API (@validator, class Config)。
"""

import logging
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 预测 (Forecast)
# ═══════════════════════════════════════════════════════════════════


class ForecastRequest(BaseModel):
    """
    负荷或电价预测请求。

    通过 model_type 区分调用 XGBoost 负荷预测器还是 LEAR 电价预测器。
    horizon 支持 1-168 小时（1 周），默认 24 对应日前预测。
    """

    model_type: Literal["load", "price"] = Field(
        description="模型类型: load=XGBoost 负荷预测, price=LEAR 电价预测",
    )
    horizon: int = Field(
        default=24,
        ge=1,
        le=168,
        description="预测时长，单位：小时 (1-168)",
    )
    data_source: str = Field(
        default="owid",
        description="数据源标识 (owid / chinese_hourly)",
    )


class ForecastMetrics(BaseModel):
    """预测误差指标。回溯场景下填充，纯推理场景下为 None。"""

    mae: float | None = Field(default=None, description="Mean Absolute Error")
    rmse: float | None = Field(default=None, description="Root Mean Squared Error")
    mape: float | None = Field(default=None, description="Mean Absolute Percentage Error (%)")


class ForecastResponse(BaseModel):
    """预测响应：时间戳序列 + 预测值序列 + 可选误差指标。"""

    model_config = {"exclude_none": True}

    timestamps: list[datetime] = Field(description="预测时间戳序列 (UTC)")
    predictions: list[float] = Field(description="预测值序列 (MW 或 元/MWh)")
    metrics: ForecastMetrics = Field(description="预测误差指标 (回溯场景)")

    @model_validator(mode="after")
    def _check_length_match(self) -> "ForecastResponse":
        if len(self.timestamps) != len(self.predictions):
            raise ValueError("timestamps and predictions must have same length")
        return self


# ═══════════════════════════════════════════════════════════════════
# 仿真 (Simulate)
# ═══════════════════════════════════════════════════════════════════


class SimulateRequest(BaseModel):
    """
    电力市场仿真请求。

    通过 config 选择预设场景（基准 / 夏季高峰 / 高风电占比），
    days 控制仿真天数 (1-30)。
    """

    config: Literal["default", "summer_peak", "wind_high"] = Field(
        description="预设场景: default=基准, summer_peak=夏季高峰, wind_high=高风电占比",
    )
    days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="仿真天数 (1-30)",
    )


class SimulateResponse(BaseModel):
    """
    仿真响应：出清电价、调度结果、代理利润。

    所有序列字段使用 default_factory=list 确保 JSON 始终输出 [] 而非 null。
    """

    model_config = {"exclude_none": True}

    status: str = Field(description="执行状态: success | error")
    clearing_prices: list[float] = Field(
        default_factory=list,
        description="出清电价序列 (元/MWh)",
    )
    dispatch: list[dict] = Field(
        default_factory=list,
        description="各单元调度结果 [{unit, power_mw, cost}, ...]",
    )
    agent_profits: dict[str, float] = Field(
        default_factory=dict,
        description="各代理利润 (元)",
    )
    output_dir: str = Field(default="", description="仿真输出目录路径")
    error_message: str | None = Field(
        default=None,
        description="错误信息 (status=error 时)",
    )


# ═══════════════════════════════════════════════════════════════════
# 回测 (Backtest)
# ═══════════════════════════════════════════════════════════════════


class BacktestRequest(BaseModel):
    """
    历史回测请求。

    指定起止日期和交易策略。RL 策略 (ppo/sac/td3) 必须提供 model_path。
    """

    start_date: date = Field(description="回测开始日期")
    end_date: date = Field(description="回测结束日期")
    strategy: Literal[
        "baseline_persistence",
        "baseline_mean",
        "oracle",
        "ppo",
        "sac",
        "td3",
    ] = Field(description="交易策略")
    model_path: str | None = Field(
        default=None,
        description="RL 模型权重路径 (strategy=ppo|sac|td3 时必填)",
    )
    data_source: str = Field(
        default="owid",
        description="数据源标识",
    )

    @model_validator(mode="after")
    def _validate_dates_and_model(self) -> "BacktestRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        rl_strategies = {"ppo", "sac", "td3"}
        if self.strategy in rl_strategies and self.model_path is None:
            raise ValueError("model_path is required for RL strategies")
        return self


class BacktestResponse(BaseModel):
    """
    回测响应：累计盈亏、夏普比率、多策略对比。

    cumulative_pnl / comparison 使用 default_factory 保证缺省时输出 [] 和 {}。
    sharpe_ratio / plot_data / error_message 为可选字段，序列化时不输出 None 值。
    """

    model_config = {"exclude_none": True}

    status: str = Field(description="执行状态: success | error")
    cumulative_pnl: list[float] = Field(
        default_factory=list,
        description="累计盈亏序列 (元)",
    )
    sharpe_ratio: float | None = Field(
        default=None,
        description="夏普比率",
    )
    comparison: dict[str, float] = Field(
        default_factory=dict,
        description="多策略指标对比 {strategy_name: final_pnl}",
    )
    plot_data: dict | None = Field(
        default=None,
        description="Plotly JSON (可选, 前端渲染)",
    )
    error_message: str | None = Field(default=None)


# ═══════════════════════════════════════════════════════════════════
# 可解释性 (Explain)
# ═══════════════════════════════════════════════════════════════════


class ExplainRequest(BaseModel):
    """
    模型可解释性请求。

    指定模型类型（xgboost / lear）和测试集样本索引，
    max_display 控制瀑布图显示的特征数量上限。
    """

    model_type: Literal["xgboost", "lear"] = Field(
        description="模型类型: xgboost=负荷预测, lear=电价预测",
    )
    sample_index: int = Field(
        default=0,
        ge=0,
        description="要解释的样本在测试集中的索引",
    )
    max_display: int = Field(
        default=10,
        ge=1,
        le=50,
        description="最多显示的特征数 (1-50)",
    )


class FeatureImportance(BaseModel):
    """单特征重要性的数值描述。"""

    name: str = Field(description="特征名称")
    importance: float = Field(description="重要性数值 (SHAP 或 gain)")
    rank: int = Field(description="排名 (1-based)")


class ExplainResponse(BaseModel):
    """
    可解释性响应：特征重要性列表 + 可选 SHAP 瀑布图 JSON。

    feature_importance 按 rank 升序排列。
    """

    model_config = {"exclude_none": True}

    status: str = Field(description="执行状态: success | error")
    feature_importance: list[FeatureImportance] = Field(
        default_factory=list,
        description="特征重要性列表，按 rank 升序",
    )
    waterfall_json: dict | None = Field(
        default=None,
        description="SHAP waterfall Plotly JSON (可选)",
    )
    error_message: str | None = Field(default=None)
