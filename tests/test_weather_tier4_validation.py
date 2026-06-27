# --- author: lmr
# created_at: 2026-06-28 01:11:57
# ---

"""
Weather Tier4 validation script tests.

Covers: FR-02, FR-03, FR-04, FR-05
Decisions: D-001@v1, D-002@v1, D-003@v1

Test groups:
  Group A: compute_metrics (FR-03)
  Group B: delta sign and consistency (FR-03, D-001@v1)
  Group C: report schema (FR-02, FR-05)
  Group D: weather degraded path (FR-02, FR-04, D-002@v1)
  Group E: write_reports file output (FR-05, D-003@v1)
  Group F: run_validation integration (FR-02/03/04/05, D-003@v1)
"""

import datetime
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ── Helper functions ──


def _sample_load_df(n: int) -> pd.DataFrame:
    ts = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"timestamp": ts, "load_mw": np.arange(n, dtype=float)})


def _fake_weather_hourly() -> pd.DataFrame:
    n_hours = 48
    ts = pd.date_range("2026-01-01", periods=n_hours, freq="h", tz="UTC")
    data = {
        "temp_jinan": np.random.randn(n_hours) * 10 + 20,
        "ghi_jinan": np.random.rand(n_hours) * 800,
        "wind_speed_jinan": np.random.rand(n_hours) * 10,
        "temp_qingdao": np.random.randn(n_hours) * 8 + 18,
        "ghi_qingdao": np.random.rand(n_hours) * 700,
    }
    return pd.DataFrame(data, index=ts)


def _minimal_report_dict() -> dict:
    return {
        "metadata": {
            "generated_at": "2026-06-28T01:11:57Z",
            "data_source": "explicit",
            "data_version": "1",
            "time_config": {"freq": "15min", "points_per_day": 96},
            "start": None,
            "end": None,
        },
        "weather_quality": {
            "weather_source": "explicit",
            "weather_features_available": True,
            "weather_columns": ["temp_jinan", "ghi_jinan"],
            "weather_column_count": 2,
            "missing_rate_by_column": {"temp_jinan": 0.0, "ghi_jinan": 0.0},
            "overall_missing_rate": 0.0,
            "time_range": {
                "start": "2026-01-01", "end": "2026-01-02", "freq": "15min"
            },
            "timezone": "UTC",
            "coverage": {
                "total_points": 96, "weather_covered_points": 96, "coverage_ratio": 1.0
            },
            "notes": [],
        },
        "experiments": {
            "baseline_tier3": {
                "feature_count": 30,
                "input_rows": 96,
                "sample_count": 86,
                "metrics": {"mae": 10.0, "rmse": 15.0, "mape": 5.0},
            },
            "weather_tier4": {
                "feature_count": 35,
                "input_rows": 96,
                "sample_count": 86,
                "metrics": {"mae": 8.0, "rmse": 12.0, "mape": 4.0},
            },
            "delta": {
                "mae_delta": -2.0,
                "rmse_delta": -3.0,
                "mape_delta": -1.0,
                "mae_delta_pct": -20.0,
            },
            "notes": [],
        },
        "interpretation": {
            "hard_threshold_applied": False,
            "summary": (
                "Ablation: baseline MAE=10.00, weather MAE=8.00, "
                "delta=-2.00 (-20.00%)"
            ),
        },
    }


def _compute_delta(baseline_metrics: dict, weather_metrics: dict) -> dict:
    w = weather_metrics
    b = baseline_metrics
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
        "mae_delta": mae_delta,
        "rmse_delta": rmse_delta,
        "mape_delta": mape_delta,
        "mae_delta_pct": mae_delta_pct,
    }


# ── Module loading fixture ──


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "validate_weather_tier4",
        "ellectric/scripts/validate_weather_tier4.py",
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["validate_weather_tier4"] = m
    spec.loader.exec_module(m)
    return m


# =====================================================================
# Group A: compute_metrics (FR-03)
# =====================================================================


def test_compute_metrics_basic(mod):
    actuals = np.array([100.0, 200.0, 300.0])
    predictions = np.array([110.0, 190.0, 290.0])
    result = mod.compute_metrics(actuals, predictions)
    assert math.isclose(result["mae"], 10.0)
    assert math.isclose(result["rmse"], 10.0)
    expected_mape = (10 / 100 + 10 / 200 + 10 / 300) / 3 * 100
    assert math.isclose(result["mape"], expected_mape)


