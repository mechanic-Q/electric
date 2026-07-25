"""Test per-instance evidence layering in build_strategy_evidence.

No live-evaluation dependency required — uses mock report JSON and Plotly HTML.
"""

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from ellectric.config import TimeConfig
from ellectric.service.strategy_evidence import (
    TEST_POINTS,
    REPLAY_POINTS,
    _validate_report_totals_per_instance,
    build_strategy_evidence,
)

_REPLAY_START = pd.Timestamp("2025-10-01", tz="Asia/Shanghai")
_TEST_START = pd.Timestamp("2025-10-01", tz="Asia/Shanghai")
_FREQ = TimeConfig.freq
_EXECUTABLE = ("td3", "ppo", "sac", "trend")


# ── Helpers ──────────────────────────────────────────────────────────


def _make_timestamps(start: pd.Timestamp, points: int) -> list[str]:
    return [
        (start + i * pd.Timedelta(seconds=900)).isoformat()
        for i in range(points)
    ]


def _make_market_df(points: int, start: pd.Timestamp) -> pd.DataFrame:
    timestamps = [start + i * pd.Timedelta(seconds=900) for i in range(points)]
    # Prices range 400-800 (mean 600) so spreads stay >> contribution/scale ratio
    return pd.DataFrame({
        "timestamp": timestamps,
        "rt_price": [600.0 + math.sin(i * 0.1) * 200 for i in range(points)],
        "load_mw": [30000.0 + math.sin(i * 0.05) * 5000 for i in range(points)],
    })


def _make_minimal_evaluation_report() -> dict[str, Any]:
    return {
        "protocol": {
            "train_start": "2024-01-01",
            "train_end": "2025-09-30",
            "test_start": "2025-10-01",
            "test_end": "2026-01-15",
            "seed": 42,
            "timesteps": 200000,
            "tier": "tier4",
            "price_proxy": "rt_price->price_da",
            "algos": ["ppo", "sac", "td3"],
            "baselines": ["persistence", "mean", "oracle"],
        },
        "metadata": {
            "generated_at": "2026-07-20T12:00:00",
            "git_sha": "a" * 40,
            "protocol_summary": {
                "train_start": "2024-01-01",
                "train_end": "2025-09-30",
                "test_start": "2025-10-01",
                "test_end": "2026-01-15",
                "algos": ["ppo", "sac", "td3"],
                "baselines": ["persistence", "mean", "oracle"],
                "seed": 42,
                "timesteps": 200000,
                "tier": "tier4",
                "price_proxy": "rt_price->price_da",
            },
        },
        "artifacts": {
            "cumulative_pnl_html": "ellectric/reports/rl_full_dataset/cumulative_pnl.html",
        },
        "metrics": [
            {"strategy": "baseline_persistence", "status": "ok", "total_pnl": 80.0},
            {"strategy": "baseline_mean", "status": "ok", "total_pnl": 0.0},
            {"strategy": "oracle", "status": "ok", "total_pnl": 400.0},
            {"strategy": "rl_ppo", "status": "ok", "total_pnl": 100.0},
            {"strategy": "rl_sac", "status": "ok", "total_pnl": 80.0},
            {"strategy": "rl_td3", "status": "ok", "total_pnl": 120.0},
        ],
    }


def _make_plotly_html(
    trace_values: dict[str, list[float]],
    timestamps: list[str],
) -> str:
    """Generate minimal Plotly HTML with named traces and list-format y values."""
    traces_json = []
    trace_names = {
        "trend": "趋势策略 (Trend)",
        "flat": "空仓策略 (Flat)",
        "oracle": "先知策略 (Oracle)",
        "ppo": "PPO 强化学习 (RL Agent)",
        "sac": "SAC 强化学习 (RL Agent)",
        "td3": "TD3 强化学习 (RL Agent)",
    }
    for strategy, name in trace_names.items():
        values = trace_values.get(strategy, [0.0] * TEST_POINTS)
        traces_json.append({
            "name": name,
            "x": timestamps[:len(values)],
            "y": values,
        })
    return f"Plotly.newPlot(\"chart\",{json.dumps(traces_json)},\n{{}})\n"


def _cumulative_from_trace(total: float, points: int) -> list[float]:
    """Generate a cumulative trace with both positive and negative steps, ending at total."""
    if points <= 0:
        return []
    base_step = total / points
    values: list[float] = []
    accum = 0.0
    for i in range(points - 1):
        step = base_step + base_step * 1.5 * math.sin(i * 0.7)
        accum += step
        values.append(accum)
    step = total - accum
    values.append(accum + step)
    return values


# ── Tests: _validate_report_totals_per_instance ─────────────────────


