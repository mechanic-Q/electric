#!/usr/bin/env python3
"""Validate WeatherFetcher Tier4 feature quality vs ground-truth."""
import argparse
import datetime
import json
import logging
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_WEATHER_COLUMN_NOTE = "No weather columns found in feature_df after merge"


def resolve_weather_source(
    weather_df: pd.DataFrame | None = None,
    weather_cache_path: str | Path | None = None,
    fetch_if_missing: bool = True,
    load_df: pd.DataFrame | None = None,
) -> tuple[str, pd.DataFrame | None]:
    """
    按四阶优先级解析 weather 来源：explicit → cache → fetch → degraded.

    纯函数设计（fetch 分支写入 cache 为必要副作用），不修改全局状态。

    Returns:
        (source_label, weather_data)
        source_label: "explicit" / "cache" / "fetch" / "degraded"
        weather_data: DataFrame 或 None
    """
    # ── 优先级 1: 显式传入 weather_df ──
    if weather_df is not None:
        if not weather_df.empty and len(weather_df.columns) > 0:
            logger.info(
                "Weather source: explicit (%d cols)", len(weather_df.columns)
            )
            return ("explicit", weather_df)
        logger.debug("Explicit weather_df is empty, skipping")

    # ── 解析 cache 路径 ──
    from ellectric.pipeline.features import _resolve_weather_cache
    cache_path = _resolve_weather_cache(weather_cache_path)

    # ── 优先级 2: parquet cache ──
    if cache_path.exists():
        try:
            cached = pd.read_parquet(cache_path)
            if not cached.empty and len(cached.columns) > 0:
                logger.info("Weather source: cache (%s)", cache_path)
                return ("cache", cached)
            logger.warning("Weather cache parquet is empty: %s", cache_path)
        except Exception as e:
            logger.warning(
                "Failed to read weather cache '%s': %s", cache_path, e
            )

    # ── 优先级 3: fetch（允许时）──
    if fetch_if_missing and load_df is not None and "timestamp" in load_df.columns:
        try:
            from ellectric.fetch.weather import WeatherFetcher

            fetcher = WeatherFetcher()
            start = pd.Timestamp(load_df["timestamp"].min()).strftime("%Y-%m-%d")
            end = pd.Timestamp(load_df["timestamp"].max()).strftime("%Y-%m-%d")
            fetched = fetcher.fetch_historical(start, end)
            if not fetched.empty and len(fetched.columns) > 0:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                fetched.to_parquet(cache_path)
                logger.info(
                    "Weather source: fetch (cached to %s)", cache_path
                )
                return ("fetch", fetched)
            logger.error("WeatherFetcher returned empty DataFrame")
        except Exception as e:
            logger.error("WeatherFetcher fetch failed: %s", e)

    # ── 降级 ──
    logger.warning("Weather source: degraded (no data available)")
    return ("degraded", None)


def build_weather_quality_report(
    load_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    weather_columns: list[str],
    weather_source: str,
) -> dict:
    """
    生成 weather 数据质量报告。

    只记录事实，不做硬阈值检查，不阻断。
    """
    from ellectric.config import TimeConfig

    report: dict = {}
    report["weather_source"] = weather_source
    report["weather_columns"] = list(weather_columns)
    report["weather_column_count"] = len(weather_columns)
    report["weather_features_available"] = len(weather_columns) > 0

    # ── 缺失率 ──
    if report["weather_features_available"]:
        n = len(feature_df)
        missing = {}
        for col in weather_columns:
            if col in feature_df.columns:
                missing[col] = float(
                    feature_df[col].isna().sum() / n
                )
            else:
                missing[col] = 1.0
        report["missing_rate_by_column"] = missing
        rates = list(missing.values())
        report["overall_missing_rate"] = float(
            sum(rates) / len(rates)
        ) if rates else 0.0
    else:
        report["missing_rate_by_column"] = {}
        report["overall_missing_rate"] = 0.0

    # ── 时间范围 ──
    has_timestamp = "timestamp" in feature_df.columns
    if has_timestamp:
        ts = feature_df["timestamp"]
        report["time_range"] = {
            "start": str(ts.min()),
            "end": str(ts.max()),
            "freq": TimeConfig.freq,
        }
        tz = getattr(ts.dt, "tz", None)
        if callable(tz):
            tz = tz()
        report["timezone"] = str(tz) if tz is not None else "unknown"
    else:
        report["time_range"] = {"start": None, "end": None, "freq": None}
        report["timezone"] = "unknown"

    # ── 覆盖范围 ──
    report["coverage"] = {}
    report["coverage"]["total_points"] = len(feature_df)
    if report["weather_features_available"] and has_timestamp:
        present_cols = [c for c in weather_columns if c in feature_df.columns]
        if present_cols:
            covered = int(feature_df[present_cols].notna().any(axis=1).sum())
        else:
            covered = 0
        report["coverage"]["weather_covered_points"] = covered
        total = len(feature_df)
        report["coverage"]["coverage_ratio"] = float(
            covered / total
        ) if total > 0 else 0.0
    else:
        report["coverage"]["weather_covered_points"] = 0
        report["coverage"]["coverage_ratio"] = 0.0

    # ── 备注 ──
    notes: list[str] = []
    if weather_source == "degraded":
        notes.append("Weather source is degraded: no weather data available")
    if not report["weather_features_available"]:
        notes.append(_WEATHER_COLUMN_NOTE)
    if not has_timestamp:
        notes.append(
            "load_df missing timestamp column; "
            "time_range/coverage not computed"
        )
    if has_timestamp and report["timezone"] == "unknown":
        notes.append("timestamp column has no timezone info")
    if report["overall_missing_rate"] > 0.1:
        notes.append("Overall weather missing rate > 0.1")
    if any(
        r == 1.0
        for r in report["missing_rate_by_column"].values()
    ):
        notes.append("Some weather columns are fully missing")

    report["notes"] = notes
    return report


