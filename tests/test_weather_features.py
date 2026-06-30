# ---
# author: lmr
# created_at: 2026-06-27 19:12:11
# ---

"""
Weather feature Tier4 契约测试。

验证 add_tier4_weather_features / get_feature_columns("tier4") /
prepare_features(tiers=[..., "tier4"]) 的接口签名和语义约束。

覆盖: FR-001, FR-002, FR-003, FR-004, D-006@v2, D-007@v2
"""

import logging

import pandas as pd
import numpy as np

from ellectric.pipeline.features import FeatureEngineer, prepare_features


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


# ── Group A: Tier4 explicit weather_df merge (FR-001, FR-003) ──


def test_add_tier4_weather_df_only():
    """weather_df 显式传入时，返回 DataFrame 包含天气列。"""
    df = _sample_load_df(96)
    weather_df = _fake_weather_hourly()
    eng = FeatureEngineer()
    result = eng.add_tier4_weather_features(df, weather_df=weather_df)
    assert "temp_jinan" in result.columns


def test_add_tier4_preserves_tier1_tier2_tier3():
    """Tier4 不破坏已存在的 Tier1-3 特征。"""
    df = _sample_load_df(200)
    weather_df = _fake_weather_hourly()
    eng = FeatureEngineer()
    df = eng.add_tier1_features(df)
    df = eng.add_tier2_features(df)
    df = eng.add_tier3_features(df)
    tier3_cols = set(df.columns)
    result = eng.add_tier4_weather_features(df, weather_df=weather_df)
    assert tier3_cols.issubset(result.columns)


def test_add_tier4_handles_timestamp_index():
    """weather_df 的 index 为 timestamp（兼容 fetch_historical() 输出格式）。"""
    df = _sample_load_df(96)
    weather_df = _fake_weather_hourly()
    assert isinstance(weather_df.index, pd.DatetimeIndex)
    eng = FeatureEngineer()
    result = eng.add_tier4_weather_features(df, weather_df=weather_df)
    assert "temp_jinan" in result.columns


def test_add_tier4_no_weather_df_warns(caplog, tmp_path):
    """weather_df 与 cache 均未提供时记录 warning 而非抛异常。"""
    df = _sample_load_df(96)
    eng = FeatureEngineer()
    with caplog.at_level(logging.WARNING):
        result = eng.add_tier4_weather_features(
            df, weather_df=None, weather_cache_path=tmp_path / "missing.parquet",
            fetch_if_missing=False,
        )
    assert len(caplog.records) > 0
    assert "weather" in caplog.text.lower()
    assert list(result.columns) == list(df.columns)


# ── Group B: Cache hit/miss (FR-002, D-007@v2) ──


def test_add_tier4_cache_hit_no_network(tmp_path, monkeypatch):
    """cache parquet 存在时从文件读取，不触网。"""
    df = _sample_load_df(96)
    weather_df = _fake_weather_hourly()
    cache_path = tmp_path / "weather.parquet"
    weather_df.to_parquet(cache_path)

    from ellectric.fetch.weather import WeatherFetcher
    fetch_called = False

    def _fake_fetch(*args, **kwargs):
        nonlocal fetch_called
        fetch_called = True
        return pd.DataFrame()

    monkeypatch.setattr(WeatherFetcher, "fetch_historical", _fake_fetch)
    eng = FeatureEngineer()
    result = eng.add_tier4_weather_features(
        df, weather_cache_path=cache_path, fetch_if_missing=True
    )
    assert not fetch_called
    assert "temp_jinan" in result.columns


def test_add_tier4_cache_miss_fetch_false_degrades(caplog):
    """cache 缺失 + fetch_if_missing=False 不抛异常，返回原 df。"""
    df = _sample_load_df(96)
    eng = FeatureEngineer()
    with caplog.at_level(logging.WARNING):
        result = eng.add_tier4_weather_features(
            df, weather_cache_path="/nonexistent/cache.parquet", fetch_if_missing=False
        )
    assert list(result.columns) == list(df.columns)
    assert any("weather" in r.msg.lower() for r in caplog.records)


def test_add_tier4_cache_miss_fetch_true_calls_fetch(tmp_path, monkeypatch):
    """cache 缺失 + fetch_if_missing=True 触发 WeatherFetcher.fetch_historical() 调用。"""
    df = _sample_load_df(96)
    cache_path = tmp_path / "nonexistent.parquet"

    from ellectric.fetch.weather import WeatherFetcher
    fetch_called = False

    def _fake_fetch(*args, **kwargs):
        nonlocal fetch_called
        fetch_called = True
        return _fake_weather_hourly()

    monkeypatch.setattr(WeatherFetcher, "fetch_historical", _fake_fetch)
    eng = FeatureEngineer()
    result = eng.add_tier4_weather_features(
        df, weather_cache_path=cache_path, fetch_if_missing=True
    )
    assert fetch_called
    assert "temp_jinan" in result.columns


# ── Group C: 15min boundary alignment (FR-003, D-007@v2) ──


def test_add_tier4_ffill_covers_0045():
    """小时级 weather 数据正确填充到 00:15, 00:30, 00:45 三个子点。"""
    n = 4
    ts = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"timestamp": ts, "load_mw": np.arange(n, dtype=float)})
    weather_ts = pd.date_range("2026-01-01 00:00", periods=2, freq="h", tz="UTC")
    weather_df = pd.DataFrame({"temp_jinan": [20.0, 21.0]}, index=weather_ts)
    eng = FeatureEngineer()
    result = eng.add_tier4_weather_features(df, weather_df=weather_df)
    assert result["temp_jinan"].iloc[0] == 20.0
    assert result["temp_jinan"].iloc[3] == 20.0


# ── Group D: get_feature_columns tier4 (FR-004, D-006@v2) ──


def test_get_feature_columns_tier4_includes_weather():
    """DataFrame 有 weather columns 时 get_feature_columns("tier4") 返回包含它们。"""
    df = _sample_load_df(96)
    weather_df = _fake_weather_hourly()
    eng = FeatureEngineer()
    df = eng.add_tier1_features(df)
    df = eng.add_tier4_weather_features(df, weather_df=weather_df)
    cols = eng.get_feature_columns("tier4")
    assert "temp_jinan" in cols


def test_get_feature_columns_tier4_missing_weather_dropped():
    """DataFrame 无 weather columns 时 get_feature_columns("tier4") 只返回 Tier1-3 列。"""
    df = _sample_load_df(96)
    eng = FeatureEngineer()
    df = eng.add_tier1_features(df)
    cols = eng.get_feature_columns("tier4")
    assert "temp_jinan" not in cols
    assert "is_holiday" in cols
    assert "rolling_mean_24h" in cols


# ── Group E: prepare_features tier4 + backward compat (FR-001, FR-003, D-006@v2) ──


def test_prepare_features_tier4_default_cache():
    """prepare_features(df, tiers=[..., 'tier4']) 使用默认 cache path 工作。"""
    df = _sample_load_df(96)
    weather_df = _fake_weather_hourly()
    result = prepare_features(
        df, tiers=["tier1", "tier2", "tier3", "tier4"], weather_df=weather_df
    )
    assert "temp_jinan" in result.columns


def test_prepare_features_tier1_unchanged():
    """prepare_features(df, tiers=['tier1']) 与旧调用行为一致（不新增 weather 参数）。"""
    df = _sample_load_df(96)
    result = prepare_features(df, tiers=["tier1"])
    assert "hour" in result.columns
    assert "temp_jinan" not in result.columns
