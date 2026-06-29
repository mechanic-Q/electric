"""
完整 96 维 RL full dataset 训练 — 单元测试

测试约定（D-007@v1）：
- 所有测试通过 monkeypatch 注入 fake BaseRLAgent adapter
- 不调用真实 stable_baselines3 PPO/SAC/TD3 .learn()
- 不依赖网络、不依赖真实 weather cache
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ellectric.pipeline.rl_trainer import BaseRLAgent


class FakeRLAgent(BaseRLAgent):
    def __init__(self, algo="ppo", fail_on_train=False):
        self._algo = algo
        self._fail_on_train = fail_on_train
        self._trained = False

    def train(self, total_timesteps=50000, callback=None):
        if self._fail_on_train:
            raise RuntimeError(f"FakeRLAgent forced failure for {self._algo}")
        self._trained = True
        return {"total_timesteps": total_timesteps, "final_reward": -100.0, "algo": self._algo}

    def predict(self, observation, deterministic=True):
        if not self._trained:
            raise RuntimeError("模型未训练，请先调用 train()")
        return np.zeros(96, dtype=np.float32)

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("fake checkpoint")

    def load(self, path, env=None):
        return

    def evaluate(self, env, n_episodes=100):
        return {"mean_reward": -50.0, "std_reward": 10.0, "episode_rewards": [-50.0] * n_episodes}


@pytest.fixture
def fake_agent_factory(monkeypatch):
    from ellectric.pipeline import rl_trainer

    def fake_create(algo, env, tensorboard_log="./tb_logs", policy_kwargs=None, verbose=0, **kwargs):
        return FakeRLAgent(algo=algo)

    def fake_load(algo, path, env=None):
        return FakeRLAgent(algo=algo)

    monkeypatch.setattr(rl_trainer.RLAgentFactory, "create", fake_create)
    monkeypatch.setattr(rl_trainer.RLAgentFactory, "load", fake_load)
    return monkeypatch


@pytest.fixture
def tiny_shandong_df():
    n = 200
    timestamps = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({
        "timestamp": timestamps,
        "load_mw": np.random.uniform(40000, 60000, n),
        "rt_price": np.random.uniform(200, 600, n),
        "da_price": np.random.uniform(200, 600, n),
        "wind_actual_mw": np.random.uniform(2000, 8000, n),
        "solar_actual_mw": np.random.uniform(0, 5000, n),
        "is_holiday": np.zeros(n, dtype=int),
        "is_weekend": (pd.Series(timestamps).dt.dayofweek >= 5).astype(int),
    })


def test_module_importable():
    from ellectric.scripts import train_rl_full_dataset
    assert train_rl_full_dataset.PRICE_PROXY == "rt_price->price_da"


def test_fake_rl_agent_is_base_rl_agent():
    fake = FakeRLAgent()
    assert isinstance(fake, BaseRLAgent)


def test_fake_rl_agent_train_returns_dict():
    fake = FakeRLAgent()
    result = fake.train(100)
    assert isinstance(result, dict)
    assert "final_reward" in result


def test_fake_rl_agent_predict_returns_96d():
    fake = FakeRLAgent()
    fake.train(100)
    action = fake.predict({"obs": np.zeros(96)})
    assert action.shape == (96,)


def test_fake_rl_agent_save_creates_file(tmp_path):
    fake = FakeRLAgent()
    p = tmp_path / "dummy.zip"
    fake.save(str(p))
    assert p.exists()


def test_fake_rl_agent_evaluate_returns_dict():
    fake = FakeRLAgent()
    result = fake.evaluate(None, n_episodes=5)
    assert result["mean_reward"] == -50.0


def test_fake_rl_agent_fail_on_train():
    fake = FakeRLAgent(fail_on_train=True)
    with pytest.raises(RuntimeError):
        fake.train(100)


def test_build_datasets_price_proxy(tiny_shandong_df, monkeypatch):
    from ellectric.scripts.train_rl_full_dataset import build_datasets
    monkeypatch.setattr("ellectric.pipeline.data_loader.create_loader",
                        lambda *a, **kw: _MockLoader(tiny_shandong_df))
    train_l, train_p, test_l, test_p = build_datasets(
        "2024-01-01", "2024-01-01T01:00:00", "2024-01-01T01:00:00", "2024-01-01T02:00:00",
    )
    assert "price_da" in train_p.columns
    assert "price_da" in test_p.columns
    assert train_p["price_da"].notna().all()
    assert test_p["price_da"].notna().all()


def test_build_datasets_split_disjoint(tiny_shandong_df, monkeypatch):
    from ellectric.scripts.train_rl_full_dataset import build_datasets
    monkeypatch.setattr("ellectric.pipeline.data_loader.create_loader",
                        lambda *a, **kw: _MockLoader(tiny_shandong_df))
    train_l, train_p, test_l, test_p = build_datasets(
        "2024-01-01", "2024-01-01T01:00:00", "2024-01-01T01:00:00", "2024-01-01T02:00:00",
    )
    assert len(train_l) > 0
    assert len(test_l) > 0
    assert train_p["timestamp"].max() <= test_p["timestamp"].min()


def test_build_datasets_null_filled(tiny_shandong_df, monkeypatch):
    tiny_shandong_df.loc[0:5, "rt_price"] = np.nan
    from ellectric.scripts.train_rl_full_dataset import build_datasets
    monkeypatch.setattr("ellectric.pipeline.data_loader.create_loader",
                        lambda *a, **kw: _MockLoader(tiny_shandong_df))
    train_l, train_p, test_l, test_p = build_datasets(
        "2024-01-01", "2024-01-01T01:00:00", "2024-01-01T01:00:00", "2024-01-01T02:00:00",
    )
    assert train_p["price_da"].isna().sum() == 0
    assert test_p["price_da"].isna().sum() == 0


def test_make_env_reward_fn(tiny_shandong_df, monkeypatch):
    from ellectric.scripts.train_rl_full_dataset import make_env
    monkeypatch.setattr("ellectric.pipeline.trading_env.ElectricityMarketEnv", _FakeEnv)
    load_df = tiny_shandong_df[["timestamp", "load_mw"]]
    price_df = tiny_shandong_df[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = make_env(load_df, price_df)
    assert hasattr(env, "_reward_fn_name")
    assert env._reward_fn_name == "profit_only"


def test_make_env_action_space(tiny_shandong_df, monkeypatch):
    from ellectric.scripts.train_rl_full_dataset import make_env
    monkeypatch.setattr("ellectric.pipeline.trading_env.ElectricityMarketEnv", _FakeEnv)
    load_df = tiny_shandong_df[["timestamp", "load_mw"]]
    price_df = tiny_shandong_df[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    env = make_env(load_df, price_df)
    assert env._max_capacity is not None


def test_train_one_success_with_fake(tiny_shandong_df, fake_agent_factory, tmp_path):
    from ellectric.scripts.train_rl_full_dataset import train_one
    env = _make_dummy_env(tiny_shandong_df)
    ckpt = str(tmp_path / "ppo.zip")
    result = train_one("ppo", env, timesteps=100, seed=42, log_dir=str(tmp_path / "tb"), ckpt_path=ckpt)
    assert result["status"] == "ok"


def test_train_one_failure_swallowed(tiny_shandong_df, monkeypatch, tmp_path):
    from ellectric.pipeline import rl_trainer
    def bad_create(algo, env, **kw):
        raise RuntimeError("forced failure")
    monkeypatch.setattr(rl_trainer.RLAgentFactory, "create", bad_create)
    from ellectric.scripts.train_rl_full_dataset import train_one
    env = _make_dummy_env(tiny_shandong_df)
    result = train_one("ppo", env, timesteps=100, seed=42,
                       log_dir=str(tmp_path / "tb"), ckpt_path=str(tmp_path / "ppo.zip"))
    assert result["status"] == "error"
    assert "forced failure" in result["error"]


def test_train_one_creates_dirs(tiny_shandong_df, fake_agent_factory, tmp_path):
    from ellectric.scripts.train_rl_full_dataset import train_one
    env = _make_dummy_env(tiny_shandong_df)
    ckpt_dir = tmp_path / "models" / "sub"
    tb_dir = tmp_path / "tb_logs" / "rl"
    train_one("ppo", env, timesteps=100, seed=42,
              log_dir=str(tb_dir), ckpt_path=str(ckpt_dir / "ppo.zip"))
    assert tb_dir.exists()
    assert ckpt_dir.exists()


def test_train_one_tensorboard_missing_fallback(tiny_shandong_df, monkeypatch, tmp_path):
    from ellectric.pipeline import rl_trainer
    captured = {}

    def fake_create(algo, env, tensorboard_log="./tb_logs", policy_kwargs=None, verbose=0, **kwargs):
        captured["tensorboard_log"] = tensorboard_log
        return FakeRLAgent(algo=algo)

    monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "tensorboard" else object())
    monkeypatch.setattr(rl_trainer.RLAgentFactory, "create", fake_create)
    from ellectric.scripts.train_rl_full_dataset import train_one
    env = _make_dummy_env(tiny_shandong_df)
    result = train_one("ppo", env, timesteps=100, seed=42,
                       log_dir=str(tmp_path / "tb"), ckpt_path=str(tmp_path / "ppo.zip"))
    assert result["status"] == "ok"
    assert captured["tensorboard_log"] is None


def test_run_backtest_marks_loaded_agent_trained(tiny_shandong_df, monkeypatch, tmp_path):
    import ellectric.pipeline.backtester as backtester
    from ellectric.pipeline import rl_trainer
    from ellectric.scripts.train_rl_full_dataset import run_backtest

    class FakeRunner:
        def __init__(self, env_factory):
            self._env_factory = env_factory
        def replay(self, model, load_data, price_data, start, end, strategy_name="rl"):
            if not isinstance(model, str):
                model.predict({})
            return pd.DataFrame({"pnl_hourly": [1.0], "pnl_cumulative": [1.0]})
        def compare(self, results):
            return pd.DataFrame([{"策略": k, "总收益": float(v["pnl_hourly"].sum())} for k, v in results.items()])
        @staticmethod
        def plot_comparison(results):
            class Fig:
                def write_html(self, path, include_plotlyjs="cdn", config=None):
                    Path(path).write_text("html")
            return Fig()

    monkeypatch.setattr(backtester, "BacktestRunner", FakeRunner)
    monkeypatch.setattr(backtester, "SUPPORTED_STRATEGIES", ["oracle"])
    monkeypatch.setattr(rl_trainer.RLAgentFactory, "load", lambda algo, path: FakeRLAgent(algo=algo))
    load_df = tiny_shandong_df[["timestamp", "load_mw"]]
    price_df = tiny_shandong_df[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    result = run_backtest({"ppo": {"status": "ok"}}, load_df, price_df,
                          test_start="2024-01-01", test_end="2024-01-02",
                          checkpoint_dir=str(tmp_path), report_dir=str(tmp_path))
    assert len(result["metrics"]) == 2
    assert (tmp_path / "cumulative_pnl.html").exists()


def test_build_interpretation_accepts_chinese_metrics():
    from ellectric.scripts.train_rl_full_dataset import _build_interpretation
    result = _build_interpretation(
        {"ppo": {"status": "ok"}},
        {"metrics": [{"策略": "oracle", "总收益": 10.0}, {"策略": "rl_ppo", "总收益": -1.0}]},
        ["ppo"],
    )
    assert "最佳策略: oracle" in result["summary"]


def test_write_reports_json_schema(tmp_path):
    from ellectric.scripts.train_rl_full_dataset import write_reports
    report = {
        "metadata": {
            "price_proxy": "rt_price->price_da",
            "reward_fn": "profit_only",
            "train_max_capacity_mw": 50000.0,
            "test_max_capacity_mw": 52000.0,
            "algo": ["ppo"],
            "timesteps_per_algo": 100,
            "train_range": ["2024-01-01", "2025-09-30"],
            "test_range": ["2025-10-01", "2026-01-14"],
            "tier": "tier4",
            "weather_source": "degraded",
            "generated_at": "2026-01-01T00:00:00Z",
            "git_sha": "test",
            "time_config": {"freq": "15min", "points_per_day": 96},
            "seed": 42,
        },
        "training": {"ppo": {"status": "ok", "final_reward": -100.0, "duration_s": 10.0,
                              "checkpoint_path": "/tmp/ppo.zip", "tb_log_path": "/tmp/tb", "error": None}},
        "backtest": {"metrics": [{"strategy": "oracle", "total_return": 0.0}],
                     "cumulative_pnl_html_path": "/tmp/pnl.html"},
        "interpretation": {"hard_threshold_applied": False, "summary": "test"},
    }
    j, m = write_reports(report, str(tmp_path))
    assert Path(j).exists()
    with open(j) as f:
        data = json.load(f)
    assert set(data) >= {"metadata", "training", "backtest", "interpretation"}
    assert data["metadata"]["price_proxy"] == "rt_price->price_da"
    assert data["metadata"]["reward_fn"] == "profit_only"
    assert data["metadata"]["train_max_capacity_mw"] == 50000.0
    assert data["metadata"]["test_max_capacity_mw"] == 52000.0


def test_write_reports_atomic(tmp_path):
    from ellectric.scripts.train_rl_full_dataset import write_reports
    report = {"metadata": {}, "training": {}, "backtest": {}, "interpretation": {"hard_threshold_applied": False, "summary": ""}}
    write_reports(report, str(tmp_path))
    tmp_files = list(tmp_path.glob(".tmp*"))
    assert len(tmp_files) == 0


def test_write_reports_md_sections(tmp_path):
    from ellectric.scripts.train_rl_full_dataset import write_reports
    report = {"metadata": {"k": "v"}, "training": {"ppo": {"status": "ok"}},
              "backtest": {"metrics": []}, "interpretation": {"hard_threshold_applied": False, "summary": ""}}
    j, m = write_reports(report, str(tmp_path))
    md = Path(m).read_text()
    for section in ["Metadata", "Training", "Backtest", "Interpretation"]:
        assert f"## {section}" in md


def test_main_dry_run_exit_0(fake_agent_factory, tmp_path):
    from ellectric.scripts.train_rl_full_dataset import main
    rc = main(["--dry-run", "--report-dir", str(tmp_path)])
    assert rc == 0


def test_main_algos_subset(fake_agent_factory, monkeypatch, tmp_path):
    from ellectric.scripts.train_rl_full_dataset import main
    monkeypatch.setattr("ellectric.pipeline.data_loader.create_loader",
                        lambda *a, **kw: _MockLoader(_dummy_shandong_df()))
    rc = main(["--dry-run", "--algos", "ppo", "--report-dir", str(tmp_path)])
    assert rc == 0


class _MockLoader:
    def __init__(self, df):
        self._df = df
    def load_data(self):
        return self._df.copy()


class _FakeEnv:
    def __init__(self, **kwargs):
        self._load_data = kwargs.get("load_data", pd.DataFrame())
        self._price_data = kwargs.get("price_data", pd.DataFrame())
        self._max_capacity = kwargs.get("max_capacity", 1000.0)
        self._reward_fn_name = "profit_only" if isinstance(kwargs.get("reward_fn"), str) else "custom"
        self.action_space = type("box", (), {"shape": (96,)})()
        self.observation_space = type("dict", (), {"keys": lambda self: ["a", "b"]})()
    def reset(self):
        return {}, {}
    def step(self, action):
        return {}, 0.0, False, False, {}


def _make_dummy_env(df):
    load_df = df[["timestamp", "load_mw"]]
    price_df = df[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    return _FakeEnv(load_data=load_df, price_data=price_df, max_capacity=float(df["load_mw"].max()),
                    reward_fn="profit_only")


def _dummy_shandong_df():
    """More realistic mock (200+ rows, all columns needed)."""
    n = 300
    timestamps = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    np.random.seed(42)
    return pd.DataFrame({
        "timestamp": timestamps,
        "load_mw": np.random.uniform(40000, 60000, n),
        "rt_price": np.random.uniform(200, 600, n),
        "da_price": np.random.uniform(200, 600, n),
        "wind_actual_mw": np.random.uniform(2000, 8000, n),
        "solar_actual_mw": np.random.uniform(0, 5000, n),
        "is_holiday": np.zeros(n, dtype=int),
        "is_weekend": (pd.Series(timestamps).dt.dayofweek >= 5).astype(int),
    })