def compute_metrics(
    actuals: np.ndarray,
    predictions: np.ndarray,
) -> dict:
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    mae = float(mean_absolute_error(actuals, predictions))
    rmse = float(np.sqrt(mean_squared_error(actuals, predictions)))

    mask = actuals != 0
    if mask.sum() == 0:
        mape = None
    else:
        mape = float(
            np.mean(np.abs((actuals[mask] - predictions[mask]) / actuals[mask])) * 100
        )

    return {"mae": mae, "rmse": rmse, "mape": mape}


def run_ablation_experiment(
    load_df: pd.DataFrame,
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    from ellectric.pipeline.features import FeatureEngineer, prepare_features
    from ellectric.pipeline.forecaster import XGBoostForecaster

    notes: list[str] = []
    engineer = FeatureEngineer()
    tier3_cols = engineer.get_feature_columns("tier3")

    # ── Baseline: Tier1-3 features ──
    baseline_feature_df = prepare_features(
        load_df, tiers=["tier1", "tier2", "tier3"]
    )
    X_baseline = baseline_feature_df[tier3_cols].copy()
    y = load_df["load_mw"]
    input_rows = len(load_df)

    try:
        forecaster_baseline = XGBoostForecaster()
        baseline_result = forecaster_baseline.train_evaluate(X_baseline, y)
        baseline_metrics = compute_metrics(
            baseline_result["actuals"], baseline_result["predictions"]
        )
        baseline_sample_count = len(baseline_result["actuals"])
    except Exception as e:
        notes.append(f"Baseline training failed: {e}")
        degraded = {
            "feature_count": len(tier3_cols),
            "input_rows": input_rows,
            "sample_count": 0,
            "metrics": {"mae": None, "rmse": None, "mape": None},
        }
        return {
            "baseline_tier3": degraded,
            "weather_tier4": {
                "feature_count": 0,
                "input_rows": input_rows,
                "sample_count": 0,
                "metrics": {"mae": None, "rmse": None, "mape": None},
            },
            "delta": {
                "mae_delta": None,
                "rmse_delta": None,
                "mape_delta": None,
                "mae_delta_pct": None,
            },
            "notes": notes,
        }

    if baseline_metrics["mape"] is None:
        notes.append("MAPE: all actual values were zero for baseline, MAPE set to None")

    baseline_data = {
        "feature_count": len(tier3_cols),
        "input_rows": input_rows,
        "sample_count": baseline_sample_count,
        "metrics": baseline_metrics,
    }

    # ── Weather: Tier1-4 features ──
    weather_feature_df = prepare_features(
        load_df,
        tiers=["tier1", "tier2", "tier3", "tier4"],
        weather_cache_path=weather_cache,
        fetch_if_missing=fetch_if_missing,
    )

    tier3_cols_set = set(tier3_cols)
    weather_all_cols = [
        c for c in weather_feature_df.columns if c not in ("timestamp", "load_mw")
    ]
    weather_cols_detected = [c for c in weather_all_cols if c not in tier3_cols_set]
    weather_feature_count = len(weather_all_cols)

    if not weather_cols_detected:
        notes.append(
            "No weather columns found in feature_df; weather experiment degraded"
        )
        weather_data = {
            "feature_count": weather_feature_count,
            "input_rows": input_rows,
            "sample_count": 0,
            "metrics": {"mae": None, "rmse": None, "mape": None},
        }
    else:
        X_weather = weather_feature_df[weather_all_cols].copy()
        try:
            forecaster_weather = XGBoostForecaster()
            weather_result = forecaster_weather.train_evaluate(X_weather, y)
            weather_metrics = compute_metrics(
                weather_result["actuals"], weather_result["predictions"]
            )
            if weather_metrics["mape"] is None:
                notes.append(
                    "MAPE: all actual values were zero for weather, MAPE set to None"
                )
            weather_data = {
                "feature_count": weather_feature_count,
                "input_rows": input_rows,
                "sample_count": len(weather_result["actuals"]),
                "metrics": weather_metrics,
            }
        except Exception as e:
            notes.append(f"Weather training failed: {e}")
            weather_data = {
                "feature_count": weather_feature_count,
                "input_rows": input_rows,
                "sample_count": 0,
                "metrics": {"mae": None, "rmse": None, "mape": None},
            }

    # ── Delta ──
    w = weather_data["metrics"]
    b = baseline_data["metrics"]
    if w["mae"] is not None and b["mae"] is not None:
        mae_delta = w["mae"] - b["mae"]
        rmse_delta = w["rmse"] - b["rmse"]
        mape_delta = (
            w["mape"] - b["mape"]
            if (w["mape"] is not None and b["mape"] is not None)
            else None
        )
        mae_delta_pct = (mae_delta / b["mae"]) * 100 if b["mae"] != 0 else None
    else:
        mae_delta = None
        rmse_delta = None
        mape_delta = None
        mae_delta_pct = None

    return {
        "baseline_tier3": baseline_data,
        "weather_tier4": weather_data,
        "delta": {
            "mae_delta": mae_delta,
            "rmse_delta": rmse_delta,
            "mape_delta": mape_delta,
            "mae_delta_pct": mae_delta_pct,
        },
        "notes": notes,
    }


def run_validation(
    start: str | None = None,
    end: str | None = None,
    output_dir: str = "ellectric/reports/weather_tier4",
    weather_cache: str | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    from ellectric.pipeline.shandong_loader import ShandongDataLoader
    from ellectric.pipeline.features import FeatureEngineer

    # ── 加载负荷数据 ──
    try:
        loader = ShandongDataLoader()
        load_df = loader.load_data(start, end)
    except Exception as e:
        logger.error("ShandongDataLoader failed: %s", e)
        return {
            "status": "error",
            "error": f"Data load failed: {e}",
            "report_paths": [],
        }

    logger.info(
        "Loaded %d rows, range %s ~ %s",
        len(load_df),
        str(load_df["timestamp"].min()),
        str(load_df["timestamp"].max()),
    )

    # ── 解析 weather 来源 ──
    source_label, weather_data = resolve_weather_source(
        weather_df=None,
        weather_cache_path=weather_cache,
        fetch_if_missing=fetch_if_missing,
        load_df=load_df,
    )

    # ── 构建基础特征 (Tier1-3) + Tier4 weather ──
    engineer = FeatureEngineer()
    feature_df = engineer.add_tier1_features(load_df)
    feature_df = engineer.add_tier2_features(feature_df)
    feature_df = engineer.add_tier3_features(feature_df)

    feature_df = engineer.add_tier4_weather_features(
        feature_df,
        weather_df=weather_data,
        weather_cache_path=weather_cache,
        fetch_if_missing=False,
    )

    weather_cols = list(engineer._weather_columns)

    # ── 生成质量报告 ──
    quality = build_weather_quality_report(
        load_df=load_df,
        feature_df=feature_df,
        weather_columns=weather_cols,
        weather_source=source_label,
    )

    # ── Ablation experiment: Tier3 vs Tier4 ──
    experiments = run_ablation_experiment(
        load_df,
        weather_cache=weather_cache,
        fetch_if_missing=fetch_if_missing,
    )

    # ── Interpretation ──
    b_mae = experiments["baseline_tier3"]["metrics"]["mae"]
    w_entry = experiments["weather_tier4"]
    w_mae = w_entry["metrics"]["mae"]
    delta = experiments["delta"]

    if w_mae is not None:
        summary = (
            f"Ablation: baseline MAE={b_mae:.2f}, "
            f"weather MAE={w_mae:.2f}, "
            f"delta={delta['mae_delta']:+.2f} ({delta['mae_delta_pct']:+.2f}%)"
        )
    else:
        summary = "Ablation: degraded (weather features unavailable or training failed)"

    from ellectric.config import TimeConfig

    metadata = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "data_source": quality.get("weather_source", "degraded"),
        "data_version": "1",
        "time_config": {
            "freq": TimeConfig.freq,
            "points_per_day": TimeConfig.points_per_day,
        },
        "start": start,
        "end": end,
    }

    interpretation = {
        "hard_threshold_applied": False,
        "summary": summary,
    }

    result = {
        "status": "ok",
        "metadata": metadata,
        "weather_quality": quality,
        "experiments": experiments,
        "interpretation": interpretation,
    }

    result["report_paths"] = write_reports(result, Path(output_dir))
    return result


# ── Report writing ──


def _json_serializer(obj):
    if isinstance(obj, pd.Timestamp):
        s = obj.isoformat()
        if obj.tzinfo is None:
            s += "Z"
        return s
    if obj is pd.NaT:
        return None
    if isinstance(obj, (datetime.datetime,)):
        s = obj.isoformat()
        if obj.tzinfo is None:
            s += "Z"
        return s
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def _atomic_write(content: str, path: Path):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
            mode="w",
            encoding="utf-8",
        ) as f:
            tmp_path = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    except Exception:
        if tmp_path is not None:
            try:
                os.unlink(str(tmp_path))
            except Exception:
                pass
        raise


