"""
15min 时间分辨率迁移验证。

验证 TimeConfig 全域配置、pipeline 频率对齐、
特征窗口、TradingEnv shape 均按 15min 语义工作。
"""

from datetime import date
import inspect

import pandas as pd
import numpy as np

from ellectric.config import TimeConfig
from ellectric.pipeline.cleaner import standardize_frequency
from ellectric.pipeline.features import FeatureEngineer
from ellectric.pipeline.forecaster import persistence_forecast


def _sample_load_df(n: int) -> pd.DataFrame:
    ts = pd.date_range(pd.Timestamp("2026-01-01", tz="UTC"), periods=n, freq="15min")
    return pd.DataFrame({"timestamp": ts, "load_mw": np.arange(n, dtype=float)})


def test_timeconfig_defaults_smd_min():
    assert TimeConfig.points_per_day == 96
    assert TimeConfig.points_per_week == 672
    assert TimeConfig.freq == "15min"


def test_standardize_frequency_preserves_smd_min():
    df = _sample_load_df(200)
    result = standardize_frequency(df)
    assert len(result) == 200
    assert result["load_mw"].isna().sum() == 0


def test_lag_features_use_timeconfig():
    df = _sample_load_df(TimeConfig.points_per_week + 10)
    eng = FeatureEngineer()
    df1 = eng.add_tier1_features(df)
    df2 = eng.add_tier2_features(df1)
    assert df1["lag_24h"].iloc[TimeConfig.points_per_day] == df["load_mw"].iloc[0]
    assert df2["lag_168h"].iloc[TimeConfig.points_per_week] == df["load_mw"].iloc[0]


def test_rolling_features_use_smd_min_window():
    df = _sample_load_df(200)
    eng = FeatureEngineer()
    df3 = eng.add_tier1_features(df)
    df3 = eng.add_tier2_features(df3)
    df3 = eng.add_tier3_features(df3)
    expected_mean = df["load_mw"].iloc[0:TimeConfig.points_per_day].mean()
    assert df3["rolling_mean_24h"].iloc[TimeConfig.points_per_day - 1] == expected_mean
    assert "rolling_std_24h" in df3.columns


def test_forecaster_defaults_use_timeconfig_gap():
    from ellectric.pipeline.forecaster import XGBoostForecaster
    from ellectric.pipeline.price_forecaster import LEARForecaster

    xgb_gap = inspect.signature(XGBoostForecaster.train_evaluate).parameters["gap"].default
    lear_gap = inspect.signature(LEARForecaster.train_evaluate).parameters["gap"].default
    assert xgb_gap == TimeConfig.points_per_day
    assert lear_gap == TimeConfig.points_per_day


def test_trading_env_action_shape_and_error_message():
    try:
        from ellectric.pipeline.trading_env import ElectricityMarketEnv
    except ImportError:
        import pytest
        pytest.skip("gymnasium not installed")
    n = 200
    ts = pd.date_range(pd.Timestamp("2026-01-01", tz="UTC"), periods=n, freq="15min")
    load_df = pd.DataFrame({"timestamp": ts, "load_mw": np.ones(n) * 500.0})
    price_df = pd.DataFrame({"timestamp": ts, "price_da": np.ones(n) * 300.0})
    env = ElectricityMarketEnv(load_df, price_df)
    assert env.action_space.shape == (TimeConfig.points_per_day,)
    assert env.observation_space["load_forecast_24h"].shape == (TimeConfig.points_per_day,)
    assert env.observation_space["price_history_168h"].shape == (TimeConfig.points_per_week,)
    env.reset()
    try:
        env.step(np.zeros(24, dtype=np.float32))
    except ValueError as exc:
        assert str(TimeConfig.points_per_day) in str(exc)
    else:
        raise AssertionError("wrong action shape should raise ValueError")


def test_persistence_uses_timeconfig():
    df = _sample_load_df(200)
    fcst = persistence_forecast(df)
    assert len(fcst) == len(df)
    assert fcst.iloc[TimeConfig.points_per_day] == df["load_mw"].iloc[0]


def test_data_source_defaults_shandong():
    from ellectric.service.schemas import BacktestRequest, ExplainRequest, ForecastRequest

    forecast_req = ForecastRequest(model_type="load")
    backtest_req = BacktestRequest(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
        strategy="baseline_persistence",
    )
    explain_req = ExplainRequest(model_type="xgboost")
    assert forecast_req.data_source == "shandong"
    assert backtest_req.data_source == "shandong"
    assert explain_req.data_source == "shandong"


