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
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

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

    model_type: Literal["load", "price", "wind", "solar", "price_dnn"] = Field(
        description="模型类型: load=XGBoost 负荷预测, price=LEAR 电价预测, price_dnn=PyTorch DNN 电价预测",
    )
    horizon: int = Field(
        default=24,
        ge=1,
        le=168,
        description="预测时长，单位：小时 (1-168)",
    )
    data_source: str = Field(
        default="shandong",
        description="数据源标识 (shandong / owid / chinese_hourly)",
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
        default="shandong",
        description="数据源标识 (shandong / owid)",
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
    data_source: str = Field(
        default="shandong",
        description="数据源标识 (shandong / owid)",
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


# ═══════════════════════════════════════════════════════════════════
# 交易建议 (Recommend)
# ═══════════════════════════════════════════════════════════════════


class TradeAction(BaseModel):
    """结构化交易动作。由 service 层生成，LLM 只做解释不修改数值。"""

    timestamp: str = Field(description="ISO 格式时间戳")
    action: Literal["buy", "sell", "hold"] = Field(description="交易动作")
    price_limit: float | None = Field(default=None, description="限价 (元/MWh)")
    quantity_mwh: float | None = Field(default=None, description="建议电量 (MWh)")
    reason: str = Field(description="中文原因说明")
    confidence: Literal["high", "medium", "low"] = Field(description="单条建议置信度")


class RecommendRequest(BaseModel):
    """交易建议请求。指定日期和市场参数，service 层聚合预测/回测/解释证据。"""

    date: str = Field(description="交易日期 YYYY-MM-DD")
    horizon_hours: int = Field(default=24, ge=1, le=72, description="预测时长（小时）")
    market: str = Field(default="shandong", description="数据源标识")
    risk_preference: str = Field(
        default="balanced",
        description="风险偏好: conservative/balanced/aggressive",
    )
    max_actions: int = Field(
        default=5,
        ge=1,
        le=10,
        description="最多返回的动作数",
    )


class RecommendResponse(BaseModel):
    """交易建议响应：含结构化动作列表、总体置信度、证据摘要和免责声明。"""

    model_config = {"exclude_none": True}

    summary: str = Field(description="中文交易建议总结")
    actions: list[TradeAction] = Field(default_factory=list, description="交易动作列表")
    confidence: Literal["high", "medium", "low"] = Field(description="总体置信度")
    evidence: dict = Field(default_factory=dict, description="证据摘要")
    disclaimer: str = Field(description="学习用途免责声明")


# ═══════════════════════════════════════════════════════════════════
# Catalog (Capabilities / Datasets / Reports)
# ═══════════════════════════════════════════════════════════════════


CapabilityCategory = Literal[
    "forecast",
    "simulation",
    "backtest",
    "explain",
    "trade",
    "report",
    "dataset",
]


class CapabilityItem(BaseModel):
    """能力目录项：一个可问/可运行能力的元信息，供 WebUI 与 Agent 引导。"""

    id: str = Field(description="稳定能力 ID，如 forecast_load、report_price_comparison")
    title: str = Field(description="中文标题")
    category: CapabilityCategory = Field(description="能力分类")
    description: str = Field(description="能力说明")
    example_questions: list[str] = Field(
        default_factory=list, description="示例问题（AI 引导用）"
    )
    endpoint: str | None = Field(default=None, description="对应 REST 端点，若适用")
    tool_name: str | None = Field(default=None, description="对应 LLM tool 名称，若适用")
    supports_offline_fallback: bool = Field(
        default=False, description="是否支持模型缺失时的离线报告 fallback"
    )
    available: bool = Field(default=True, description="能力当前是否可用")


class DatasetInfo(BaseModel):
    """数据集元信息：数据源标识、时间范围、字段等，用于面板展示与 Agent 查询。"""

    id: str = Field(description="数据源 ID，如 shandong / owid / chinese_hourly")
    title: str = Field(description="中文标题")
    description: str = Field(description="来源与用途说明")
    source: str = Field(description="来源标签，如 shandong / owid / chinese")
    frequency: str | None = Field(default=None, description="时间频率，如 15min / hourly / daily")
    rows: int | None = Field(default=None, description="行数（若可获取）")
    start: str | None = Field(default=None, description="起始时间 ISO 字符串")
    end: str | None = Field(default=None, description="结束时间 ISO 字符串")
    columns: list[str] = Field(default_factory=list, description="字段列表")
    available: bool = Field(default=True, description="数据是否可加载")
    note: str | None = Field(default=None, description="补充说明或错误摘要")


ReportStatus = Literal["ok", "missing", "error", "degraded"]


class ReportSummary(BaseModel):
    """离线报告摘要：ID、标题、类型、状态、关键指标、资产路径。"""

    id: str = Field(description="稳定报告 ID，如 weather_tier4/validation")
    title: str = Field(description="中文标题")
    report_type: str = Field(description="报告类型：weather_tier4/renewable/price_comparison/rl_evaluation/full_real_run/recommend")
    status: ReportStatus = Field(description="报告状态")
    generated_at: str | None = Field(default=None, description="生成时间 ISO 字符串")
    summary: str = Field(default="", description="中文摘要")
    metrics: dict[str, float | int | str] = Field(
        default_factory=dict, description="标量关键指标"
    )
    metrics_meta: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="指标元信息 {metric_key: {label, unit, description}}",
    )
    paths: dict[str, str] = Field(
        default_factory=dict, description="项目内相对路径 {json,md,html,csv}"
    )


class ReportDetail(ReportSummary):
    """离线报告详情：在摘要之上附带 content（可能是 JSON dict 或纯文本）。"""

    content: dict | str | None = Field(
        default=None, description="报告主体内容；JSON 报告为 dict，其他为文本"
    )


# ═══════════════════════════════════════════════════════════════════
# 滚动展示 DTO (Rolling Dashboard)
# ═══════════════════════════════════════════════════════════════════


class RollingDemoMeta(BaseModel):
    """滚动展示数据元信息。"""

    source: str = Field(description="数据源标识")
    start: str = Field(description="窗口起始时间 (ISO)")
    end: str = Field(description="窗口结束时间 (ISO)")
    frequency: str = Field(description="时间粒度")
    points_per_day: int = Field(description="每日点数")
    rows: int = Field(description="总行数")


class RollingDemoSeries(BaseModel):
    """滚动展示时序数据，按时间戳对齐。"""

    timestamps: list[str] = Field(default_factory=list, description="ISO 格式时间戳")
    load_actual: list[float | None] = Field(default_factory=list, description="实际负荷 (MW)")
    load_forecast: list[float | None] = Field(default_factory=list, description="预测负荷 (MW)")
    price_rt: list[float | None] = Field(default_factory=list, description="实时电价 (元/MWh)")
    price_da: list[float | None] = Field(default_factory=list, description="日前电价 (元/MWh)")
    wind_actual: list[float | None] = Field(default_factory=list, description="风电出力 (MW)")
    solar_actual: list[float | None] = Field(default_factory=list, description="光伏出力 (MW)")
    tie_line: list[float | None] = Field(default_factory=list, description="省间联络线 (MW)")
    pumped_storage: list[float | None] = Field(default_factory=list, description="抽水蓄能 (MW)")


class RollingDemoPanel(BaseModel):
    """滚动展示面板元信息。"""

    id: str = Field(description="面板 ID")
    title: str = Field(description="面板标题")
    chart_type: str = Field(description="图表类型: line/heatmap/area/evidence")
    summary: str = Field(default="", description="文字摘要")
    metrics: dict[str, float | int | str] = Field(default_factory=dict, description="关键指标")
    warning_ids: list[str] = Field(default_factory=list, description="关联警告 ID")


class InstanceStatus(BaseModel):
    """Per-instance evidence validation status."""

    status: Literal["ok", "degraded"] = "degraded"
    degradation_reason: str | None = None


class RollingDemoStrategy(BaseModel):
    """Versioned strategy evidence for the fixed 30-day historical replay."""

    status: Literal["ok", "degraded"] = Field(default="degraded")
    degradation_reason: str | None = Field(default=None)
    instance_status: dict[str, InstanceStatus] = Field(default_factory=dict)
    snapshot_version: int | None = Field(default=None)
    window: dict[str, Any] = Field(default_factory=dict)
    methodology: dict[str, Any] = Field(default_factory=dict)
    summary: list[dict[str, Any]] = Field(default_factory=list)
    timeseries: dict[str, Any] = Field(default_factory=dict)
    daily: dict[str, Any] = Field(default_factory=dict)
    oracle: dict[str, Any] = Field(default_factory=dict)
    long_term_evidence: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class RollingDemoReportEvidence(BaseModel):
    """滚动展示报告证据条目。"""

    id: str = Field(description="报告 ID")
    title: str = Field(description="报告标题")
    status: str = Field(description="状态: ok/missing/error/degraded")
    summary: str = Field(default="", description="摘要")
    metrics: dict[str, float | int | str] = Field(default_factory=dict, description="关键指标")


class RollingDemoRequest(BaseModel):
    """滚动展示请求参数。"""

    start: str = Field(default="2025-10-01", description="窗口起始日期 (YYYY-MM-DD)")
    days: int = Field(default=30, ge=1, le=30, description="展示天数 (1-30)")


class RollingDemoResponse(BaseModel):
    """滚动展示响应 payload。"""

    meta: RollingDemoMeta = Field(description="数据元信息")
    series: RollingDemoSeries = Field(default_factory=RollingDemoSeries, description="时序数据")
    panels: list[RollingDemoPanel] = Field(default_factory=list, description="面板列表")
    strategy: RollingDemoStrategy = Field(default_factory=RollingDemoStrategy, description="策略信息")
    reports: list[RollingDemoReportEvidence] = Field(default_factory=list, description="报告证据列表")
    warnings: list[str] = Field(default_factory=list, description="降级/缺失警告")