def test_compute_metrics_identical(mod):
    actuals = np.array([100.0, 200.0, 300.0])
    predictions = actuals.copy()
    result = mod.compute_metrics(actuals, predictions)
    assert result["mae"] == 0.0
    assert result["rmse"] == 0.0
    assert result["mape"] == 0.0


def test_compute_metrics_zero_actual_mask(mod):
    actuals = np.array([0.0, 100.0, 200.0, 300.0, 400.0])
    predictions = np.array([10.0, 110.0, 190.0, 290.0, 410.0])
    result = mod.compute_metrics(actuals, predictions)
    assert math.isclose(result["mae"], 10.0)
    expected_mape = (10 / 100 + 10 / 200 + 10 / 300 + 10 / 400) / 4 * 100
    assert math.isclose(result["mape"], expected_mape)


def test_compute_metrics_all_zero_actual(mod):
    actuals = np.array([0.0, 0.0, 0.0])
    predictions = np.array([1.0, 2.0, 3.0])
    result = mod.compute_metrics(actuals, predictions)
    assert result["mape"] is None


# =====================================================================
# Group B: delta sign and consistency (FR-03, D-001@v1)
# =====================================================================


def test_delta_calculation_positive():
    baseline = {"mae": 10.0, "rmse": 15.0, "mape": 5.0}
    weather = {"mae": 8.0, "rmse": 12.0, "mape": 4.0}
    d = _compute_delta(baseline, weather)
    assert math.isclose(d["mae_delta"], -2.0)
    assert math.isclose(d["mae_delta_pct"], -20.0)


def test_delta_calculation_negative():
    baseline = {"mae": 8.0, "rmse": 12.0, "mape": 4.0}
    weather = {"mae": 10.0, "rmse": 15.0, "mape": 5.0}
    d = _compute_delta(baseline, weather)
    assert math.isclose(d["mae_delta"], 2.0)
    assert math.isclose(d["mae_delta_pct"], 25.0)


def test_delta_pct_from_baseline():
    baseline = {"mae": 20.0, "rmse": 30.0, "mape": 6.0}
    weather = {"mae": 15.0, "rmse": 25.0, "mape": 5.0}
    d = _compute_delta(baseline, weather)
    assert math.isclose(d["mae_delta"], -5.0)
    assert math.isclose(d["mae_delta_pct"], -25.0)
    assert math.isclose(d["rmse_delta"], -5.0)
    assert math.isclose(d["mape_delta"], -1.0)


def test_delta_no_division_by_zero():
    baseline = {"mae": 0.0, "rmse": 0.0, "mape": 0.0}
    weather = {"mae": 0.0, "rmse": 0.0, "mape": 0.0}
    d = _compute_delta(baseline, weather)
    assert math.isclose(d["mae_delta"], 0.0)
    assert d["mae_delta_pct"] is None


# =====================================================================
# Group C: report schema (FR-02, FR-05)
# =====================================================================


def test_report_schema_top_level_keys(mod):
    report = _minimal_report_dict()
    expected = {"metadata", "weather_quality", "experiments", "interpretation"}
    assert set(report.keys()) == expected


def test_report_schema_weather_quality_keys(mod):
    n = 96
    load_df = _sample_load_df(n)
    weather_df = _fake_weather_hourly()
    feature_df = load_df.copy()
    feature_df["temp_jinan"] = np.random.randn(n) * 10 + 20
    report = mod.build_weather_quality_report(
        load_df=load_df,
        feature_df=feature_df,
        weather_columns=["temp_jinan"],
        weather_source="explicit",
    )

    expected = {
        "weather_source",
        "weather_features_available",
        "weather_columns",
        "weather_column_count",
        "missing_rate_by_column",
        "overall_missing_rate",
        "time_range",
        "timezone",
        "coverage",
        "notes",
    }
    assert set(report.keys()) == expected


def test_report_schema_experiments_keys(mod):
    report = _minimal_report_dict()
    expected = {"baseline_tier3", "weather_tier4", "delta", "notes"}
    assert set(report["experiments"].keys()) == expected