class TestValidateReportTotalsPerInstance:
    def test_all_match(self):
        report = _make_minimal_evaluation_report()
        traces = {
            s: {"values": [0.0, v]}
            for s, v in [("trend", 80.0), ("flat", 0.0), ("oracle", 400.0),
                         ("ppo", 100.0), ("sac", 80.0), ("td3", 120.0)]
        }
        result = _validate_report_totals_per_instance(report, traces)
        for strategy in ("td3", "ppo", "sac", "trend"):
            assert result.get(strategy) is True, f"{strategy} should match"

    def test_one_mismatch(self):
        report = _make_minimal_evaluation_report()
        traces = {
            s: {"values": [0.0, v]}
            for s, v in [("trend", 80.0), ("flat", 0.0), ("oracle", 400.0),
                         ("ppo", 9999999.0), ("sac", 80.0), ("td3", 120.0)]
        }
        result = _validate_report_totals_per_instance(report, traces)
        assert result["ppo"] is False
        assert result["td3"] is True
        assert result["sac"] is True

    def test_missing_trace_returns_false(self):
        report = _make_minimal_evaluation_report()
        traces = {
            s: {"values": [0.0, v]}
            for s, v in [("trend", 80.0), ("flat", 0.0), ("oracle", 400.0),
                         ("sac", 80.0), ("td3", 120.0)]
        }
        result = _validate_report_totals_per_instance(report, traces)
        assert "ppo" not in result or result.get("ppo") is False

    def test_empty_metrics_returns_empty(self):
        report = {"protocol": {}, "metadata": {}}
        result = _validate_report_totals_per_instance(report, {})
        assert result == {}


# ── Tests: build_strategy_evidence per-instance layering ────────────


class TestBuildStrategyEvidence:
    @pytest.fixture
    def artifacts(self, tmp_path: Path) -> dict[str, Any]:
        """Create minimal mock evaluation report, plotly HTML, and market data."""
        reports_root = tmp_path
        report = _make_minimal_evaluation_report()
        (reports_root / "rl_full_dataset").mkdir(parents=True, exist_ok=True)

        # Write evaluation report
        (reports_root / "rl_full_dataset" / "evaluation_report.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )

        # Create cumulative values per strategy
        trace_values: dict[str, list[float]] = {}
        for s, total in [
            ("trend", 80.0), ("flat", 0.0), ("oracle", 400.0),
            ("ppo", 100.0), ("sac", 80.0), ("td3", 120.0),
        ]:
            trace_values[s] = _cumulative_from_trace(total, TEST_POINTS)

        test_ts = _make_timestamps(_TEST_START, TEST_POINTS)
        html = _make_plotly_html(trace_values, test_ts)
        (reports_root / "rl_full_dataset" / "cumulative_pnl.html").write_text(
            html, encoding="utf-8"
        )

        replay_market = _make_market_df(REPLAY_POINTS, _REPLAY_START)
        test_market = _make_market_df(TEST_POINTS, _TEST_START)

        return {
            "reports_root": reports_root,
            "replay_market": replay_market,
            "test_market": test_market,
        }

    def test_all_instances_valid(self, artifacts: dict[str, Any]):
        result = build_strategy_evidence(
            artifacts["replay_market"],
            artifacts["test_market"],
            artifacts["reports_root"],
        )
        assert result["status"] == "ok"
        for s in _EXECUTABLE:
            st = result.get("instance_status", {}).get(s, {})
            assert st.get("status") == "ok", f"{s} should be ok, got {st}"

    def test_one_instance_degraded(self, artifacts: dict[str, Any]):
        """Corrupt PPO's total in the report so its total doesn't match its trace."""
        report_path = artifacts["reports_root"] / "rl_full_dataset" / "evaluation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for m in report["metrics"]:
            if m["strategy"] == "rl_ppo":
                m["total_pnl"] = 9999999.0
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

        result = build_strategy_evidence(
            artifacts["replay_market"],
            artifacts["test_market"],
            artifacts["reports_root"],
        )
        assert result["status"] == "ok"
        assert result["instance_status"]["ppo"]["status"] == "degraded"
        assert result["instance_status"]["td3"]["status"] == "ok"
        assert result["instance_status"]["sac"]["status"] == "ok"
        assert result["instance_status"]["trend"]["status"] == "ok"

    def test_protocol_accepts_new_values(self, artifacts: dict[str, Any]):
        """A snapshot with different but internally consistent values is accepted."""
        report_path = artifacts["reports_root"] / "rl_full_dataset" / "evaluation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["metrics"] = [
            {"strategy": "baseline_persistence", "status": "ok", "total_pnl": 60.0},
            {"strategy": "baseline_mean", "status": "ok", "total_pnl": 0.0},
            {"strategy": "oracle", "status": "ok", "total_pnl": 200.0},
            {"strategy": "rl_ppo", "status": "ok", "total_pnl": 80.0},
            {"strategy": "rl_sac", "status": "ok", "total_pnl": 50.0},
            {"strategy": "rl_td3", "status": "ok", "total_pnl": 100.0},
        ]
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

        trace_values: dict[str, list[float]] = {}
        for s, total in [
            ("trend", 60.0), ("flat", 0.0), ("oracle", 200.0),
            ("ppo", 80.0), ("sac", 50.0), ("td3", 100.0),
        ]:
            trace_values[s] = _cumulative_from_trace(total, TEST_POINTS)

        test_ts = _make_timestamps(_TEST_START, TEST_POINTS)
        html = _make_plotly_html(trace_values, test_ts)
        (artifacts["reports_root"] / "rl_full_dataset" / "cumulative_pnl.html").write_text(
            html, encoding="utf-8"
        )

        result = build_strategy_evidence(
            artifacts["replay_market"],
            artifacts["test_market"],
            artifacts["reports_root"],
        )
        assert result["status"] == "ok"
        for s in _EXECUTABLE:
            st = result.get("instance_status", {}).get(s, {})
            assert st.get("status") == "ok", f"{s} should be ok, got {st}"
