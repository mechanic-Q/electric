import numpy as np
import pandas as pd
from ellectric.pipeline.price_forecaster_dnn import DNNPriceForecaster, _compute_metrics

def _fake_price_df(n=480):
    np.random.seed(42)
    t = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"timestamp": t})
    df["hour"] = t.hour
    df["day_of_week"] = t.dayofweek
    df["month"] = t.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["lag_24h_price"] = 300 + 50 * np.sin(2 * np.pi * df["hour"] / 24) + np.random.randn(n) * 20
    df["lag_168h_price"] = df["lag_24h_price"].shift(1).fillna(300)
    df["rolling_mean_24h_price"] = df["lag_24h_price"].rolling(96, min_periods=1).mean()
    df["rolling_std_24h_price"] = df["lag_24h_price"].rolling(96, min_periods=1).std().fillna(10)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    price = 300 + 50 * np.sin(2 * np.pi * df["hour"] / 24) + np.random.randn(n) * 30
    df["price_da"] = np.maximum(price, 0)
    return df

def test_dnn_train_evaluate():
    df = _fake_price_df()
    f = DNNPriceForecaster(input_dim=8, epochs=5)
    feature_cols = ["hour", "day_of_week", "month", "is_weekend", "lag_24h_price", "lag_168h_price", "hour_sin", "hour_cos"]
    X = df[feature_cols]
    y = df["price_da"]
    result = f.train_evaluate(X, y, n_splits=2)
    assert "predictions" in result
    assert "actuals" in result
    assert "metrics" in result
    m = result["metrics"]
    assert "mae" in m
    assert "rmse" in m
    assert 0 < m["mae"] < 500

def test_predict_after_train():
    df = _fake_price_df()
    f = DNNPriceForecaster(input_dim=8, epochs=5)
    feature_cols = ["hour", "day_of_week", "month", "is_weekend", "lag_24h_price", "lag_168h_price", "hour_sin", "hour_cos"]
    X = df[feature_cols].iloc[:400]
    y = df["price_da"].iloc[:400]
    f.train_evaluate(X, y, n_splits=2)
    X_new = df[feature_cols].iloc[400:410]
    preds = f.predict(X_new)
    assert len(preds) == 10
    assert np.all(np.isfinite(preds))

def test_compute_metrics():
    actuals = np.array([100.0, 200.0, 300.0])
    preds = np.array([110.0, 190.0, 310.0])
    m = _compute_metrics(actuals, preds)
    assert "mae" in m
    assert "rmse" in m
    assert "mape" in m
    assert 0 < m["mae"] < 50
