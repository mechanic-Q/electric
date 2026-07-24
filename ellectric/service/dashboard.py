"""
Wave 1, task-02 — Rolling demo builder (read-only service).
Builds Shandong 15min rolling demo payload with degradation warnings.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from ellectric.config import TimeConfig
from ellectric.service.schemas import (
    RollingDemoMeta,
    RollingDemoPanel,
    RollingDemoReportEvidence,
    RollingDemoResponse,
    RollingDemoSeries,
    RollingDemoStrategy,
)
from ellectric.service.strategy_evidence import (
    REPLAY_END,
    REPLAY_POINTS,
    REPLAY_START,
    TEST_POINTS,
    build_strategy_evidence,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_REPORTS_ROOT = _PROJECT_ROOT / "ellectric" / "reports"


# ── Column mapping helpers ──

_COLUMN_SERIES_MAP: dict[str, tuple[str, str]] = {
    "load_actual": ("load_mw", "实际负荷"),
    "load_forecast": ("load_forecast_mw", "负荷预测"),
    "price_rt": ("rt_price", "实时价格"),
    "price_da": ("da_price", "日前价格"),
    "wind_actual": ("wind_actual_mw", "风电实际出力"),
    "solar_actual": ("solar_actual_mw", "光伏实际出力"),
    "tie_line": ("tie_line_actual_mw", "联络线受电"),
    "pumped_storage": ("pumped_storage_mw", "抽蓄"),
}


def _load_window(start: str | None, days: int) -> pd.DataFrame:
    from ellectric.pipeline.shandong_loader import ShandongDataLoader

    loader = ShandongDataLoader(include_forecasts=True)
    start_dt = pd.Timestamp(start or "2025-10-01")
    if start_dt.tzinfo is None:
        start_dt = start_dt.tz_localize("Asia/Shanghai")
    else:
        start_dt = start_dt.tz_convert("Asia/Shanghai")
    end_exclusive = start_dt + pd.Timedelta(days=days)
    # Loader uses inclusive ≤ filter — pass end_exclusive date, then re-filter
    df = loader.load_data(str(start_dt.date()), str(end_exclusive.date()))
    timestamps = pd.to_datetime(df["timestamp"])
    # Source clocks are Shandong local time; the loader currently tags them UTC.
    # Correct only the showcase boundary so historical training artifacts stay unchanged.
    if timestamps.dt.tz is not None:
        timestamps = timestamps.dt.tz_localize(None)
    df["timestamp"] = timestamps.dt.tz_localize("Asia/Shanghai")
    df = df[
        (df["timestamp"] >= start_dt) & (df["timestamp"] < end_exclusive)
    ].sort_values("timestamp").reset_index(drop=True)
    return df


def _build_series(df: pd.DataFrame, warnings: list[str]) -> RollingDemoSeries:
    ts: list[str] = []
    arrays: dict[str, list[float | None]] = {k: [] for k in _COLUMN_SERIES_MAP}

    for _, row in df.iterrows():
        ts.append(pd.Timestamp(row["timestamp"]).isoformat())
        for series_key, (col, label) in _COLUMN_SERIES_MAP.items():
            val = row.get(col)
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                arrays[series_key].append(float(val))
            else:
                arrays[series_key].append(None)
                if col not in df.columns and col not in [x[0] for x in _COLUMN_SERIES_MAP.values()]:
                    pass  # column absent — first occurrence captured below

    # Check for missing columns
    present = set(df.columns)
    for series_key, (col, label) in _COLUMN_SERIES_MAP.items():
        if col not in present:
            warnings.append(f"列 '{col}' ({label}) 不在数据中，对应 series '{series_key}' 全为 null")

    return RollingDemoSeries(timestamps=ts, **arrays)


def _build_panels(series: RollingDemoSeries) -> list[RollingDemoPanel]:
    panels: list[RollingDemoPanel] = []

    # Load — line chart
    has_actual = any(x is not None for x in series.load_actual)
    load_metrics: dict[str, float | int | str] = {}
    if has_actual:
        actuals = [x for x in series.load_actual if x is not None]
        if actuals:
            s = pd.Series(actuals)
            load_metrics["mean_mw"] = round(float(s.mean()), 1)
            load_metrics["max_mw"] = round(float(s.max()), 1)
            load_metrics["min_mw"] = round(float(s.min()), 1)
    panels.append(RollingDemoPanel(
        id="load", title="负荷曲线", chart_type="line",
        metrics=load_metrics,
    ))

    # Price — heatmap
    has_rt = any(x is not None for x in series.price_rt)
    has_da = any(x is not None for x in series.price_da)
    price_metrics: dict[str, float | int | str] = {}
    if has_rt:
        vals = [x for x in series.price_rt if x is not None]
        if vals:
            s = pd.Series(vals)
            price_metrics["rt_mean"] = round(float(s.mean()), 1)
            price_metrics["rt_max"] = round(float(s.max()), 1)
    if has_da:
        vals = [x for x in series.price_da if x is not None]
        if vals:
            s = pd.Series(vals)
            price_metrics["da_mean"] = round(float(s.mean()), 1)
            price_metrics["da_max"] = round(float(s.max()), 1)
    panels.append(RollingDemoPanel(
        id="price", title="电价形态", chart_type="heatmap",
        metrics=price_metrics,
    ))

    # Wind + Solar — area
    has_wind = any(x is not None for x in series.wind_actual)
    has_solar = any(x is not None for x in series.solar_actual)
    re_metrics: dict[str, float | int | str] = {}
    if has_wind:
        vals = [x for x in series.wind_actual if x is not None]
        if vals:
            re_metrics["wind_mean"] = round(float(pd.Series(vals).mean()), 1)
    if has_solar:
        vals = [x for x in series.solar_actual if x is not None]
        if vals:
            re_metrics["solar_mean"] = round(float(pd.Series(vals).mean()), 1)
    panels.append(RollingDemoPanel(
        id="renewable", title="风光出力", chart_type="area",
        metrics=re_metrics,
    ))

    # Evidence
    panels.append(RollingDemoPanel(
        id="evidence", title="解释性证据", chart_type="evidence",
    ))

    return panels


def _build_strategy(df: pd.DataFrame, warnings: list[str]) -> RollingDemoStrategy:
    try:
        timestamps = [pd.Timestamp(value).isoformat() for value in df["timestamp"]]
        if (
            len(df) != REPLAY_POINTS
            or not timestamps
            or timestamps[0] != REPLAY_START
            or timestamps[-1] != REPLAY_END
        ):
            raise ValueError("策略证据仅支持固定的山东 2025 年 10 月 30 天场景")
        test_market = _load_window(
            "2025-10-01", TEST_POINTS // TimeConfig.points_per_day
        )
        snapshot = build_strategy_evidence(df, test_market, _REPORTS_ROOT)
        return RollingDemoStrategy(**snapshot)
    except Exception as exc:
        reason = f"30 天策略证据不可用: {exc}"
        warnings.append(reason)
        return RollingDemoStrategy(status="degraded", degradation_reason=reason)


def _build_reports(warnings: list[str]) -> list[RollingDemoReportEvidence]:
    reports: list[RollingDemoReportEvidence] = []

    # Known report subdirs and their JSON files
    known_reports: list[tuple[str, str, str, str]] = [
        ("weather_tier4", "weather_tier4/validation", "Weather Tier4 负荷预测验证", "weather_tier4_validation.json"),
        ("renewable_forecaster", "renewable_forecaster/validation", "风光出力预测验证", "renewable_forecast_validation.json"),
        ("rl_full_dataset", "rl_full_dataset/evaluation", "RL 全量评估", "evaluation_metrics.csv"),
    ]

    for subdir, rid, title, filename in known_reports:
        dir_path = _REPORTS_ROOT / subdir
        file_path = dir_path / filename
        if not dir_path.exists() or not file_path.exists():
            warnings.append(f"报告 '{rid}' 文件 {filename} 未找到")
            reports.append(RollingDemoReportEvidence(
                id=rid, title=title, status="missing",
                summary="报告文件未找到。",
            ))
            continue

        try:
            if filename.endswith(".json"):
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                summary = ""
                json_metrics: dict = {}
                if isinstance(data, dict):
                    interp = data.get("interpretation", {}) or {}
                    summary = interp.get("summary", "") if isinstance(interp, dict) else ""
                    experiments = data.get("experiments", {}) or {}
                    baseline = experiments.get("baseline_tier3", {}).get("metrics", {}) or {}
                    weather = experiments.get("weather_tier4", {}).get("metrics", {}) or {}
                    if baseline.get("mae") is not None:
                        json_metrics["baseline_mae"] = _round_val(baseline["mae"], 2)
                    if weather.get("mae") is not None:
                        json_metrics["weather_mae"] = _round_val(weather["mae"], 2)
                    # renewable
                    for src in ("wind", "solar"):
                        exp = experiments.get(src, {}) or {}
                        m = exp.get("metrics", {}) or {}
                        if m.get("mae") is not None:
                            json_metrics[f"{src}_mae"] = _round_val(m["mae"], 2)
                        if m.get("nrmse") is not None:
                            json_metrics[f"{src}_nrmse"] = _round_val(m["nrmse"], 4)
                else:
                    summary = ""
                status = data.get("status", "ok") if isinstance(data, dict) else "ok"
                reports.append(RollingDemoReportEvidence(
                    id=rid, title=title, status=status,
                    summary=summary or f"{title} 验证结果。",
                    metrics=json_metrics,
                ))
            elif filename.endswith(".csv"):
                df_csv = pd.read_csv(file_path)
                csv_metrics: dict[str, float | int | str] = {}
                for _, r in df_csv.iterrows():
                    strat = r.get("strategy", "")
                    pnl_val = r.get("total_pnl")
                    if strat and pnl_val is not None:
                        try:
                            csv_metrics[f"pnl_{strat}"] = _round_val(float(pnl_val), 2)
                        except (TypeError, ValueError):
                            pass
                reports.append(RollingDemoReportEvidence(
                    id=rid, title=title, status="ok",
                    summary="山东全量数据上的 RL 策略评估。",
                    metrics=csv_metrics,
                ))
        except Exception as exc:
            warnings.append(f"读取报告 '{rid}' 失败: {exc}")
            reports.append(RollingDemoReportEvidence(
                id=rid, title=title, status="error",
                summary=f"读取失败: {exc}",
            ))

    # full_real_run SUMMARY.json
    frr_root = _REPORTS_ROOT / "full_real_run"
    if frr_root.exists():
        for run_dir in sorted(frr_root.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_path = run_dir / "SUMMARY.json"
            if not summary_path.exists():
                continue
            try:
                with summary_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                rid = f"full_real_run/{run_dir.name}"
                tasks = data.get("tasks", {}) or {}
                metrics: dict[str, float | int | str] = {}
                for task_name, entry in tasks.items():
                    status = (entry or {}).get("status", "unknown")
                    metrics[f"{task_name}_status"] = str(status)
                reports.append(RollingDemoReportEvidence(
                    id=rid, title=f"全量运行 ({run_dir.name})", status="ok",
                    summary="Weather + 风光 + 电价 + RL 全量运行汇总。",
                    metrics=metrics,
                ))
            except Exception as exc:
                warnings.append(f"读取 full_real_run/{run_dir.name} 失败: {exc}")

    return reports


def _round_val(v: Any, digits: int = 2) -> float | int | str:
    try:
        return round(float(v), digits)
    except (TypeError, ValueError):
        return str(v)


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════


def build_rolling_demo(start: str | None = None, days: int = 30) -> RollingDemoResponse:
    """Build read-only dashboard payload from Shandong historical data.

    Args:
        start: Shandong market date (YYYY-MM-DD). Default '2025-10-01'.
        days: Number of days to include, clamped to [1, 30].

    Returns:
        RollingDemoResponse with meta, series, panels, strategy, reports, warnings.
    """
    warnings: list[str] = []
    clamped_days = max(1, min(days, 30))
    if clamped_days != days:
        warnings.append(f"days 参数已从 {days} 调整为 {clamped_days}（上限 30）")

    start_str = start or "2025-10-01"
    try:
        start_dt = pd.Timestamp(start_str)
        if start_dt.tzinfo is None:
            start_dt = start_dt.tz_localize("Asia/Shanghai")
        else:
            start_dt = start_dt.tz_convert("Asia/Shanghai")
    except Exception:
        warnings.append(f"start 参数 '{start_str}' 解析失败，回退到 2025-10-01")
        start_dt = pd.Timestamp("2025-10-01", tz="Asia/Shanghai")
        start_str = "2025-10-01"

    end_dt = start_dt + pd.Timedelta(days=clamped_days)

    # Load
    try:
        df = _load_window(start_str, clamped_days)
    except Exception as exc:
        warnings.append(f"山东数据加载失败: {exc}")
        return RollingDemoResponse(
            meta=RollingDemoMeta(
                source="shandong",
                start=start_dt.isoformat(), end=end_dt.isoformat(),
                frequency=TimeConfig.freq, points_per_day=TimeConfig.points_per_day,
                rows=0,
            ),
            warnings=warnings,
        )

    if df.empty:
        warnings.append(f"窗口 {start_str} ~ {end_dt.date()} 内无数据")
        return RollingDemoResponse(
            meta=RollingDemoMeta(
                source="shandong",
                start=start_dt.isoformat(), end=end_dt.isoformat(),
                frequency=TimeConfig.freq, points_per_day=TimeConfig.points_per_day,
                rows=0,
            ),
            warnings=warnings,
        )

    series = _build_series(df, warnings)
    panels = _build_panels(series)
    strategy = _build_strategy(df, warnings)
    reports = _build_reports(warnings)

    # Wire warning ids into panels
    for i, w in enumerate(warnings):
        for panel in panels:
            if panel.chart_type == "ranking" and "策略" in w:
                panel.warning_ids.append(i)
            elif panel.chart_type == "evidence" and "报告" in w:
                panel.warning_ids.append(i)

    meta = RollingDemoMeta(
        source="shandong",
        start=pd.Timestamp(df["timestamp"].min()).isoformat(),
        end=pd.Timestamp(df["timestamp"].max()).isoformat(),
        frequency=TimeConfig.freq,
        points_per_day=TimeConfig.points_per_day,
        rows=len(df),
    )

    return RollingDemoResponse(
        meta=meta,
        series=series,
        panels=panels,
        strategy=strategy,
        reports=reports,
        warnings=warnings,
    )
