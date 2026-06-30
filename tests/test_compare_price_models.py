import numpy as np
import pandas as pd
import pytest

from ellectric.config import TimeConfig
from ellectric.scripts.compare_price_models import (
    ComparisonResult,
    _rename_for_lear,
    prepare_data,
    create_folds,
    parse_args,
    compute_metrics,
    train_and_evaluate_persistence,
    train_and_evaluate_weekly_avg,
    run_dm_gw_pairwise,
    _pairwise_dm,
    _pairwise_gw,
)


# ── Helpers ─────────────────────────────────────────────

def _fake_price_df(n=480) -> pd.DataFrame:
    np.random.seed(42)
    t = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"timestamp": t})
    hour = t.hour
    df["hour"] = hour
    df["day_of_week"] = t.dayofweek
    df["month"] = t.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["lag_24h_price"] = (300 + 50 * np.sin(2 * np.pi * hour / 24) + np.random.randn(n) * 20).tolist()
    df["lag_168h_price"] = pd.Series(df["lag_24h_price"]).shift(1).fillna(300).tolist()
    df["rolling_mean_24h_price"] = pd.Series(df["lag_24h_price"]).rolling(96, min_periods=1).mean().tolist()
    df["rolling_std_24h_price"] = pd.Series(df["lag_24h_price"]).rolling(96, min_periods=1).std().fillna(10).tolist()
    price = 300 + 50 * np.sin(2 * np.pi * hour / 24) + np.random.randn(n) * 30
    df["price_da"] = np.maximum(price, 0)
    df["da_price"] = df["price_da"]
    df["load_mw"] = 5000 + 500 * np.sin(2 * np.pi * hour / 24)
    df["wind_mw"] = 1000 + 200 * np.random.randn(n)
    df["solar_mw"] = np.maximum(2000 * (1 - abs(hour - 12) / 12), 0) + 100 * np.random.randn(n)
    return df


# ── Test ComparisonResult schema ───────────────────────

def test_comparison_result_schema():
    meta = {"dataset": "shandong", "tier": "tier3"}
    r = ComparisonResult(metadata=meta)
    meta_out = r.metadata
    assert meta_out["dataset"] == "shandong"
    assert r.models == {}
    assert r.metrics == {}
    assert r.statistical_tests == {}
    assert r.artifacts == {}
    assert r.notes == []


# ── Test _rename_for_lear ──────────────────────────────

def test_rename_for_lear():
    df = pd.DataFrame({"da_price": [1], "wind_actual_mw": [2], "solar_actual_mw": [3], "load_mw": [4]})
    renamed = _rename_for_lear(df)
    assert "price_da" in renamed.columns
    assert "wind_mw" in renamed.columns
    assert "solar_mw" in renamed.columns
    assert "load_mw" in renamed.columns


# ── Test prepare_data ─────────────────────────────────

def test_prepare_data():
    df = _fake_price_df(1000)
    X, y, df_feat, forecaster = prepare_data(df, tier="tier1")
    assert X.shape[0] > 0
    assert len(X) == len(y)
    assert all(c in X.columns for c in ["hour", "day_of_week", "month", "is_weekend", "lag_24h_price", "lag_168h_price"])


def test_prepare_data_missing_price_da():
    df = _fake_price_df(100).drop(columns=["price_da"])
    with pytest.raises(ValueError, match="Missing required columns"):
        prepare_data(df)


# ── Test create_folds ──────────────────────────────────

def test_create_folds():
    df = _fake_price_df(2000)
    X, y, df_feat, _ = prepare_data(df, tier="tier1")
    folds = list(create_folds(X, y, n_splits=3))
    assert len(folds) == 3
    for Xtr, Xte, ytr, yte in folds:
        assert len(Xtr) > 0
        assert len(Xte) > 0
        assert len(Xtr) == len(ytr)
        assert len(Xte) == len(yte)


def test_create_folds_insufficient_data():
    X_small = pd.DataFrame({"a": range(10)})
    y_small = pd.Series(range(10))
    with pytest.raises(ValueError, match="Not enough rows"):
        list(create_folds(X_small, y_small, n_splits=5))


# ── Test compute_metrics ───────────────────────────────