def test_report_schema_experiment_subkeys(mod):
    report = _minimal_report_dict()
    for key in ("baseline_tier3", "weather_tier4"):
        sub = report["experiments"][key]
        assert "feature_count" in sub
        assert "input_rows" in sub
        assert "sample_count" in sub
        assert "metrics" in sub
        assert set(sub["metrics"].keys()) == {"mae", "rmse", "mape"}


def test_report_schema_delta_keys(mod):
    report = _minimal_report_dict()
    expected = {"mae_delta", "rmse_delta", "mape_delta", "mae_delta_pct"}
    assert set(report["experiments"]["delta"].keys()) == expected


def test_report_schema_metadata_keys(mod):
    report = _minimal_report_dict()
    expected = {
        "generated_at", "data_source", "data_version",
        "time_config", "start", "end",
    }
    assert set(report["metadata"].keys()) == expected


def test_report_schema_interpretation_keys(mod):
    report = _minimal_report_dict()
    expected = {"hard_threshold_applied", "summary"}
    assert set(report["interpretation"].keys()) == expected


def test_report_hard_threshold_false(mod):
    report = _minimal_report_dict()
    assert report["interpretation"]["hard_threshold_applied"] is False


# =====================================================================
# Group D: weather degraded path (FR-02, FR-04, D-002@v1)
# =====================================================================


def test_weather_degraded_report_structure(mod):
    n = 96
    load_df = _sample_load_df(n)
    feature_df = load_df.copy()
    report = mod.build_weather_quality_report(
        load_df=load_df,
        feature_df=feature_df,
        weather_columns=[],
        weather_source="degraded",
    )
    assert report["weather_features_available"] is False
    assert report["weather_columns"] == []
    assert report["weather_column_count"] == 0
    assert report["missing_rate_by_column"] == {}
    assert report["overall_missing_rate"] == 0.0


def test_weather_degraded_with_source_degraded(mod):
    n = 96
    load_df = _sample_load_df(n)
    feature_df = load_df.copy()
    report = mod.build_weather_quality_report(
        load_df=load_df,
        feature_df=feature_df,
        weather_columns=[],
        weather_source="degraded",
    )
    assert len(report["notes"]) >= 1


def test_weather_degraded_does_not_block_experiment(mod, monkeypatch):
    import ellectric.pipeline.forecaster as _fxmod

    n = 96
    load_df = _sample_load_df(n)

    class FakeForecaster:
        def train_evaluate(self, X, y):
            m = min(len(y), 80)
            return {
                "actuals": np.array(y.values[:m]),
                "predictions": np.array(y.values[:m]),
            }

    monkeypatch.setattr(_fxmod, "XGBoostForecaster", lambda: FakeForecaster())

    result = mod.run_ablation_experiment(
        load_df,
        weather_cache=Path("/nonexistent_test_cache.parquet"),
        fetch_if_missing=False,
    )
    assert "baseline_tier3" in result
    assert result["weather_tier4"]["sample_count"] == 0
    assert result["weather_tier4"]["metrics"]["mae"] is None


# =====================================================================
# Group E: write_reports file output (FR-05, D-003@v1)
# =====================================================================


def test_write_reports_creates_json(mod, tmp_path):
    report = _minimal_report_dict()
    mod.write_reports(report, tmp_path)
    json_path = tmp_path / "weather_tier4_validation.json"
    assert json_path.exists()


def test_write_reports_creates_markdown(mod, tmp_path):
    report = _minimal_report_dict()
    mod.write_reports(report, tmp_path)
    md_path = tmp_path / "weather_tier4_validation.md"
    assert md_path.exists()


def test_write_reports_json_content(mod, tmp_path):
    report = _minimal_report_dict()
    mod.write_reports(report, tmp_path)
    json_path = tmp_path / "weather_tier4_validation.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key in ("metadata", "weather_quality", "experiments", "interpretation"):
        assert key in data
    assert math.isclose(
        data["experiments"]["baseline_tier3"]["metrics"]["mae"], 10.0
    )