def _write_json_report(result: dict, path: Path):
    content = json.dumps(
        result, ensure_ascii=False, indent=2, default=_json_serializer
    )
    _atomic_write(content, path)


def _escape_md(text) -> str:
    return str(text).replace("|", "\\|")


def _cell(val, fmt=".4f"):
    if val is None:
        return "—"
    return _escape_md(f"{val:{fmt}}")


def _cell_delta(val, fmt=".4f"):
    if val is None:
        return "—"
    return _escape_md(f"{val:+{fmt}}")


def _write_markdown_report(result: dict, path: Path):
    meta = result.get("metadata", {}) or {}
    weather_quality = result.get("weather_quality")
    experiments = result.get("experiments")
    interpretation = result.get("interpretation")

    lines = []

    # ── Title ──
    generated_at = _escape_md(meta.get("generated_at", "N/A"))
    data_source = _escape_md(meta.get("data_source", "N/A"))
    lines.append("# Weather Tier4 Validation Report\n")
    lines.append(f"*Generated: {generated_at} | Data source: {data_source}*\n")

    # ── Metadata ──
    lines.append("## Metadata\n")
    tc = meta.get("time_config", {}) or {}
    lines.append(f"- **generated_at**: {generated_at}")
    lines.append(f"- **data_source**: {data_source}")
    lines.append(
        "- **data_version**: %s" % _escape_md(meta.get("data_version", "N/A"))
    )
    lines.append(
        "- **time_config**: freq=%s, points_per_day=%s"
        % (
            _escape_md(str(tc.get("freq", "N/A"))),
            _escape_md(str(tc.get("points_per_day", "N/A"))),
        )
    )
    lines.append("- **start**: %s" % _escape_md(str(meta.get("start", "N/A"))))
    lines.append("- **end**: %s\n" % _escape_md(str(meta.get("end", "N/A"))))

    # ── Weather Quality ──
    lines.append("## Weather Quality\n")
    if weather_quality is None:
        lines.append("Not available.\n")
    else:
        lines.append(
            "- **weather_source**: %s"
            % _escape_md(str(weather_quality.get("weather_source", "N/A")))
        )
        lines.append(
            "- **weather_features_available**: %s"
            % weather_quality.get("weather_features_available", "N/A")
        )
        lines.append(
            "- **weather_column_count**: %s"
            % weather_quality.get("weather_column_count", "N/A")
        )

        cols = weather_quality.get("weather_columns", [])
        if cols:
            lines.append("- **weather_columns**: %s" % _escape_md(", ".join(cols)))
        else:
            lines.append("- **weather_columns**: (none)")

        mr = weather_quality.get("overall_missing_rate", 0)
        if isinstance(mr, (int, float)):
            lines.append("- **overall_missing_rate**: %.1f%%" % (mr * 100))
        else:
            lines.append(
                "- **overall_missing_rate**: %s" % _escape_md(str(mr))
            )

        tr = weather_quality.get("time_range", {}) or {}
        lines.append(
            "- **time_range**: start=%s, end=%s, freq=%s"
            % (
                _escape_md(str(tr.get("start", "N/A"))),
                _escape_md(str(tr.get("end", "N/A"))),
                _escape_md(str(tr.get("freq", "N/A"))),
            )
        )
        lines.append(
            "- **timezone**: %s"
            % _escape_md(str(weather_quality.get("timezone", "N/A")))
        )

        cov = weather_quality.get("coverage", {}) or {}
        cr = cov.get("coverage_ratio", 0)
        if isinstance(cr, (int, float)):
            lines.append("- **coverage_ratio**: %.1f%%" % (cr * 100))
        else:
            lines.append("- **coverage_ratio**: %s" % _escape_md(str(cr)))

        wq_notes = weather_quality.get("notes", [])
        if wq_notes:
            lines.append("- **notes**:")
            for n in wq_notes:
                lines.append("  - %s" % _escape_md(n))
        lines.append("")

    # ── Experiment Comparison ──
    lines.append("## Experiment Comparison\n")
    if experiments is None:
        lines.append("Not available.")
    else:
        b = experiments.get("baseline_tier3", {}) or {}
        w = experiments.get("weather_tier4", {}) or {}
        d = experiments.get("delta", {}) or {}

        bm = b.get("metrics", {}) or {}
        wm = w.get("metrics", {}) or {}

        lines.append("### Metrics Comparison\n")
        lines.append("| Metric | Baseline Tier3 | Weather Tier4 | Delta | Delta % |")
        lines.append("|--------|---------------|--------------|-------|---------|")

        # MAE
        mae_b = bm.get("mae")
        mae_w = wm.get("mae")
        mae_d = d.get("mae_delta")
        mae_dp = d.get("mae_delta_pct")
        lines.append(
            "| MAE | %s | %s | %s | %s |"
            % (
                _cell(mae_b),
                _cell(mae_w),
                _cell_delta(mae_d),
                _cell(mae_dp, ".2f"),
            )
        )

        # RMSE
        rmse_b = bm.get("rmse")
        rmse_w = wm.get("rmse")
        rmse_d = d.get("rmse_delta")
        lines.append(
            "| RMSE | %s | %s | %s | — |"
            % (_cell(rmse_b), _cell(rmse_w), _cell_delta(rmse_d))
        )

        # MAPE
        mape_b = bm.get("mape")
        mape_w = wm.get("mape")
        mape_d = d.get("mape_delta")
        lines.append(
            "| MAPE | %s | %s | %s | — |"
            % (
                _cell(mape_b, ".2f"),
                _cell(mape_w, ".2f"),
                _cell_delta(mape_d, ".2f"),
            )
        )

        lines.append("")
        lines.append("### Config Comparison\n")
        lines.append("| Config | Baseline Tier3 | Weather Tier4 |")
        lines.append("|--------|---------------|--------------|")
        lines.append(
            "| Feature Count | %s | %s |"
            % (
                _escape_md(str(b.get("feature_count", "—"))),
                _escape_md(str(w.get("feature_count", "—"))),
            )
        )
        lines.append(
            "| Input Rows | %s | %s |"
            % (
                _escape_md(str(b.get("input_rows", "—"))),
                _escape_md(str(w.get("input_rows", "—"))),
            )
        )
        lines.append(
            "| Sample Count | %s | %s |"
            % (
                _escape_md(str(b.get("sample_count", "—"))),
                _escape_md(str(w.get("sample_count", "—"))),
            )
        )
        lines.append("")

    # ── Delta ──
    lines.append("## Delta\n")
    if experiments is not None:
        d_exp = experiments.get("delta", {}) or {}
        has_any = any(
            d_exp.get(k) is not None
            for k in ("mae_delta", "rmse_delta", "mape_delta")
        )
        if has_any:
            b_exp = experiments.get("baseline_tier3", {}) or {}
            w_exp = experiments.get("weather_tier4", {}) or {}
            bm_exp = b_exp.get("metrics", {}) or {}
            wm_exp = w_exp.get("metrics", {}) or {}

            mae_b_v = bm_exp.get("mae")
            mae_w_v = wm_exp.get("mae")
            mae_d_v = d_exp.get("mae_delta")
            mae_dp_v = d_exp.get("mae_delta_pct")
            if (
                mae_b_v is not None
                and mae_w_v is not None
                and mae_d_v is not None
            ):
                dp_str = " (%+.2f%%)" % mae_dp_v if mae_dp_v is not None else ""
                lines.append(
                    "MAE: baseline=%.4f, weather=%.4f, delta=%+.4f%s"
                    % (mae_b_v, mae_w_v, mae_d_v, dp_str)
                )

            rmse_b_v = bm_exp.get("rmse")
            rmse_w_v = wm_exp.get("rmse")
            rmse_d_v = d_exp.get("rmse_delta")
            if (
                rmse_b_v is not None
                and rmse_w_v is not None
                and rmse_d_v is not None
            ):
                lines.append(
                    "RMSE: baseline=%.4f, weather=%.4f, delta=%+.4f"
                    % (rmse_b_v, rmse_w_v, rmse_d_v)
                )

            mape_b_v = bm_exp.get("mape")
            mape_w_v = wm_exp.get("mape")
            mape_d_v = d_exp.get("mape_delta")
            if (
                mape_b_v is not None
                and mape_w_v is not None
                and mape_d_v is not None
            ):
                lines.append(
                    "MAPE: baseline=%.2f%%, weather=%.2f%%, delta=%+.2f%%"
                    % (mape_b_v, mape_w_v, mape_d_v)
                )
        else:
            lines.append("No significant improvement observed in this run.")
    else:
        lines.append("No significant improvement observed in this run.")
    lines.append("")

    # ── Interpretation ──
    lines.append("## Interpretation\n")
    lines.append(
        "This validation is report-only — hard thresholds are not enforced.\n"
    )
    lines.append(
        "Weather Tier4 features serve as an optional enhancement layer for "
        "load forecasting. "
        "This run reports metrics without requiring hard accuracy improvement "
        "thresholds. "
        "The baseline uses Tier1-3 features; the experiment adds Tier4 "
        "weather features. "
        "Model selection, feature engineering, and hyperparameter tuning "
        "may yield different results.\n"
    )
    if interpretation is not None:
        lines.append(
            "**Summary**: %s\n"
            % _escape_md(interpretation.get("summary", "N/A"))
        )
    else:
        lines.append("**Summary**: N/A\n")

    # ── Notes ──
    lines.append("## Notes\n")
    all_notes = []
    if weather_quality is not None:
        all_notes.extend(weather_quality.get("notes", []))
    if experiments is not None:
        all_notes.extend(experiments.get("notes", []))
    if all_notes:
        for n in all_notes:
            lines.append("- %s" % _escape_md(n))
    else:
        lines.append("None.")
    lines.append("")

    _atomic_write("\n".join(lines), path)