def test_compute_metrics():
    actuals = np.array([100.0, 200.0, 300.0])
    preds = np.array([110.0, 190.0, 310.0])
    m = compute_metrics(actuals, preds)
    assert "mae" in m and "rmse" in m and "mape" in m
    assert 0 < m["mae"] < 50
    assert m["mape"] is not None


def test_compute_metrics_zero_mask():
    actuals = np.array([0.0, 200.0, 0.0])
    preds = np.array([10.0, 190.0, 10.0])
    m = compute_metrics(actuals, preds)
    assert m["mape"] is not None
    assert m["mape"] > 0


# ── Test baselines ────────────────────────────────────

def test_persistence_baseline():
    df = _fake_price_df(2000)
    result = train_and_evaluate_persistence(df)
    assert "predictions" in result
    assert "actuals" in result
    assert "metrics" in result
    assert result["model"] is None
    assert np.isfinite(result["metrics"]["mae"])


def test_weekly_avg_baseline():
    df = _fake_price_df(3000)
    result = train_and_evaluate_weekly_avg(df)
    assert "predictions" in result
    assert "actuals" in result
    assert "metrics" in result
    assert result["model"] is None
    assert np.isfinite(result["metrics"]["mae"])


def test_baselines_ignore_nan_price_rows():
    df = _fake_price_df(3000)
    df.loc[df.index[100:1800], "price_da"] = np.nan
    persistence = train_and_evaluate_persistence(df)
    weekly = train_and_evaluate_weekly_avg(df)
    assert np.isfinite(persistence["metrics"]["mae"])
    assert np.isfinite(weekly["metrics"]["mae"])


# ── Test DM/GW ─────────────────────────────────────────

def test_pairwise_dm_basic():
    e1 = np.random.randn(200)
    e2 = np.random.randn(200)
    result = _pairwise_dm(e1, e2, h=24, crit="MAE")
    assert "dm_stat" in result
    assert "p_value" in result
    assert "significant" in result
    assert result["skip_reason"] is None or "MOCK" in result["skip_reason"]


def test_pairwise_gw_basic():
    e1 = np.random.randn(200)
    e2 = np.random.randn(200)
    result = _pairwise_gw(e1, e2, h=24, crit="MAE")
    assert "gw_stat" in result
    assert "p_value" in result
    assert "significant" in result


def test_pairwise_dm_short_series():
    e1 = np.random.randn(5)
    e2 = np.random.randn(5)
    result = _pairwise_dm(e1, e2, h=24, crit="MAE")
    assert result["skip_reason"] is not None


def test_run_dm_gw_pairwise():
    rng = np.random.RandomState(42)
    model_results = {
        "lear": {"predictions": rng.randn(200), "actuals": rng.randn(200)},
        "dnn": {"predictions": rng.randn(200), "actuals": rng.randn(200)},
        "persistence": {"predictions": rng.randn(200), "actuals": rng.randn(200)},
    }
    result = run_dm_gw_pairwise(model_results, h=24, crit="MAE")
    assert "pairwise_results" in result
    assert "summary" in result
    assert len(result["pairwise_results"]) >= 2


def test_run_dm_gw_pairwise_filters_nan_pairs():
    rng = np.random.RandomState(42)
    actuals = rng.randn(200)
    predictions = rng.randn(200)
    actuals[::5] = np.nan
    predictions[::7] = np.nan
    model_results = {
        "lear": {"predictions": predictions, "actuals": actuals},
        "dnn": {"predictions": rng.randn(200), "actuals": rng.randn(200)},
    }
    result = run_dm_gw_pairwise(model_results, h=24, crit="MAE")
    assert result["pairwise_results"][0]["dm"]["skip_reason"] is None or "MOCK" in result["pairwise_results"][0]["dm"]["skip_reason"]


# ── Test CLI args ──────────────────────────────────────

def test_parse_args_dry_run():
    args = parse_args(["--dry-run"])
    assert args.dry_run is True
    assert args.dataset == "shandong"
    assert args.tier == "tier3"


def test_parse_args_custom():
    args = parse_args(["--tier", "tier2", "--start", "2024-06", "--end", "2024-08"])
    assert args.tier == "tier2"
    assert args.start == "2024-06"
    assert args.end == "2024-08"
    assert args.dry_run is False
