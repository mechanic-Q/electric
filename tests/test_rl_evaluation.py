"""
RL 统一评估 — 单元测试

测试约定（D-007@v1）：
- 所有测试通过 monkeypatch 注入 fake BaseRLAgent adapter
- 不调用真实 stable_baselines3 PPO/SAC/TD3 .learn()
- 不依赖网络、不依赖真实 weather cache
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ellectric.pipeline.backtester import SUPPORTED_STRATEGIES
from ellectric.pipeline.rl_evaluation import (
    EvaluationProtocol,
    StrategyEvaluation,
    compute_strategy_metrics,
    evaluate_baselines,
    evaluate_rl_agents,
    generate_cumulative_pnl_html,
    write_evaluation_report,
)
from ellectric.pipeline.rl_trainer import BaseRLAgent, RLAgentFactory


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


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def tiny_shandong():
    np.random.seed(42)
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


def _dummy_trades(n=10):
    np.random.seed(42)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
        "bid_mw": np.random.uniform(40000, 50000, n),
        "cleared_mw": np.random.uniform(40000, 50000, n),
        "clearing_price": np.random.uniform(200, 600, n),
        "actual_load": np.random.uniform(40000, 60000, n),
        "pnl_hourly": np.random.uniform(-10000, 10000, n),
        "pnl_cumulative": np.random.uniform(-50000, 50000, n),
        "strategy": "test",
    })


class FakeRunner:
    def __init__(self, env_factory=None, initial_cash=0.0):
        self._env_factory = env_factory

    def replay(self, model, load_data, price_data, start, end, strategy_name="rl"):
        if isinstance(model, str) and model not in SUPPORTED_STRATEGIES:
            raise ValueError(f"Unknown strategy: {model}")
        return _dummy_trades()

    @staticmethod
    def plot_comparison(results):
        class Fig:
            def write_html(self, path, include_plotlyjs="cdn", config=None):
                Path(path).write_text("html content")
        return Fig()


@pytest.fixture
def fake_runner():
    return FakeRunner()


@pytest.fixture
def fake_agent_factory(monkeypatch):
    def fake_load(algo, path, env=None):
        return FakeRLAgent(algo=algo)
    monkeypatch.setattr(RLAgentFactory, "load", fake_load)
    return monkeypatch


# ═══════════════════════════════════════════════════════════════
# Test 1
# ═══════════════════════════════════════════════════════════════


def test_evaluation_protocol_defaults():
    p = EvaluationProtocol(
        train_start="2024-01-01", train_end="2024-02-01",
        test_start="2024-02-01", test_end="2024-03-01",
    )
    assert p.algos == ("ppo", "sac", "td3")
    assert p.baselines == ("baseline_persistence", "baseline_mean", "oracle")
    assert p.seed == 42
    assert p.timesteps == 50000
    assert p.tier == "tier4"
    assert p.price_proxy == "rt_price->price_da"
    assert p.checkpoint_dir == "models/rl_full_dataset"
    assert p.report_dir == "ellectric/reports/rl_full_dataset"


# ═══════════════════════════════════════════════════════════════
# Test 2
# ═══════════════════════════════════════════════════════════════


def test_strategy_evaluation_defaults():
    ev = StrategyEvaluation(strategy="test", status="ok")
    assert ev.strategy == "test"
    assert ev.status == "ok"
    assert ev.trades is None
    assert ev.error is None
    assert ev.artifact_path is None


# ═══════════════════════════════════════════════════════════════
# Test 3
# ═══════════════════════════════════════════════════════════════


def test_evaluate_baselines_success(tiny_shandong, fake_runner):
    load = tiny_shandong[["timestamp", "load_mw"]]
    price = tiny_shandong[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    results = evaluate_baselines(
        fake_runner,
        ("baseline_persistence", "oracle"),
        load, price,
        "2024-01-01", "2024-01-02",
    )
    assert len(results) == 2
    for name in ("baseline_persistence", "oracle"):
        assert results[name].status == "ok"
        assert results[name].trades is not None


# ═══════════════════════════════════════════════════════════════
# Test 4
# ═══════════════════════════════════════════════════════════════


def test_evaluate_baselines_skip_missing(tiny_shandong, fake_runner):
    load = tiny_shandong[["timestamp", "load_mw"]]
    price = tiny_shandong[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    results = evaluate_baselines(
        fake_runner,
        ("baseline_persistence", "nonexistent_strategy", "oracle"),
        load, price,
        "2024-01-01", "2024-01-02",
    )
    assert results["baseline_persistence"].status == "ok"
    assert results["oracle"].status == "ok"
    assert results["nonexistent_strategy"].status == "error"
    assert "Unknown strategy" in results["nonexistent_strategy"].error


# ═══════════════════════════════════════════════════════════════
# Test 5
# ═══════════════════════════════════════════════════════════════


def test_evaluate_rl_agents_checkpoint_missing(tiny_shandong, tmp_path):
    runner = FakeRunner()
    load = tiny_shandong[["timestamp", "load_mw"]]
    price = tiny_shandong[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})
    fake_dir = str(tmp_path / "nonexistent")
    results = evaluate_rl_agents(
        runner, ("ppo", "sac", "td3"), fake_dir,
        load, price,
        "2024-01-01", "2024-01-02",
    )
    for name in ("rl_ppo", "rl_sac", "rl_td3"):
        assert results[name].status == "error"
        assert "checkpoint 不存在" in results[name].error


# ═══════════════════════════════════════════════════════════════
# Test 6
# ═══════════════════════════════════════════════════════════════


def test_compute_strategy_metrics_columns():
    evaluations = {
        "baseline_persistence": StrategyEvaluation(
            strategy="baseline_persistence", status="ok", trades=_dummy_trades(10),
        ),
        "oracle": StrategyEvaluation(
            strategy="oracle", status="ok", trades=_dummy_trades(15),
        ),
    }
    df = compute_strategy_metrics(evaluations)
    expected_cols = [
        "strategy", "total_pnl", "sharpe", "win_rate", "max_drawdown",
        "profit_factor", "volatility", "oracle_gap", "baseline_delta",
        "rank", "status",
    ]
    assert list(df.columns) == expected_cols


# ═══════════════════════════════════════════════════════════════
# Test 7
# ═══════════════════════════════════════════════════════════════


def test_compute_strategy_metrics_empty():
    df = compute_strategy_metrics({})
    assert len(df) == 0
    expected_cols = [
        "strategy", "total_pnl", "sharpe", "win_rate", "max_drawdown",
        "profit_factor", "volatility", "oracle_gap", "baseline_delta",
        "rank", "status",
    ]
    assert list(df.columns) == expected_cols


# ═══════════════════════════════════════════════════════════════
# Test 8
# ═══════════════════════════════════════════════════════════════


def test_compute_strategy_metrics_failure_isolation():
    evaluations = {
        "good": StrategyEvaluation(strategy="good", status="ok", trades=_dummy_trades(10)),
        "bad": StrategyEvaluation(strategy="bad", status="error", error="broken"),
        "skipped": StrategyEvaluation(strategy="skipped", status="skipped"),
    }
    df = compute_strategy_metrics(evaluations)
    assert set(df["strategy"]) == {"good", "bad", "skipped"}
    assert df[df["strategy"] == "bad"]["status"].iloc[0] == "error"
    assert df[df["strategy"] == "skipped"]["status"].iloc[0] == "skipped"
    bad_row = df[df["strategy"] == "bad"].iloc[0]
    assert np.isnan(bad_row["total_pnl"])
    good_row = df[df["strategy"] == "good"].iloc[0]
    assert not np.isnan(good_row["total_pnl"])


# ═══════════════════════════════════════════════════════════════
# Test 9
# ═══════════════════════════════════════════════════════════════


def test_write_evaluation_report_json_schema(tmp_path):
    protocol = EvaluationProtocol(
        train_start="2024-01-01", train_end="2024-02-01",
        test_start="2024-02-01", test_end="2024-03-01",
    )
    training = {
        "ppo": {"status": "ok", "final_reward": -100.0},
        "sac": {"status": "error", "error": "failed"},
    }
    evaluations = {
        "baseline_persistence": StrategyEvaluation(
            strategy="baseline_persistence", status="ok", trades=_dummy_trades(10),
        ),
        "rl_ppo": StrategyEvaluation(
            strategy="rl_ppo", status="error", error="checkpoint missing",
        ),
    }
    metrics = compute_strategy_metrics(evaluations)
    paths = write_evaluation_report(protocol, training, evaluations, metrics, str(tmp_path))
    with open(paths["json_path"]) as f:
        data = json.load(f)
    for key in ("metadata", "protocol", "training", "evaluations", "metrics", "artifacts"):
        assert key in data, f"missing key: {key}"
    assert data["metadata"]["protocol_summary"]["train_start"] == "2024-01-01"
    assert data["protocol"]["checkpoint_dir"] == "models/rl_full_dataset"


# ═══════════════════════════════════════════════════════════════
# Test 10
# ═══════════════════════════════════════════════════════════════


def test_write_evaluation_report_files_exist(tmp_path):
    protocol = EvaluationProtocol(
        train_start="2024-01-01", train_end="2024-02-01",
        test_start="2024-02-01", test_end="2024-03-01",
    )
    paths = write_evaluation_report(protocol, {}, {}, pd.DataFrame(), str(tmp_path))
    for key in ("json_path", "csv_path", "md_path"):
        assert Path(paths[key]).exists(), f"missing: {paths[key]}"


# ═══════════════════════════════════════════════════════════════
# Test 11
# ═══════════════════════════════════════════════════════════════


def test_write_evaluation_report_failure_diagnosis(tmp_path):
    protocol = EvaluationProtocol(
        train_start="2024-01-01", train_end="2024-02-01",
        test_start="2024-02-01", test_end="2024-03-01",
    )
    evaluations = {
        "rl_ppo": StrategyEvaluation(
            strategy="rl_ppo", status="error", error="checkpoint missing",
        ),
        "oracle": StrategyEvaluation(
            strategy="oracle", status="ok", trades=_dummy_trades(5),
        ),
    }
    metrics = compute_strategy_metrics(evaluations)
    paths = write_evaluation_report(protocol, {}, evaluations, metrics, str(tmp_path))
    with open(paths["json_path"]) as f:
        data = json.load(f)
    assert data["evaluations"]["rl_ppo"]["status"] == "error"
    assert data["evaluations"]["rl_ppo"]["error"] == "checkpoint missing"
    assert data["evaluations"]["oracle"]["status"] == "ok"
    md = Path(paths["md_path"]).read_text()
    assert "rl_ppo" in md
    assert "checkpoint missing" in md
    assert "Failure Diagnosis" in md
    assert "All strategies completed successfully" not in md


# ═══════════════════════════════════════════════════════════════
# Test 12
# ═══════════════════════════════════════════════════════════════


def test_dry_run_no_training(tiny_shandong, tmp_path, monkeypatch):
    load = tiny_shandong[["timestamp", "load_mw"]]
    price = tiny_shandong[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})

    called = []

    def spy_load(algo, path, env=None):
        called.append((algo, path))
        return FakeRLAgent(algo=algo)

    monkeypatch.setattr(RLAgentFactory, "load", spy_load)

    runner = FakeRunner()
    fake_dir = str(tmp_path / "nonexistent")
    results = evaluate_rl_agents(
        runner, ("ppo", "sac"), fake_dir,
        load, price, "2024-01-01", "2024-01-02",
    )
    assert len(called) == 0
    for name in ("rl_ppo", "rl_sac"):
        assert results[name].status == "error"
        assert "checkpoint" in results[name].error.lower()


# ═══════════════════════════════════════════════════════════════
# Test 13
# ═══════════════════════════════════════════════════════════════


def test_generate_pnl_html_no_ok(tmp_path):
    evaluations = {
        "rl_ppo": StrategyEvaluation(strategy="rl_ppo", status="error", error="failed"),
    }
    result = generate_cumulative_pnl_html(evaluations, str(tmp_path))
    assert result == ""


# ═══════════════════════════════════════════════════════════════
# Test 14
# ═══════════════════════════════════════════════════════════════


def test_full_pipeline_smoke(tiny_shandong, fake_runner, fake_agent_factory, tmp_path):
    load = tiny_shandong[["timestamp", "load_mw"]]
    price = tiny_shandong[["timestamp", "rt_price"]].rename(columns={"rt_price": "price_da"})

    ckpt_dir = tmp_path / "ckpts"
    ckpt_dir.mkdir()
    for algo in ("ppo", "td3"):
        (ckpt_dir / f"{algo}.zip").write_text("fake")

    protocol = EvaluationProtocol(
        train_start="2024-01-01", train_end="2024-01-01",
        test_start="2024-01-01", test_end="2024-01-02",
        checkpoint_dir=str(ckpt_dir),
        report_dir=str(tmp_path / "report"),
    )

    baseline_results = evaluate_baselines(
        fake_runner, protocol.baselines, load, price,
        protocol.test_start, protocol.test_end,
    )
    assert len(baseline_results) == len(protocol.baselines)

    rl_results = evaluate_rl_agents(
        fake_runner, protocol.algos, protocol.checkpoint_dir,
        load, price,
        protocol.test_start, protocol.test_end,
    )
    assert len(rl_results) == len(protocol.algos)

    all_evals = {**baseline_results, **rl_results}
    metrics = compute_strategy_metrics(all_evals)
    assert len(metrics) == len(protocol.baselines) + len(protocol.algos)

    training = {"ppo": {"status": "ok"}, "td3": {"status": "ok"}}
    paths = write_evaluation_report(
        protocol, training, all_evals, metrics,
        str(tmp_path / "report"),
    )
    for p in paths.values():
        assert Path(p).exists()
