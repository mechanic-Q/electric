"""
投机者价差模型单元测试 — reward 可正、action bounds、scaling、baseline 策略
"""
import numpy as np
import pandas as pd
import pytest

from ellectric.config import TimeConfig
from ellectric.pipeline.trading_env import ElectricityMarketEnv
from ellectric.pipeline.backtester import baseline_mean, oracle_strategy


@pytest.fixture
def env_data_800():
    """800 行合成数据：前 672 行价格 300，后 128 行价格 500。"""
    n = 800
    timestamps = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    price = np.ones(n) * 300.0
    price[672:] = 500.0
    return pd.DataFrame({
        "timestamp": timestamps,
        "load_mw": np.ones(n) * 50000,
        "rt_price": price,
    })


@pytest.fixture
def env_data_200():
    """200 行随机数据（常规 fixture，用于 action bounds 等快速测试）。"""
    n = 200
    timestamps = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({
        "timestamp": timestamps,
        "load_mw": np.random.default_rng(42).uniform(40000, 60000, n),
        "rt_price": np.random.default_rng(42).uniform(200, 600, n),
    })


def test_action_space_has_correct_bounds(env_data_200):
    load = env_data_200[["timestamp", "load_mw"]]
    price = env_data_200[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = ElectricityMarketEnv(load, price)
    assert (env.action_space.low == -1.0).all()
    assert (env.action_space.high == 1.0).all()
    assert env.action_space.shape == (TimeConfig.points_per_day,)
    assert env.action_space.dtype == np.float32


def test_reward_can_be_positive(env_data_800):
    """8 天数据，前 7 天价格 300，第 8 天价格 500。全部做多应盈利。"""
    load = env_data_800[["timestamp", "load_mw"]]
    price = env_data_800[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = ElectricityMarketEnv(load, price)
    env.reset()

    for _ in range(7):
        obs, _, terminated, _, info = env.step(np.ones(TimeConfig.points_per_day))
        if terminated:
            return

    baseline_mean = info.get("baseline_price", 0)
    assert baseline_mean < 500, f"baseline {baseline_mean:.0f} 应低于第 8 天价格 500"

    obs, reward, terminated, truncated, info = env.step(np.ones(TimeConfig.points_per_day))
    assert reward > 0, f"reward={reward:.2f} 应为正（做多时价格高于 baseline）"


def test_short_also_profitable(env_data_800):
    """价格突然下跌时，做空应有正 reward。"""
    n = 800
    timestamps = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    price = np.ones(n) * 500.0
    price[672:] = 300.0
    df = pd.DataFrame({
        "timestamp": timestamps,
        "load_mw": np.ones(n) * 50000,
        "rt_price": price,
    })
    load = df[["timestamp", "load_mw"]]
    price = df[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = ElectricityMarketEnv(load, price)
    env.reset()

    for _ in range(7):
        obs, _, terminated, _, info = env.step(np.ones(TimeConfig.points_per_day))
        if terminated:
            return

    obs, reward, terminated, truncated, info = env.step(-np.ones(TimeConfig.points_per_day))
    assert reward > 0, f"reward={reward:.2f} 应为正（做空时价格低于 baseline）"


def test_reward_scaling_applied(env_data_200):
    """验证 reward 被缩放（不是原始 P&L 的百万量级）。"""
    load = env_data_200[["timestamp", "load_mw"]]
    price = env_data_200[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = ElectricityMarketEnv(load, price)

    assert env._reward_scale > 0, f"_reward_scale 应为正，实际 {env._reward_scale}"
    env.reset()
    obs, reward, _, _, info = env.step(np.ones(TimeConfig.points_per_day))
    assert abs(reward) < 1e6, f"scaled reward={reward:.2f} 不应为百万量级"
    assert abs(reward) < 1e4, f"scaled reward={reward:.2f} 应在 O(10-100) 而非 O(1000+)"
    assert not np.isnan(reward), "reward 不应为 NaN"


def test_flat_strategy_zeros(env_data_200):
    """baseline_mean 应返回全零向量。"""
    load = env_data_200[["timestamp", "load_mw"]]
    price = env_data_200[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = ElectricityMarketEnv(load, price)
    action = baseline_mean(env, 0)
    assert action.shape == (TimeConfig.points_per_day,)
    assert (action == 0).all()


def test_oracle_returns_directional(env_data_200):
    """oracle 根据 price vs baseline 返回方向性信号。"""
    load = env_data_200[["timestamp", "load_mw"]]
    price = env_data_200[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = ElectricityMarketEnv(load, price)
    action = oracle_strategy(env, 0)
    assert action.shape == (TimeConfig.points_per_day,)
    assert set(np.unique(action)).issubset({-1.0, 1.0}), f"oracle 应仅返回 ±1，实际 {np.unique(action)}"