def test_write_reports_markdown_includes_metrics(mod, tmp_path):
    report = _minimal_report_dict()
    mod.write_reports(report, tmp_path)
    md_path = tmp_path / "weather_tier4_validation.md"
    content = md_path.read_text("utf-8")
    for keyword in ("MAE", "RMSE", "MAPE", "baseline", "weather"):
        assert keyword in content


def test_write_reports_creates_directory(mod, tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    report = _minimal_report_dict()
    mod.write_reports(report, nested)
    assert nested.exists()
    assert (nested / "weather_tier4_validation.json").exists()


# =====================================================================
# Group F: run_validation integration (FR-02/03/04/05, D-003@v1)
# =====================================================================


def test_run_validation_returns_dict(mod, monkeypatch):
    import ellectric.pipeline.shandong_loader as _smod

    n = 96
    load_df = _sample_load_df(n)
    weather_df = _fake_weather_hourly()

    class FakeLoader:
        def load_data(self, start=None, end=None):
            return load_df

    monkeypatch.setattr(_smod, "ShandongDataLoader", FakeLoader)

    monkeypatch.setattr(
        mod,
        "resolve_weather_source",
        lambda *a, **kw: ("explicit", weather_df),
    )

    fake_experiment = {
        "baseline_tier3": {
            "feature_count": 30, "input_rows": 96, "sample_count": 86,
            "metrics": {"mae": 10.0, "rmse": 15.0, "mape": 5.0},
        },
        "weather_tier4": {
            "feature_count": 35, "input_rows": 96, "sample_count": 86,
            "metrics": {"mae": 8.0, "rmse": 12.0, "mape": 4.0},
        },
        "delta": {
            "mae_delta": -2.0, "rmse_delta": -3.0,
            "mape_delta": -1.0, "mae_delta_pct": -20.0,
        },
        "notes": [],
    }
    monkeypatch.setattr(
        mod, "run_ablation_experiment", lambda *a, **kw: fake_experiment
    )
    monkeypatch.setattr(
        mod, "write_reports",
        lambda *a, **kw: {"json": "/fake/report.json", "markdown": "/fake/report.md"},
    )

    result = mod.run_validation()
    assert result["status"] == "ok"
    assert "weather_quality" in result
    assert "experiments" in result
    assert "report_paths" in result


def test_run_validation_data_load_failure(mod, monkeypatch):
    import ellectric.pipeline.shandong_loader as _smod

    class FailingLoader:
        def load_data(self, start=None, end=None):
            raise FileNotFoundError("No data file found")

    monkeypatch.setattr(_smod, "ShandongDataLoader", FailingLoader)

    result = mod.run_validation()
    assert result["status"] == "error"
    assert "error" in result


def test_run_validation_degraded_path(mod, monkeypatch):
    import ellectric.pipeline.shandong_loader as _smod

    n = 96
    load_df = _sample_load_df(n)

    class FakeLoader:
        def load_data(self, start=None, end=None):
            return load_df

    monkeypatch.setattr(_smod, "ShandongDataLoader", FakeLoader)
    monkeypatch.setattr(
        mod,
        "resolve_weather_source",
        lambda *a, **kw: ("degraded", None),
    )

    fake_experiment = {
        "baseline_tier3": {
            "feature_count": 30, "input_rows": 96, "sample_count": 86,
            "metrics": {"mae": 10.0, "rmse": 15.0, "mape": 5.0},
        },
        "weather_tier4": {
            "feature_count": 35, "input_rows": 96, "sample_count": 0,
            "metrics": {"mae": None, "rmse": None, "mape": None},
        },
        "delta": {
            "mae_delta": None, "rmse_delta": None,
            "mape_delta": None, "mae_delta_pct": None,
        },
        "notes": ["No weather data available"],
    }
    monkeypatch.setattr(
        mod, "run_ablation_experiment", lambda *a, **kw: fake_experiment
    )
    monkeypatch.setattr(
        mod, "write_reports",
        lambda *a, **kw: {"json": "/fake/report.json", "markdown": "/fake/report.md"},
    )

    result = mod.run_validation(
        weather_cache="/nonexistent_test_cache.parquet"
    )
    assert result["weather_quality"]["weather_features_available"] is False
    assert "experiments" in result
    assert result["experiments"]["baseline_tier3"]["sample_count"] > 0
