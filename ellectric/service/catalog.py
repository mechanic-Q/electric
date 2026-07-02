"""
Catalog Registry — 能力、数据集、离线报告统一目录（只读事实层）。

设计目标 (Design Goal)
~~~~~~~~~~~~~~~~~~~~~~
把项目已有事实（predict/simulate/backtest/explain/recommend 能力 +
山东/OWID 数据源 + ellectric/reports/**）暴露成一份稳定 registry，
供 WebUI 数据面板、Agent LLM tools 和 API 端点复用。

原则:
- 只读：不训练模型、不生成新报告、不写任何文件。
- 容错：缺失文件返回 status="missing" 或 available=False，不抛异常。
- 稳定：report id 使用 "<report_type>/<slug>" 形式，如
  "weather_tier4/validation"、"rl_full_dataset/evaluation"、
  "full_real_run/latest"。
- 安全：路径只返回项目内相对路径，不出现绝对路径或路径穿越。

暴露函数 (Public API)
~~~~~~~~~~~~~~~~~~~~~
- list_capabilities() -> list[CapabilityItem]
- list_datasets() -> list[DatasetInfo]
- list_reports(report_type: str | None = None) -> list[ReportSummary]
- get_report(report_id: str) -> ReportDetail
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ellectric.service.schemas import (
    CapabilityItem,
    DatasetInfo,
    ReportDetail,
    ReportSummary,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════════════════

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_REPORTS_ROOT = _PROJECT_ROOT / "ellectric" / "reports"


# ═══════════════════════════════════════════════════════════════════
# Capabilities
# ═══════════════════════════════════════════════════════════════════


_CAPABILITIES: list[dict[str, Any]] = [
    {
        "id": "forecast_load",
        "title": "负荷预测",
        "category": "forecast",
        "description": "XGBoost 山东 15min 负荷预测；模型缺失时 fallback 到 Weather Tier4 离线报告。",
        "example_questions": [
            "今天的负荷预测值是多少？",
            "山东未来 48 小时负荷曲线怎么样？",
        ],
        "endpoint": "/predict",
        "tool_name": "query_forecast",
        "supports_offline_fallback": True,
    },
    {
        "id": "forecast_price",
        "title": "电价预测（LEAR）",
        "category": "forecast",
        "description": "LEAR Lasso 山东日前电价预测；模型缺失时 fallback 到价格模型对比离线报告。",
        "example_questions": [
            "明天的日前电价预测怎么样？",
            "LEAR 相比持续法基线好多少？",
        ],
        "endpoint": "/predict",
        "tool_name": "query_forecast",
        "supports_offline_fallback": True,
    },
    {
        "id": "forecast_wind",
        "title": "风电出力预测",
        "category": "forecast",
        "description": "XGBoost 山东风电总加实际功率预测，复用 Tier1-4 特征工程。",
        "example_questions": [
            "山东未来 24 小时风电出力预测？",
            "风电预测的 MAE 是多少？",
        ],
        "endpoint": "/predict",
        "tool_name": "query_forecast",
        "supports_offline_fallback": True,
    },
    {
        "id": "forecast_solar",
        "title": "光伏出力预测",
        "category": "forecast",
        "description": "XGBoost 山东光伏总加实际功率预测。",
        "example_questions": [
            "山东今天光伏出力预测？",
            "光伏预测的 nRMSE 是多少？",
        ],
        "endpoint": "/predict",
        "tool_name": "query_forecast",
        "supports_offline_fallback": True,
    },
    {
        "id": "simulate_market",
        "title": "电力市场仿真",
        "category": "simulation",
        "description": "ASSUME 中国省间现货市场仿真（默认/夏季高峰/高风电占比场景）。",
        "example_questions": [
            "运行一次夏季高峰 7 天仿真",
            "高风电占比场景下出清价格如何？",
        ],
        "endpoint": "/simulate",
        "tool_name": "run_simulation",
    },
    {
        "id": "backtest_strategy",
        "title": "历史回测与策略对比",
        "category": "backtest",
        "description": "在山东历史价格数据上回放 baseline/oracle/PPO/SAC/TD3 策略并对比 P&L。",
        "example_questions": [
            "回测 2025-10-01 到 2026-01-14 的 PPO 表现",
            "PPO 相比 baseline_persistence 好多少？",
        ],
        "endpoint": "/backtest",
        "tool_name": "run_backtest",
    },
    {
        "id": "explain_shap",
        "title": "SHAP 模型可解释性",
        "category": "explain",
        "description": "XGBoost 负荷预测和 LEAR 电价预测的 SHAP 特征重要性与瀑布图。",
        "example_questions": [
            "解释一下 XGBoost 负荷模型的关键特征",
            "LEAR 电价模型 top 5 特征是什么？",
        ],
        "endpoint": "/explain",
    },
    {
        "id": "recommend_trade",
        "title": "结构化交易建议",
        "category": "trade",
        "description": "聚合预测/回测/SHAP 证据，输出学习平台交易建议（非真实交易）。",
        "example_questions": [
            "生成明天的交易建议",
            "balanced 风险偏好下有哪些动作？",
        ],
        "endpoint": "/recommend",
        "tool_name": "recommend_trade",
    },
    {
        "id": "reports_offline",
        "title": "离线报告浏览",
        "category": "report",
        "description": "浏览 Weather Tier4、可再生预测、价格模型对比、RL 全量评估、full_real_run 等离线报告。",
        "example_questions": [
            "有哪些离线报告可以看？",
            "Weather Tier4 对负荷预测提升多少？",
            "RL 策略评估结果如何？",
        ],
        "endpoint": "/reports",
        "tool_name": "query_reports",
    },
    {
        "id": "datasets_info",
        "title": "数据集元信息",
        "category": "dataset",
        "description": "山东 15min、OWID 中国年度、Chinese 小时级数据源的字段与时间范围。",
        "example_questions": [
            "山东数据包含哪些字段？",
            "OWID 中国数据覆盖哪些年份？",
        ],
        "endpoint": "/datasets",
        "tool_name": "query_datasets",
    },
]


def list_capabilities() -> list[CapabilityItem]:
    """返回全部能力目录项。"""
    items: list[CapabilityItem] = []
    for cap in _CAPABILITIES:
        items.append(CapabilityItem(**cap))
    return items


# ═══════════════════════════════════════════════════════════════════
# Datasets
# ═══════════════════════════════════════════════════════════════════


def _shandong_dataset() -> DatasetInfo:
    try:
        from ellectric.pipeline.shandong_loader import ShandongDataLoader

        loader = ShandongDataLoader()
        if not loader.data_path.exists():
            return DatasetInfo(
                id="shandong",
                title="山东 15min 电力数据",
                description="用户提供的山东电力 15 分钟数据（负荷/风光/电价）。",
                source="shandong",
                frequency="15min",
                available=False,
                note=f"数据文件不存在: {loader.data_path.relative_to(_PROJECT_ROOT)}",
            )
        meta = loader.get_metadata()
        df = loader.load_data()
        return DatasetInfo(
            id="shandong",
            title="山东 15min 电力数据",
            description="用户提供的山东电力 15 分钟数据（负荷/风光/电价）。745 天 × 96 点。",
            source=str(meta.get("source", "shandong")),
            frequency=str(meta.get("granularity") or meta.get("frequency") or "15min"),
            rows=int(meta.get("rows", len(df))),
            start=str(meta.get("start")),
            end=str(meta.get("end")),
            columns=[str(c) for c in df.columns],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("加载山东数据集元信息失败: %s", exc)
        return DatasetInfo(
            id="shandong",
            title="山东 15min 电力数据",
            description="用户提供的山东电力 15 分钟数据。",
            source="shandong",
            frequency="15min",
            available=False,
            note=f"读取失败: {type(exc).__name__}: {exc}",
        )


def _owid_dataset() -> DatasetInfo:
    return DatasetInfo(
        id="owid",
        title="OWID 中国电力年度数据",
        description="Our World in Data 中国电力年度数据，从 TWh 换算为日均 MW。",
        source="owid",
        frequency="yearly",
        note="按需在线拉取；不预取。",
    )


def _chinese_hourly_dataset() -> DatasetInfo:
    data_path = _PROJECT_ROOT / "ellectric" / "data" / "price_data.xlsx"
    return DatasetInfo(
        id="chinese_hourly",
        title="ZionLuo 中国小时级电价数据",
        description="ZionLuo/Electricity-Price-Forecasting price_data.xlsx（日前/实时价格 + 负荷 + 新能源出力）。",
        source="chinese",
        frequency="hourly",
        available=data_path.exists(),
        note=None if data_path.exists() else "数据文件缺失；需手动下载到 ellectric/data/price_data.xlsx。",
    )


def list_datasets() -> list[DatasetInfo]:
    """返回全部数据源元信息。加载失败降级为 available=False。"""
    return [_shandong_dataset(), _owid_dataset(), _chinese_hourly_dataset()]


# ═══════════════════════════════════════════════════════════════════
# Reports
# ═══════════════════════════════════════════════════════════════════


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(_PROJECT_ROOT))
    except ValueError:
        return str(path)


def _safe_read_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取 JSON 失败 %s: %s", path, exc)
        return None


def _round(value: Any, digits: int = 4) -> Any:
    try:
        f = float(value)
        return round(f, digits)
    except (TypeError, ValueError):
        return value


def _weather_tier4_summary() -> ReportSummary | None:
    json_path = _REPORTS_ROOT / "weather_tier4" / "weather_tier4_validation.json"
    md_path = _REPORTS_ROOT / "weather_tier4" / "weather_tier4_validation.md"
    if not json_path.exists():
        return ReportSummary(
            id="weather_tier4/validation",
            title="Weather Tier4 负荷预测验证",
            report_type="weather_tier4",
            status="missing",
            summary="报告文件不存在。",
        )
    data = _safe_read_json(json_path)
    if data is None:
        return ReportSummary(
            id="weather_tier4/validation",
            title="Weather Tier4 负荷预测验证",
            report_type="weather_tier4",
            status="error",
            summary="JSON 解析失败。",
            paths={"json": _rel(json_path)},
        )
    delta = data.get("experiments", {}).get("delta", {}) or {}
    baseline = data.get("experiments", {}).get("baseline_tier3", {}).get("metrics", {}) or {}
    weather = data.get("experiments", {}).get("weather_tier4", {}).get("metrics", {}) or {}
    raw_status = data.get("status", "unknown")
    metrics: dict[str, float | int | str] = {}
    if baseline.get("mae") is not None:
        metrics["mae_baseline_tier3"] = _round(baseline.get("mae"), 2)
    if weather.get("mae") is not None:
        metrics["mae_weather_tier4"] = _round(weather.get("mae"), 2)
    if delta.get("mae_delta_pct") is not None:
        metrics["mae_delta_pct"] = _round(delta.get("mae_delta_pct"), 2)
    metrics_meta: dict[str, dict[str, str]] = {}
    for k in metrics:
        if k == "mae_baseline_tier3":
            metrics_meta[k] = {"label": "Baseline Tier3 MAE", "unit": "MW"}
        elif k == "mae_weather_tier4":
            metrics_meta[k] = {"label": "Weather Tier4 MAE", "unit": "MW"}
        elif k == "mae_delta_pct":
            metrics_meta[k] = {"label": "MAE Delta", "unit": "%"}
    generated = data.get("metadata", {}).get("generated_at")
    interp = data.get("interpretation", {}).get("summary", "")
    paths = {"json": _rel(json_path)}
    if md_path.exists():
        paths["md"] = _rel(md_path)
    status = "ok" if raw_status == "ok" else ("degraded" if raw_status == "degraded" else "error")
    return ReportSummary(
        id="weather_tier4/validation",
        title="Weather Tier4 负荷预测验证",
        report_type="weather_tier4",
        status=status,
        generated_at=generated,
        summary=interp or "Weather Tier4 消融实验结果。",
        metrics=metrics,
        metrics_meta=metrics_meta,
        paths=paths,
    )


def _renewable_summary() -> ReportSummary | None:
    json_path = _REPORTS_ROOT / "renewable_forecaster" / "renewable_forecast_validation.json"
    md_path = _REPORTS_ROOT / "renewable_forecaster" / "renewable_forecast_validation.md"
    if not json_path.exists():
        return ReportSummary(
            id="renewable_forecaster/validation",
            title="风光出力预测验证",
            report_type="renewable",
            status="missing",
            summary="报告文件不存在。",
        )
    data = _safe_read_json(json_path)
    if data is None:
        return ReportSummary(
            id="renewable_forecaster/validation",
            title="风光出力预测验证",
            report_type="renewable",
            status="error",
            summary="JSON 解析失败。",
            paths={"json": _rel(json_path)},
        )
    wind = data.get("experiments", {}).get("wind", {}).get("metrics", {}) or {}
    solar = data.get("experiments", {}).get("solar", {}).get("metrics", {}) or {}
    metrics: dict[str, float | int | str] = {}
    for k, v in {"wind_mae": wind.get("mae"), "wind_nrmse": wind.get("nrmse"),
                 "solar_mae": solar.get("mae"), "solar_nrmse": solar.get("nrmse")}.items():
        if v is not None:
            metrics[k] = _round(v, 4)
    paths = {"json": _rel(json_path)}
    if md_path.exists():
        paths["md"] = _rel(md_path)
    return ReportSummary(
        id="renewable_forecaster/validation",
        title="风光出力预测验证",
        report_type="renewable",
        status="ok" if data.get("status") == "ok" else "error",
        generated_at=data.get("metadata", {}).get("generated_at"),
        summary="XGBoost 风电/光伏预测在山东全量数据上的验证结果。",
        metrics=metrics,
        paths=paths,
    )


def _rl_evaluation_summary() -> ReportSummary | None:
    json_path = _REPORTS_ROOT / "rl_full_dataset" / "evaluation_report.json"
    md_path = _REPORTS_ROOT / "rl_full_dataset" / "evaluation_report.md"
    html_path = _REPORTS_ROOT / "rl_full_dataset" / "cumulative_pnl.html"
    if not json_path.exists():
        return ReportSummary(
            id="rl_full_dataset/evaluation",
            title="RL 全量评估",
            report_type="rl_evaluation",
            status="missing",
            summary="报告文件不存在。",
        )
    data = _safe_read_json(json_path)
    if data is None:
        return ReportSummary(
            id="rl_full_dataset/evaluation",
            title="RL 全量评估",
            report_type="rl_evaluation",
            status="error",
            summary="JSON 解析失败。",
            paths={"json": _rel(json_path)},
        )
    metrics_list = data.get("metrics", []) or []
    metrics: dict[str, float | int | str] = {}
    for row in metrics_list:
        strategy = row.get("strategy")
        pnl = row.get("total_pnl")
        if strategy and pnl is not None:
            metrics[f"pnl_{strategy}"] = _round(pnl, 2)
    paths = {"json": _rel(json_path)}
    if md_path.exists():
        paths["md"] = _rel(md_path)
    if html_path.exists():
        paths["html"] = _rel(html_path)
    return ReportSummary(
        id="rl_full_dataset/evaluation",
        title="RL 全量评估（PPO/SAC/TD3 vs baseline/oracle）",
        report_type="rl_evaluation",
        status="ok",
        generated_at=data.get("metadata", {}).get("generated_at"),
        summary="山东全量数据上的 RL 策略评估与基线对比。",
        metrics=metrics,
        paths=paths,
    )


def _price_comparison_summaries() -> list[ReportSummary]:
    """扫描 full_real_run 下的 price_comparison。"""
    items: list[ReportSummary] = []
    root = _REPORTS_ROOT / "full_real_run"
    if not root.exists():
        return items
    for run_dir in sorted(root.iterdir()):
        if not run_dir.is_dir():
            continue
        cmp_json = run_dir / "price_comparison" / "comparison.json"
        if not cmp_json.exists():
            continue
        data = _safe_read_json(cmp_json)
        if data is None:
            items.append(ReportSummary(
                id=f"price_comparison/{run_dir.name}",
                title=f"电价模型对比 ({run_dir.name})",
                report_type="price_comparison",
                status="error",
                summary="JSON 解析失败。",
                paths={"json": _rel(cmp_json)},
            ))
            continue
        models = data.get("models", {}) or {}
        metrics: dict[str, float | int | str] = {}
        for name, entry in models.items():
            m = (entry or {}).get("metrics", {}) or {}
            if m.get("mae") is not None:
                metrics[f"{name}_mae"] = _round(m.get("mae"), 2)
        md_path = run_dir / "price_comparison" / "comparison.md"
        html_path = run_dir / "price_comparison" / "residuals.html"
        paths = {"json": _rel(cmp_json)}
        if md_path.exists():
            paths["md"] = _rel(md_path)
        if html_path.exists():
            paths["html"] = _rel(html_path)
        items.append(ReportSummary(
            id=f"price_comparison/{run_dir.name}",
            title=f"电价模型对比 ({run_dir.name})",
            report_type="price_comparison",
            status="ok",
            generated_at=str(data.get("metadata", {}).get("args", {}).get("start", "")) or None,
            summary="LEAR/DNN/persistence/weekly_avg 四模型 MAE/RMSE/MAPE 对比。",
            metrics=metrics,
            paths=paths,
        ))
    return items


def _full_real_run_summaries() -> list[ReportSummary]:
    """扫描 full_real_run/**/SUMMARY.json。"""
    items: list[ReportSummary] = []
    root = _REPORTS_ROOT / "full_real_run"
    if not root.exists():
        return items
    for run_dir in sorted(root.iterdir()):
        if not run_dir.is_dir():
            continue
        summary_json = run_dir / "SUMMARY.json"
        if not summary_json.exists():
            continue
        data = _safe_read_json(summary_json)
        if data is None:
            items.append(ReportSummary(
                id=f"full_real_run/{run_dir.name}",
                title=f"全量运行汇总 ({run_dir.name})",
                report_type="full_real_run",
                status="error",
                summary="JSON 解析失败。",
                paths={"json": _rel(summary_json)},
            ))
            continue
        tasks = data.get("tasks", {}) or {}
        metrics: dict[str, float | int | str] = {}
        for task_name, entry in tasks.items():
            status = (entry or {}).get("status", "unknown")
            metrics[f"{task_name}_status"] = str(status)
        summary_md = run_dir / "SUMMARY.md"
        paths = {"json": _rel(summary_json)}
        if summary_md.exists():
            paths["md"] = _rel(summary_md)
        items.append(ReportSummary(
            id=f"full_real_run/{run_dir.name}",
            title=f"全量运行汇总 ({run_dir.name})",
            report_type="full_real_run",
            status="ok",
            generated_at=str(data.get("generated_at", "")) or None,
            summary="Weather Tier4 + 风光预测 + 电价模型对比 + RL 训练 + pytest 全量汇总。",
            metrics=metrics,
            paths=paths,
        ))
    return items


def _recommend_sample_summary() -> ReportSummary | None:
    md_path = _REPORTS_ROOT / "recommend" / "sample_output.md"
    if not md_path.exists():
        return None
    return ReportSummary(
        id="recommend/sample_output",
        title="交易建议样例",
        report_type="recommend",
        status="ok",
        summary="学习平台生成的结构化交易建议样例。",
        paths={"md": _rel(md_path)},
    )


def list_reports(report_type: str | None = None) -> list[ReportSummary]:
    """返回全部（或按类型过滤的）离线报告摘要。缺失/解析失败会用 status 标记，不抛异常。"""
    items: list[ReportSummary] = []
    for candidate in (
        _weather_tier4_summary(),
        _renewable_summary(),
        _rl_evaluation_summary(),
        _recommend_sample_summary(),
    ):
        if candidate is not None:
            items.append(candidate)
    items.extend(_price_comparison_summaries())
    items.extend(_full_real_run_summaries())
    if report_type:
        items = [x for x in items if x.report_type == report_type]
    return items


def _find_report(report_id: str) -> ReportSummary | None:
    for item in list_reports():
        if item.id == report_id:
            return item
    return None


def _read_body(paths: dict[str, str]) -> dict | str | None:
    """尝试按 json > md > csv > html 顺序读取报告主体。"""
    order = ["json", "md", "csv", "html"]
    for key in order:
        rel = paths.get(key)
        if not rel:
            continue
        abs_path = _PROJECT_ROOT / rel
        if not abs_path.exists():
            continue
        try:
            if key == "json":
                with abs_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                with abs_path.open("r", encoding="utf-8") as f:
                    return f.read()
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取报告主体失败 %s: %s", abs_path, exc)
            continue
    return None


def get_report(report_id: str) -> ReportDetail:
    """按稳定 ID 返回报告详情；未知 ID 返回 status='missing'。"""
    if not report_id or ".." in report_id:
        return ReportDetail(
            id=report_id or "",
            title="",
            report_type="unknown",
            status="error",
            summary="非法 report_id。",
        )
    summary = _find_report(report_id)
    if summary is None:
        return ReportDetail(
            id=report_id,
            title="",
            report_type="unknown",
            status="missing",
            summary=f"未找到报告: {report_id}",
        )
    body = _read_body(summary.paths)
    return ReportDetail(
        id=summary.id,
        title=summary.title,
        report_type=summary.report_type,
        status=summary.status,
        generated_at=summary.generated_at,
        summary=summary.summary,
        metrics=summary.metrics,
        metrics_meta=summary.metrics_meta,
        paths=summary.paths,
        content=body,
    )


# ═══════════════════════════════════════════════════════════════════
# 调试入口
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":  # pragma: no cover - manual smoke
    print(f"generated_at: {datetime.utcnow().isoformat()}Z")
    print(f"capabilities: {len(list_capabilities())}")
    print(f"datasets:     {len(list_datasets())}")
    print(f"reports:      {len(list_reports())}")
