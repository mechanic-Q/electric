"""
Wind/Solar 预测器单元测试（骨架）。
"""

import pandas as pd
import numpy as np

from ellectric.pipeline.renewable_forecaster import (
    WindPowerForecaster,
    SolarPowerForecaster,
    _compute_metrics,
)


def _fake_renewable_df(n=480):
    np.random.seed(42)
    t = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"timestamp": t})
    df["hour"] = t.hour
    df["day_of_week"] = t.dayofweek
    df["month"] = t.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    # Synthetically correlated features
    df["temp_jinan"] = 20 + 10 * np.sin(2 * np.pi * df["hour"] / 24) + np.random.randn(n) * 2
    df["wind_speed_jinan"] = 5 + 3 * np.sin(2 * np.pi * df["hour"] / 24 + 1) + np.random.randn(n) * 1
    df["ghi_jinan"] = np.maximum(0, 800 * np.sin(np.pi * (df["hour"] - 6) / 12))
    df["humidity_jinan"] = 60 + np.random.randn(n) * 10
    df["cloud_jinan"] = np.random.uniform(0, 100, n)

    df["wind_actual_mw"] = (
        2000 + 500 * np.sin(2 * np.pi * df["hour"] / 24)
        + 300 * (df["wind_speed_jinan"] / 5)
        + np.random.randn(n) * 100
    )
    df["wind_forecast_mw"] = df["wind_actual_mw"] + np.random.randn(n) * 200
    df["solar_actual_mw"] = np.maximum(
        0, 500 * np.sin(np.pi * (df["hour"] - 6) / 12) + np.random.randn(n) * 50
    )
    df["solar_forecast_mw"] = df["solar_actual_mw"] + np.random.randn(n) * 80
    return df


def test_wind_forecaster_train_evaluate():
    df = _fake_renewable_df()
    f = WindPowerForecaster()
    feature_cols = [
        "hour", "day_of_week", "month", "is_weekend",
        "temp_jinan", "wind_speed_jinan", "ghi_jinan",
        "humidity_jinan", "cloud_jinan",
    ]
    X = df[feature_cols]
    y = df["wind_actual_mw"]
    result = f.train_evaluate(X, y, n_splits=2)
    assert "predictions" in result
    assert "actuals" in result
    assert "metrics" in result
    m = result["metrics"]
    assert "mae" in m
    assert "rmse" in m
    assert "nrmse" in m
    assert 0 < m["mae"] < 300


def test_solar_forecaster_train_evaluate():
    df = _fake_renewable_df()
    f = SolarPowerForecaster()
    feature_cols = [
        "hour", "day_of_week", "month", "is_weekend",
        "temp_jinan", "wind_speed_jinan", "ghi_jinan",
        "humidity_jinan", "cloud_jinan",
    ]
    X = df[feature_cols]
    y = df["solar_actual_mw"]
    result = f.train_evaluate(X, y, n_splits=2)
    assert "metrics" in result
    m = result["metrics"]
    assert 0 < m["mae"] < 300


def test_predict_after_train():
    df = _fake_renewable_df()
    f = WindPowerForecaster()
    feature_cols = [c for c in df.columns if c not in ("timestamp", "wind_actual_mw", "wind_forecast_mw", "solar_actual_mw", "solar_forecast_mw")]
    X = df[feature_cols].iloc[:400]
    y = df["wind_actual_mw"].iloc[:400]
    f.train_evaluate(X, y, n_splits=2)
    X_new = df[feature_cols].iloc[400:]
    preds = f.predict(X_new)
    assert len(preds) == len(X_new)
    assert np.all(np.isfinite(preds))


def test_compute_metrics():
    actuals = np.array([100.0, 200.0, 300.0])
    preds = np.array([110.0, 190.0, 310.0])
    m = _compute_metrics(actuals, preds)
    assert "mae" in m
    assert "rmse" in m
    assert "nrmse" in m
    assert m["nrmse"] is not None
    assert 0 < m["mae"] < 50


def test_nrmse_zero_denom():
    actuals = np.ones(10) * 100.0
    preds = np.ones(10) * 100.0
    m = _compute_metrics(actuals, preds)
    assert m["nrmse"] is None