def write_reports(
    result: dict,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write JSON and Markdown reports to output_dir.

    Args:
        result: Complete validation result dict with keys:
            metadata, weather_quality, experiments, interpretation.
        output_dir: Directory to write reports into. Created if missing.

    Returns:
        Dict with keys 'json' and 'markdown' mapping to absolute report paths.

    Raises:
        OSError: If output_dir creation or file write fails.
    """
    output_dir = Path(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    result.setdefault("metadata", {})
    result.setdefault("weather_quality", None)
    result.setdefault("experiments", None)
    result.setdefault("interpretation", None)

    result["metadata"]["generated_at"] = datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    json_path = output_dir / "weather_tier4_validation.json"
    md_path = output_dir / "weather_tier4_validation.md"

    paths: dict[str, str] = {}

    try:
        _write_json_report(result, json_path)
        paths["json"] = str(json_path.resolve())
    except Exception as e:
        logger.error("Failed to write JSON report to %s: %s", json_path, e)

    try:
        _write_markdown_report(result, md_path)
        paths["markdown"] = str(md_path.resolve())
    except Exception as e:
        logger.error(
            "Failed to write Markdown report to %s: %s", md_path, e
        )

    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate WeatherFetcher Tier4 feature quality"
    )
    parser.add_argument(
        "--output-dir",
        default="ellectric/reports/weather_tier4",
        help="Directory for validation reports",
    )
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--weather-cache", default=None, help="Weather cache directory")
    parser.add_argument(
        "--no-fetch", action="store_true", help="Skip fetching missing weather data"
    )
    args = parser.parse_args()

    result = run_validation(
        start=args.start,
        end=args.end,
        output_dir=args.output_dir,
        weather_cache=args.weather_cache,
        fetch_if_missing=not args.no_fetch,
    )
    if result.get("report_paths"):
        print("Reports generated:")
        for p in result["report_paths"]:
            print(f"  {p}")
    print(f"Validation status: {result['status']}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, ".")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    main()