def test_service_horizon_hours_convert_to_15min_points():
    from ellectric.service.handlers import _horizon_to_points

    assert _horizon_to_points(24) == TimeConfig.points_per_day
    assert _horizon_to_points(168) == TimeConfig.points_per_week
    assert _horizon_to_points(1) == 4


def test_service_shandong_price_data_contract(monkeypatch):
    import ellectric.pipeline.shandong_loader as shandong_loader
    from ellectric.service.handlers import _load_price_data

    ts = pd.date_range(pd.Timestamp("2026-01-01", tz="UTC"), periods=2, freq="15min")

    class FakeLoader:
        def load_data(self):
            return pd.DataFrame(
                {
                    "timestamp": ts,
                    "load_mw": [1.0, 2.0],
                    "rt_price": [300.0, 310.0],
                    "da_price": [np.nan, 305.0],
                    "wind_actual_mw": [10.0, 11.0],
                    "solar_actual_mw": [20.0, 21.0],
                    "tie_line_actual_mw": [30.0, 31.0],
                }
            )

    monkeypatch.setattr(shandong_loader, "ShandongDataLoader", FakeLoader)
    df = _load_price_data("shandong")
    assert list(df["price_da"]) == [300.0, 305.0]
    assert "price_rt" in df.columns
    assert "wind_mw" in df.columns
    assert "solar_mw" in df.columns


def test_backtester_baseline_actions_use_timeconfig():
    try:
        from ellectric.pipeline.backtester import baseline_mean, baseline_persistence, oracle_strategy
    except ImportError:
        import pytest
        pytest.skip("gymnasium not installed")

    class Env:
        _max_capacity = 1000.0
        _load_data = pd.DataFrame({"load_mw": np.ones(TimeConfig.points_per_week + TimeConfig.points_per_day) * 500.0})

    env = Env()
    assert baseline_persistence(env, TimeConfig.points_per_day).shape == (TimeConfig.points_per_day,)
    assert baseline_mean(env, TimeConfig.points_per_week).shape == (TimeConfig.points_per_day,)
    assert oracle_strategy(env, 0).shape == (TimeConfig.points_per_day,)


def test_shandong_loader_outputs_15min_contract(tmp_path):
    from ellectric.pipeline.shandong_loader import ShandongDataLoader

    data_path = tmp_path / "shandong.csv"
    pd.DataFrame(
        {
            "日期": ["2024-01-01", "2024-01-01"],
            "时刻": ["23:45", "24:00"],
            "是否节假日": ["否", "是"],
            "是否周末休息日": ["否", "否"],
            "直调负荷(实际)": [500.0, 510.0],
            "实时价格": [300.0, 310.0],
            "日前价格": [290.0, 295.0],
            "风电总加(实际)": [10.0, 11.0],
            "光伏总加(实际)": [20.0, 21.0],
            "非市场化核电总加(实际)": [30.0, 31.0],
            "自备机组总加(实际)": [40.0, 41.0],
            "联络线受电负荷(实际)": [50.0, 51.0],
            "抽蓄(实际)": [60.0, 61.0],
            "地方电厂发电总加(实际)": [70.0, 71.0],
        }
    ).to_csv(data_path, index=False, encoding="utf-8-sig")

    df = ShandongDataLoader(data_path=str(data_path)).load_data()
    assert {"timestamp", "load_mw", "rt_price", "da_price", "province", "source", "granularity"}.issubset(df.columns)
    assert df["granularity"].eq("15min").all()
    assert df["province"].eq("shandong").all()
    assert str(df["timestamp"].dt.tz) == "UTC"
    assert df["timestamp"].iloc[1] == pd.Timestamp("2024-01-02 00:00", tz="UTC")


def test_public_api_names_preserved():
    from ellectric.config import TimeConfig
    from ellectric.pipeline.cleaner import clean_data, standardize_frequency
    from ellectric.pipeline.features import FeatureEngineer
    from ellectric.pipeline.forecaster import XGBoostForecaster
    from ellectric.pipeline.shandong_loader import ShandongDataLoader
    from ellectric.service.schemas import ForecastRequest, ForecastResponse

    assert TimeConfig.points_per_day == 96
    assert callable(clean_data)
    assert callable(standardize_frequency)
    assert FeatureEngineer is not None
    assert XGBoostForecaster is not None
    assert ShandongDataLoader is not None
    assert ForecastRequest is not None
    assert ForecastResponse is not None
