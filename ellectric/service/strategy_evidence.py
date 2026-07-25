"""Build the versioned strategy evidence used by the static showcase replay."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import pandas as pd

from ellectric.config import TimeConfig


REPLAY_START = "2025-10-01T00:00:00+08:00"
REPLAY_END = "2025-10-30T23:45:00+08:00"
TEST_START = "2025-10-01T00:00:00+08:00"
TEST_END = "2026-01-14T23:45:00+08:00"
REPLAY_POINTS = 30 * TimeConfig.points_per_day
TEST_POINTS = 106 * TimeConfig.points_per_day
TIMEZONE = "Asia/Shanghai"
FLAT_POSITION_THRESHOLD = 0.01
INDETERMINATE_SPREAD_THRESHOLD = 0.01
POSITION_BOUND_TOLERANCE = 1.001

_TRACE_NAMES = {
    "趋势策略 (Trend)": "trend",
    "空仓策略 (Flat)": "flat",
    "先知策略 (Oracle)": "oracle",
    "PPO 强化学习 (RL Agent)": "ppo",
    "SAC 强化学习 (RL Agent)": "sac",
    "TD3 强化学习 (RL Agent)": "td3",
}
_EXECUTABLE_STRATEGIES = ("td3", "ppo", "sac", "trend")
_REPORT_STRATEGIES = {
    "trend": "baseline_persistence",
    "flat": "baseline_mean",
    "oracle": "oracle",
    "ppo": "rl_ppo",
    "sac": "rl_sac",
    "td3": "rl_td3",
}
_REFERENCE_STRATEGIES = {"flat", "oracle"}


class StrategyEvidenceError(ValueError):
    """Raised when source evidence cannot form one trustworthy snapshot."""


def build_strategy_evidence(
    replay_market: pd.DataFrame,
    test_market: pd.DataFrame,
    reports_root: Path,
) -> dict[str, Any]:
    """Build and validate the fixed October strategy evidence snapshot."""
    report_dir = reports_root / "rl_full_dataset"
    report_path = report_dir / "evaluation_report.json"
    chart_path = report_dir / "cumulative_pnl.html"
    report = _read_json_object(report_path)
    protocol = report.get("protocol")
    metadata = report.get("metadata")
    if not isinstance(protocol, dict) or not isinstance(metadata, dict):
        raise StrategyEvidenceError("RL evaluation report lacks protocol or metadata")

    _validate_protocol(protocol)
    _validate_provenance(report, protocol, metadata)
    replay_timestamps = _market_timestamps(
        replay_market, REPLAY_POINTS, REPLAY_START, REPLAY_END
    )
    test_timestamps = _market_timestamps(test_market, TEST_POINTS, TEST_START, TEST_END)
    traces = _read_plotly_traces(chart_path)
    any_trace = traces[next(iter(traces))]
    if any_trace["timestamps"] != test_timestamps:
        raise StrategyEvidenceError(
            "strategy timestamps do not align with the 106-day market window"
        )
    if replay_timestamps != any_trace["timestamps"][:REPLAY_POINTS]:
        raise StrategyEvidenceError(
            "strategy timestamps do not align with the 30-day replay"
        )

    report_validity = _validate_report_totals_per_instance(report, traces)
    prices = _finite_column(replay_market, "rt_price")
    capacity_scale = max(_finite_column(test_market, "load_mw"))
    daily_baselines = _daily_baselines(prices)
    strategy_series: dict[str, dict[str, Any]] = {}
    daily_series: dict[str, dict[str, list[Any]]] = {}
    instance_status: dict[str, dict[str, str | None]] = {}

    for strategy in _EXECUTABLE_STRATEGIES:
        if strategy not in traces:
            instance_status[strategy] = {
                "status": "degraded", "degradation_reason": "trace data missing"
            }
            continue
        if not report_validity.get(strategy, True):
            instance_status[strategy] = {
                "status": "degraded", "degradation_reason": "report total does not match trace"
            }
            continue
        try:
            cumulative = traces[strategy]["values"][:REPLAY_POINTS]
            increments = _increments(cumulative)
            positions, states = _reconstruct_positions(
                increments, prices, daily_baselines, capacity_scale
            )
            strategy_series[strategy] = {
                "simulated_spread_value": increments,
                "cumulative_simulated_spread_value": cumulative,
                "reconstructed_position": positions,
                "position_state": states,
            }
            daily_series[strategy] = _aggregate_daily(cumulative, increments, positions)
            instance_status[strategy] = {"status": "ok", "degradation_reason": None}
        except Exception as exc:
            instance_status[strategy] = {
                "status": "degraded", "degradation_reason": str(exc)
            }

    oracle_cumulative = traces["oracle"]["values"][:REPLAY_POINTS]
    oracle_increments = _increments(oracle_cumulative)
    oracle_daily = _daily_sums(oracle_increments)
    flat_values = traces["flat"]["values"][:REPLAY_POINTS]
    if any(abs(value) > 1e-9 for value in flat_values):
        raise StrategyEvidenceError("flat reference is not zero")

    valid_strategies = tuple(
        s for s in _EXECUTABLE_STRATEGIES
        if instance_status.get(s, {}).get("status") == "ok"
    )
    if not valid_strategies:
        raise StrategyEvidenceError("no executable strategies have valid evidence")

    summary = _build_summary(strategy_series, daily_series, oracle_cumulative[-1], valid_strategies)
    snapshot: dict[str, Any] = {
        "status": "ok",
        "degradation_reason": None,
        "instance_status": instance_status,
        "snapshot_version": 1,
        "window": {
            "start": REPLAY_START,
            "end": REPLAY_END,
            "timezone": TIMEZONE,
            "points": REPLAY_POINTS,
            "points_per_day": TimeConfig.points_per_day,
            "standardized_day": "00:00-23:45",
        },
        "methodology": {
            "value_name": "simulated_spread_value",
            "unit": "simulated_unit",
            "settlement_price": "historical_rt_price",
            "formula": "position * capacity_scale * (rt_price - daily_baseline_price) / 1000",
            "capacity_scale_mw": capacity_scale,
            "capacity_scale_source": "106_day_test_window_max_load",
            "baseline_initialization_days": 7,
            "baseline_after_initialization": "preceding_672_point_mean",
            "approximate_flat_position_threshold": FLAT_POSITION_THRESHOLD,
            "indeterminate_spread_threshold_cny_per_mwh": INDETERMINATE_SPREAD_THRESHOLD,
            "reconstructed_position_bound": 1.0,
            "zero_reference": "flat",
        },
        "summary": summary,
        "timeseries": {
            "timestamps": replay_timestamps,
            "daily_baseline_price": daily_baselines,
            "strategies": strategy_series,
        },
        "daily": {
            "dates": [f"2025-10-{day:02d}" for day in range(1, 31)],
            "baseline_initialization": [True] * 7 + [False] * 23,
            "strategies": daily_series,
        },
        "oracle": {
            "role": "theoretical_upper_bound",
            "simulated_spread_value": oracle_increments,
            "cumulative_simulated_spread_value": oracle_cumulative,
            "daily_simulated_spread_value": oracle_daily,
            "terminal_simulated_spread_value": oracle_cumulative[-1],
            "capture_rate": {
                row["strategy"]: row["oracle_capture_rate"] for row in summary
            },
        },
        "long_term_evidence": _long_term_evidence(report, traces),
        "provenance": {
            "source_generated_at": metadata.get("generated_at"),
            "source_git_sha": metadata.get("git_sha"),
            "training_steps_per_algorithm": protocol.get("timesteps"),
            "seed": protocol.get("seed"),
            "feature_tier": protocol.get("tier"),
            "source_evaluation_window": {
                "start": protocol.get("test_start"),
                "end_exclusive": protocol.get("test_end"),
                "points": TEST_POINTS,
            },
            "source_artifacts": {
                "evaluation_report": "rl_full_dataset/evaluation_report.json",
                "cumulative_path": "rl_full_dataset/cumulative_pnl.html",
            },
            "source_hashes": {
                "evaluation_report_sha256": _file_hash(report_path),
                "cumulative_path_sha256": _file_hash(chart_path),
            },
        },
    }
    _validate_snapshot(snapshot, valid_strategies)
    snapshot["provenance"]["content_hash"] = hashlib.sha256(
        json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return snapshot


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise StrategyEvidenceError(f"strategy evidence file missing: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StrategyEvidenceError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise StrategyEvidenceError(f"{path.name} is not a JSON object")
    return value


def _validate_protocol(protocol: dict[str, Any]) -> None:
    expected = {
        "train_start": "2024-01-01",
        "train_end": "2025-09-30",
        "test_start": "2025-10-01",
        "test_end": "2026-01-15",
        "seed": 42,
        "timesteps": 200000,
        "tier": "tier4",
        "price_proxy": "rt_price->price_da",
    }
    mismatches = [key for key, value in expected.items() if protocol.get(key) != value]
    if mismatches:
        raise StrategyEvidenceError(
            "evaluation protocol mismatch: " + ", ".join(mismatches)
        )


def _validate_provenance(
    report: dict[str, Any], protocol: dict[str, Any], metadata: dict[str, Any]
) -> None:
    if (
        not isinstance(metadata.get("generated_at"), str)
        or not metadata["generated_at"]
    ):
        raise StrategyEvidenceError("evaluation metadata lacks generated_at")
    git_sha = metadata.get("git_sha")
    if not isinstance(git_sha, str) or len(git_sha) != 40:
        raise StrategyEvidenceError("evaluation metadata lacks a full source Git SHA")
    summary = metadata.get("protocol_summary")
    if not isinstance(summary, dict):
        raise StrategyEvidenceError("evaluation metadata lacks protocol_summary")
    for key in (
        "train_start",
        "train_end",
        "test_start",
        "test_end",
        "algos",
        "baselines",
        "seed",
        "timesteps",
        "tier",
        "price_proxy",
    ):
        if summary.get(key) != protocol.get(key):
            raise StrategyEvidenceError(f"protocol metadata mismatch: {key}")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict) or artifacts.get("cumulative_pnl_html") != (
        "ellectric/reports/rl_full_dataset/cumulative_pnl.html"
    ):
        raise StrategyEvidenceError(
            "evaluation report points to an incompatible cumulative artifact"
        )


def _market_timestamps(
    frame: pd.DataFrame, expected_points: int, expected_start: str, expected_end: str
) -> list[str]:
    if len(frame) != expected_points or "timestamp" not in frame.columns:
        raise StrategyEvidenceError(
            f"market window must contain exactly {expected_points} timestamped points"
        )
    timestamps = [_shanghai_iso(value) for value in frame["timestamp"]]
    if timestamps[0] != expected_start or timestamps[-1] != expected_end:
        raise StrategyEvidenceError("market window boundary mismatch")
    expected = [
        value.isoformat()
        for value in pd.date_range(
            expected_start, periods=expected_points, freq=TimeConfig.freq
        )
    ]
    if timestamps != expected:
        raise StrategyEvidenceError(
            "market window is not a contiguous 15-minute series"
        )
    return timestamps


def _shanghai_iso(value: Any) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(TIMEZONE)
    else:
        timestamp = timestamp.tz_convert(TIMEZONE)
    return timestamp.isoformat()


def _read_plotly_traces(path: Path) -> dict[str, dict[str, list[Any]]]:
    """Read the one retained point-level artifact; any format drift fails closed."""
    if not path.exists():
        raise StrategyEvidenceError(f"strategy evidence file missing: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
        position = text.index("Plotly.newPlot(") + len("Plotly.newPlot(")
        decoder = json.JSONDecoder()
        position = _skip_json_separator(text, position, comma=False)
        _, position = decoder.raw_decode(text, position)
        position = _skip_json_separator(text, position, comma=True)
        raw_traces, _ = decoder.raw_decode(text, position)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise StrategyEvidenceError(f"cannot parse {path.name}: {exc}") from exc
    if not isinstance(raw_traces, list):
        raise StrategyEvidenceError("cumulative Plotly artifact has no trace list")

    traces: dict[str, dict[str, list[Any]]] = {}
    for raw_trace in raw_traces:
        if not isinstance(raw_trace, dict) or raw_trace.get("name") not in _TRACE_NAMES:
            continue
        strategy = _TRACE_NAMES[raw_trace["name"]]
        raw_timestamps = raw_trace.get("x")
        if not isinstance(raw_timestamps, list):
            raise StrategyEvidenceError(f"{strategy} trace timestamps are missing")
        timestamps = [_shanghai_iso(value) for value in raw_timestamps]
        values = _decode_plotly_values(raw_trace.get("y"))
        if len(timestamps) != TEST_POINTS or len(values) != TEST_POINTS:
            raise StrategyEvidenceError(
                f"{strategy} trace must contain exactly {TEST_POINTS} points"
            )
        traces[strategy] = {"timestamps": timestamps, "values": values}
    missing_references = _REFERENCE_STRATEGIES - set(traces)
    if missing_references:
        raise StrategyEvidenceError(
            "cumulative Plotly artifact lacks required references: "
            + ", ".join(sorted(missing_references))
        )
    for strategy, trace in traces.items():
        if trace["timestamps"] != traces[next(iter(traces))]["timestamps"]:
            raise StrategyEvidenceError(f"{strategy} trace timestamps are misaligned")
    return traces


def _skip_json_separator(text: str, position: int, *, comma: bool) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    if comma:
        if position >= len(text) or text[position] != ",":
            raise StrategyEvidenceError("invalid Plotly call separator")
        position += 1
        while position < len(text) and text[position].isspace():
            position += 1
    return position


def _decode_plotly_values(value: Any) -> list[float]:
    if isinstance(value, list):
        result = [float(item) for item in value]
    elif isinstance(value, dict) and value.get("dtype") in {"f8", "f4"}:
        try:
            raw = base64.b64decode(value["bdata"], validate=True)
            code = "d" if value["dtype"] == "f8" else "f"
            size = struct.calcsize(code)
            if len(raw) % size:
                raise ValueError("binary array length is invalid")
            result = list(struct.unpack(f"<{len(raw) // size}{code}", raw))
        except (KeyError, TypeError, ValueError, struct.error) as exc:
            raise StrategyEvidenceError(f"invalid Plotly binary array: {exc}") from exc
    else:
        raise StrategyEvidenceError("unsupported Plotly trace value encoding")
    if any(not math.isfinite(item) for item in result):
        raise StrategyEvidenceError("strategy trace contains non-finite values")
    return result


def _validate_report_totals_per_instance(
    report: dict[str, Any], traces: dict[str, dict[str, list[Any]]]
) -> dict[str, bool]:
    """Validate each strategy's report total against its trace.
    Returns dict mapping strategy name to whether totals match."""
    metrics = report.get("metrics")
    if not isinstance(metrics, list):
        return {}
    by_name = {row.get("strategy"): row for row in metrics if isinstance(row, dict)}
    result: dict[str, bool] = {}
    for strategy, report_name in _REPORT_STRATEGIES.items():
        row = by_name.get(report_name)
        if not row or row.get("status") != "ok":
            result[strategy] = False
            continue
        raw_total = row.get("total_pnl")
        if not isinstance(raw_total, (int, float)):
            result[strategy] = False
            continue
        if strategy not in traces:
            result[strategy] = False
            continue
        report_total = float(raw_total)
        trace_total = traces[strategy]["values"][-1]
        result[strategy] = math.isclose(report_total, trace_total, rel_tol=1e-10, abs_tol=1e-6)
    return result


def _finite_column(frame: pd.DataFrame, column: str) -> list[float]:
    if column not in frame.columns:
        raise StrategyEvidenceError(f"market data lacks {column}")
    values = [float(value) for value in frame[column]]
    if any(not math.isfinite(value) for value in values):
        raise StrategyEvidenceError(
            f"market data column {column} contains missing values"
        )
    return values


def _daily_baselines(prices: list[float]) -> list[float]:
    points_per_day = TimeConfig.points_per_day
    points_per_week = TimeConfig.points_per_week
    baselines: list[float] = []
    for start in range(0, len(prices), points_per_day):
        current = prices[start : start + points_per_day]
        history = (
            prices[start - points_per_week : start]
            if start >= points_per_week
            else current
        )
        baseline = sum(history) / len(history)
        baselines.extend([baseline] * len(current))
    return baselines


def _increments(cumulative: list[float]) -> list[float]:
    previous = 0.0
    increments: list[float] = []
    for value in cumulative:
        increments.append(value - previous)
        previous = value
    return increments


def _reconstruct_positions(
    increments: list[float],
    prices: list[float],
    baselines: list[float],
    capacity_scale: float,
) -> tuple[list[float | None], list[str]]:
    positions: list[float | None] = []
    states: list[str] = []
    for contribution, price, baseline in zip(
        increments, prices, baselines, strict=True
    ):
        spread = price - baseline
        if abs(spread) < INDETERMINATE_SPREAD_THRESHOLD:
            positions.append(None)
            states.append("indeterminate")
            continue
        position = contribution * 1000.0 / (capacity_scale * spread)
        if not math.isfinite(position) or abs(position) > POSITION_BOUND_TOLERANCE:
            raise StrategyEvidenceError(
                f"reconstructed position {position!r} exceeds the evidence bound"
            )
        if abs(position) < FLAT_POSITION_THRESHOLD:
            state = "approximately_flat"
        elif position > 0:
            state = "long"
        else:
            state = "short"
        positions.append(position)
        states.append(state)
    return positions, states


def _daily_sums(values: list[float]) -> list[float]:
    size = TimeConfig.points_per_day
    return [sum(values[start : start + size]) for start in range(0, len(values), size)]


def _aggregate_daily(
    cumulative: list[float], increments: list[float], positions: list[float | None]
) -> dict[str, list[Any]]:
    size = TimeConfig.points_per_day
    result: dict[str, list[Any]] = {
        "simulated_spread_value": [],
        "cumulative_simulated_spread_value": [],
        "long_periods": [],
        "short_periods": [],
        "approximately_flat_periods": [],
        "indeterminate_periods": [],
        "mean_absolute_position": [],
    }
    for start in range(0, len(increments), size):
        end = start + size
        day_positions = positions[start:end]
        determinate = [value for value in day_positions if value is not None]
        result["simulated_spread_value"].append(sum(increments[start:end]))
        result["cumulative_simulated_spread_value"].append(cumulative[end - 1])
        result["long_periods"].append(
            sum(value >= FLAT_POSITION_THRESHOLD for value in determinate)
        )
        result["short_periods"].append(
            sum(value <= -FLAT_POSITION_THRESHOLD for value in determinate)
        )
        result["approximately_flat_periods"].append(
            sum(abs(value) < FLAT_POSITION_THRESHOLD for value in determinate)
        )
        result["indeterminate_periods"].append(len(day_positions) - len(determinate))
        result["mean_absolute_position"].append(
            sum(abs(value) for value in determinate) / len(determinate)
            if determinate
            else None
        )
    return result


def _build_summary(
    strategy_series: dict[str, dict[str, Any]],
    daily_series: dict[str, dict[str, list[Any]]],
    oracle_total: float,
    valid_strategies: tuple[str, ...],
) -> list[dict[str, Any]]:
    totals = {
        strategy: values["cumulative_simulated_spread_value"][-1]
        for strategy, values in strategy_series.items()
    }
    trend_total = totals.get("trend", 1.0)
    facts = {
        "td3": ["highest_30_day_value", "most_profitable_days"],
        "ppo": [
            "highest_active_positive_rate",
            "smallest_max_drawdown",
            "highest_profit_factor",
        ],
        "sac": ["above_trend_baseline"],
        "trend": ["simple_rule_reference"],
    }
    rows: list[dict[str, Any]] = []
    for strategy in valid_strategies:
        increments = strategy_series[strategy]["simulated_spread_value"]
        cumulative = strategy_series[strategy]["cumulative_simulated_spread_value"]
        positions = strategy_series[strategy]["reconstructed_position"]
        active = [
            index
            for index, value in enumerate(positions)
            if value is not None and abs(value) >= FLAT_POSITION_THRESHOLD
        ]
        positive_active = sum(increments[index] > 0 for index in active)
        positive_sum = sum(value for value in increments if value > 0)
        negative_sum = -sum(value for value in increments if value < 0)
        running_peak = 0.0
        maximum_drawdown = 0.0
        for value in cumulative:
            running_peak = max(running_peak, value)
            maximum_drawdown = max(maximum_drawdown, running_peak - value)
        rows.append(
            {
                "strategy": strategy,
                "simulated_spread_value": totals[strategy],
                "profitable_days": sum(
                    value > 0
                    for value in daily_series[strategy]["simulated_spread_value"]
                ),
                "active_positive_contribution_rate": positive_active / len(active) if active else 0.0,
                "approximately_flat_period_rate": sum(
                    value is not None and abs(value) < FLAT_POSITION_THRESHOLD
                    for value in positions
                )
                / len(positions),
                "max_drawdown": maximum_drawdown,
                "profit_factor": positive_sum / negative_sum if negative_sum else 0.0,
                "trend_multiple": totals[strategy] / trend_total,
                "oracle_capture_rate": totals[strategy] / oracle_total,
                "facts": facts[strategy],
            }
        )
    return rows


def _long_term_evidence(
    report: dict[str, Any], traces: dict[str, dict[str, list[Any]]]
) -> dict[str, Any]:
    totals = {
        strategy: traces[strategy]["values"][-1] for strategy in _EXECUTABLE_STRATEGIES
    }
    leader = max(totals, key=lambda strategy: totals[strategy])
    return {
        "title": "106_day_out_of_sample_stability_evaluation",
        "window": {
            "start": TEST_START,
            "end": TEST_END,
            "timezone": TIMEZONE,
        },
        "training_window": {
            "start": "2024-01-01",
            "end": "2025-09-30",
        },
        "points": TEST_POINTS,
        "cumulative_leader": leader,
        "terminal_simulated_spread_value": totals,
        "source_report": "rl_full_dataset/evaluation_report.json",
        "purpose": "check_whether_30_day_conclusions_persist",
    }


def _validate_snapshot(snapshot: dict[str, Any], valid_strategies: tuple[str, ...]) -> None:
    timeseries = snapshot["timeseries"]
    daily = snapshot["daily"]
    if len(timeseries["timestamps"]) != REPLAY_POINTS:
        raise StrategyEvidenceError("strategy snapshot does not contain 2,880 points")
    if len(daily["dates"]) != 30:
        raise StrategyEvidenceError(
            "strategy snapshot does not contain 30 daily aggregates"
        )
    for row in snapshot["summary"]:
        strategy = row["strategy"]
        if strategy not in valid_strategies:
            continue
        for metric in (
            "simulated_spread_value",
            "active_positive_contribution_rate",
            "max_drawdown",
            "profit_factor",
            "trend_multiple",
            "oracle_capture_rate",
        ):
            value = row.get(metric)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise StrategyEvidenceError(f"{strategy} summary metric {metric} is invalid")
        series = timeseries["strategies"][strategy]
        increments = series["simulated_spread_value"]
        cumulative = series["cumulative_simulated_spread_value"]
        daily_values = daily["strategies"][strategy]["simulated_spread_value"]
        if not math.isclose(
            sum(increments), cumulative[-1], rel_tol=1e-12, abs_tol=1e-6
        ):
            raise StrategyEvidenceError(f"{strategy} increments do not reconcile")
        if not math.isclose(
            sum(daily_values), cumulative[-1], rel_tol=1e-12, abs_tol=1e-6
        ):
            raise StrategyEvidenceError(f"{strategy} daily values do not reconcile")
        if not math.isclose(
            row["simulated_spread_value"], cumulative[-1], rel_tol=1e-12, abs_tol=1e-6
        ):
            raise StrategyEvidenceError(f"{strategy} summary does not reconcile")


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
