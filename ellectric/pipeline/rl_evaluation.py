"""
RL 统一对比评估 — 协议与策略结果模型
========================================

本模块定义评估协议与策略结果数据结构，为 baseline/RL 统一评估提供稳定数据契约。

- EvaluationProtocol: 评估配置契约，包含 train/test 窗口、算法/基线列表、路径等。
- StrategyEvaluation: 单个策略评估结果，保存 trade 明细 / error / artifact 路径。

Wave 1 只定义模型，不涉及评估、指标或报告逻辑。

Unified RL evaluation — Protocol & Result Models
=================================================
Defines the evaluation protocol and strategy result data structures that serve as
the stable data contract for unified baseline/RL evaluation.

- EvaluationProtocol: frozen config dataclass — train/test windows, algos/baselines, paths.
- StrategyEvaluation: per-strategy evaluation result — trades / error / artifact_path.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ellectric.pipeline.backtester import BacktestRunner
from ellectric.pipeline.rl_trainer import RLAgentFactory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluationProtocol:
    """评估协议 — 集中描述山东 RL 评估所需配置。

    Attributes:
        train_start: 训练窗口开始日期 (YYYY-MM-DD)。
        train_end: 训练窗口结束日期 (YYYY-MM-DD)。
        test_start: 回测窗口开始日期 (YYYY-MM-DD)。
        test_end: 回测窗口结束日期 (YYYY-MM-DD)。
        algos: 待评估 RL 算法列表。默认 ("ppo", "sac", "td3")。
        baselines: 基线策略列表。默认 ("baseline_persistence", "baseline_mean", "oracle")。
        seed: 随机种子。默认 42。
        timesteps: RL 训练步数。默认 50000。
        tier: 特征等级。默认 "tier4"。
        price_proxy: 价格代理映射。默认 "rt_price->price_da"。
        checkpoint_dir: 模型 checkpoint 目录。默认 "models/rl_full_dataset"。
        report_dir: 报告输出目录。默认 "ellectric/reports/rl_full_dataset"。
    """

    train_start: str
    train_end: str
    test_start: str
    test_end: str
    algos: tuple[str, ...] = ("ppo", "sac", "td3")
    baselines: tuple[str, ...] = ("baseline_persistence", "baseline_mean", "oracle")
    seed: int = 42
    timesteps: int = 50000
    tier: str = "tier4"
    price_proxy: str = "rt_price->price_da"
    checkpoint_dir: str = "models/rl_full_dataset"
    report_dir: str = "ellectric/reports/rl_full_dataset"


@dataclass
class StrategyEvaluation:
    """单个策略评估结果。

    Attributes:
        strategy: 策略名称，如 "rl_ppo", "baseline_persistence", "oracle"。
        status: 状态，可选 "ok", "error", "skipped"。
        trades: 交易明细 DataFrame，含 timestamp / bid_mw / pnl_hourly 等列。
        error: 错误信息（仅 status=error 时）。
        artifact_path: 策略相关 artifact 文件路径（如 checkpoint 或中间数据）。
    """

    strategy: str
    status: str
    trades: pd.DataFrame | None = None
    error: str | None = None
    artifact_path: str | None = None


def evaluate_baselines(
    runner: BacktestRunner,
    baselines: Iterable[str],
    load_data: pd.DataFrame,
    price_data: pd.DataFrame,
    start: str,
    end: str,
) -> dict[str, StrategyEvaluation]:
    """统一评估基线策略 — 遍历 baselines 并隔离单策略失败。

    Iterates over baseline strategies, replays each via BacktestRunner.replay,
    and isolates failures so one broken baseline does not block others.

    Args:
        runner: BacktestRunner 实例。
        baselines: 基线策略名称可迭代对象（如 ("baseline_persistence", "baseline_mean", "oracle")）。
        load_data: 负荷数据 DataFrame（不会被就地修改）。
        price_data: 价格数据 DataFrame（不会被就地修改）。
        start: 回测开始日期 "YYYY-MM-DD"。
        end: 回测结束日期 "YYYY-MM-DD"。

    Returns:
        {strategy_name: StrategyEvaluation} 映射，每项含 status="ok" 或 status="error"。
    """
    results: dict[str, StrategyEvaluation] = {}
    for strategy_name in baselines:
        try:
            trades = runner.replay(
                strategy_name,
                load_data,
                price_data,
                start,
                end,
                strategy_name=strategy_name,
            )
            results[strategy_name] = StrategyEvaluation(
                strategy=strategy_name,
                status="ok",
                trades=trades,
            )
        except Exception as exc:
            logger.warning("基线策略评估失败: %s — %s", strategy_name, exc)
            results[strategy_name] = StrategyEvaluation(
                strategy=strategy_name,
                status="error",
                error=str(exc),
            )
    return results


def evaluate_rl_agents(
    runner: BacktestRunner,
    algos: Iterable[str],
    checkpoint_dir: str,
    load_data: pd.DataFrame,
    price_data: pd.DataFrame,
    start: str,
    end: str,
) -> dict[str, StrategyEvaluation]:
    """统一评估 RL 策略 — 遍历 algos 加载 checkpoint 并 replay，单策略失败不阻断。

    Iterates over RL algorithms, loads each checkpoint via RLAgentFactory.load,
    replays via BacktestRunner.replay, and catches per-agent failures
    (missing checkpoint, load error, replay error) without blocking others.

    Args:
        runner: BacktestRunner 实例。
        algos: 算法名称可迭代对象（如 ("ppo", "sac", "td3")）。
        checkpoint_dir: 模型 checkpoint 目录路径。
        load_data: 负荷数据 DataFrame。
        price_data: 价格数据 DataFrame。
        start: 回测开始日期 "YYYY-MM-DD"。
        end: 回测结束日期 "YYYY-MM-DD"。

    Returns:
        {strategy_name: StrategyEvaluation} 映射，每项含 status="ok" 或 status="error"。
    """
    results: dict[str, StrategyEvaluation] = {}
    for algo in algos:
        strategy_name = f"rl_{algo}"
        ckpt_path = os.path.join(checkpoint_dir, f"{algo}.zip")
        try:
            if not os.path.exists(ckpt_path):
                raise FileNotFoundError(f"checkpoint 不存在: {ckpt_path}")

            agent = RLAgentFactory.load(algo, ckpt_path)
            trades = runner.replay(
                agent,
                load_data,
                price_data,
                start,
                end,
                strategy_name=strategy_name,
            )
            results[strategy_name] = StrategyEvaluation(
                strategy=strategy_name,
                status="ok",
                trades=trades,
                artifact_path=ckpt_path,
            )
            logger.info("RL 策略评估成功: %s", strategy_name)
        except Exception as exc:
            logger.warning("RL 策略评估失败: %s — %s", strategy_name, exc)
            results[strategy_name] = StrategyEvaluation(
                strategy=strategy_name,
                status="error",
                error=str(exc),
                artifact_path=ckpt_path if os.path.exists(ckpt_path) else None,
            )
    return results


def generate_cumulative_pnl_html(
    evaluations: Mapping[str, StrategyEvaluation],
    report_dir: str | Path,
) -> str:
    """从 evaluations 生成累计 P&L 图并写入 report_dir/cumulative_pnl.html.

    Extracts successfully evaluated strategies, calls BacktestRunner.plot_comparison
    to generate a Plotly cumulative P&L figure, and writes it as an HTML file.

    Args:
        evaluations: {strategy_name: StrategyEvaluation} mapping.
        report_dir: Output directory for the HTML file.

    Returns:
        Absolute path to the generated HTML file, or empty string if no
        successful strategies are available.
    """
    ok_results: dict[str, pd.DataFrame] = {}
    for ev in evaluations.values():
        if ev.status == "ok" and ev.trades is not None and not ev.trades.empty:
            ok_results[ev.strategy] = ev.trades

    if not ok_results:
        logger.info("无成功策略，跳过累计 P&L 图")
        return ""

    fig = BacktestRunner.plot_comparison(ok_results)
    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)
    html_path = report_dir / "cumulative_pnl.html"
    fig.write_html(
        str(html_path),
        include_plotlyjs="cdn",
        config={"responsive": True, "displaylogo": False},
    )
    abs_path = str(html_path.resolve())
    logger.info("累计 P&L 图已保存: %s", abs_path)
    return abs_path


def compute_strategy_metrics(
    evaluations: Mapping[str, StrategyEvaluation],
    baseline_name: str = "baseline_persistence",
    oracle_name: str = "oracle",
) -> pd.DataFrame:
    """Compute unified English-column metrics table for strategy comparison.

    Based on StrategyEvaluation results, computes a metrics DataFrame
    with English column names for downstream reporting (JSON/CSV/Markdown).

    Args:
        evaluations: {strategy_name: StrategyEvaluation} mapping.
        baseline_name: Baseline strategy name for baseline_delta.
        oracle_name: Oracle strategy name for oracle_gap.

    Returns:
        DataFrame with columns:
            strategy, total_pnl, sharpe, win_rate, max_drawdown,
            profit_factor, volatility, oracle_gap, baseline_delta, rank, status
    """
    totals: dict[str, float] = {}
    for ev in evaluations.values():
        if ev.status == "ok" and ev.trades is not None and not ev.trades.empty:
            totals[ev.strategy] = float(ev.trades["pnl_hourly"].sum())

    baseline_total = totals.get(baseline_name)
    oracle_total = totals.get(oracle_name)

    rows: list[dict[str, Any]] = []
    for ev in evaluations.values():
        row: dict[str, Any] = {"strategy": ev.strategy, "status": ev.status}

        if ev.status == "ok" and ev.trades is not None and not ev.trades.empty:
            pnl = ev.trades["pnl_hourly"].values.astype(np.float64)
            total_pnl = float(pnl.sum())
            std = float(pnl.std(ddof=0))

            row["total_pnl"] = total_pnl
            row["sharpe"] = float(pnl.mean() / std * np.sqrt(8760)) if std > 1e-10 else 0.0
            row["win_rate"] = float((pnl > 0).mean())

            cum = np.cumsum(pnl)
            peak = np.maximum.accumulate(cum)
            row["max_drawdown"] = float((cum - peak).min())

            pos_sum = pnl[pnl > 0].sum()
            neg_sum = pnl[pnl < 0].sum()
            row["profit_factor"] = float("inf") if neg_sum == 0 else float(pos_sum / abs(neg_sum))

            row["volatility"] = std

            if oracle_total is not None and abs(oracle_total) > 1e-12:
                row["oracle_gap"] = float((oracle_total - total_pnl) / abs(oracle_total))
            else:
                row["oracle_gap"] = float("nan")

            if baseline_total is not None:
                row["baseline_delta"] = float(total_pnl - baseline_total)
            else:
                row["baseline_delta"] = float("nan")
        else:
            for col in (
                "total_pnl", "sharpe", "win_rate", "max_drawdown",
                "profit_factor", "volatility", "oracle_gap", "baseline_delta",
            ):
                row[col] = float("nan")

        rows.append(row)

    columns = [
        "strategy", "total_pnl", "sharpe", "win_rate", "max_drawdown",
        "profit_factor", "volatility", "oracle_gap", "baseline_delta",
        "rank", "status",
    ]
    df = pd.DataFrame(rows, columns=columns)
    df["rank"] = df["total_pnl"].rank(method="min", ascending=False, na_option="keep")
    return df[columns]


def write_evaluation_report(
    protocol: EvaluationProtocol,
    training: Mapping[str, dict],
    evaluations: Mapping[str, StrategyEvaluation],
    metrics: pd.DataFrame,
    report_dir: str | Path = "ellectric/reports/rl_full_dataset",
    cumulative_pnl_html_path: str = "",
) -> dict[str, str]:
    """Write evaluation results to JSON, CSV, and Markdown files.

    Produces three files in *report_dir*:
    - evaluation_report.json   — machine-readable full result
    - evaluation_metrics.csv   — metrics table (header-only when empty)
    - evaluation_report.md     — human-readable report with rankings & diagnosis

    Uses atomic writes (``.tmp`` + ``os.replace``) to avoid partial output.
    Does not touch any ``training_report.*`` files in the same directory.

    Args:
        protocol: The evaluation protocol (config contract).
        training: Per-algo training results dict, e.g. ``{"ppo": {"status": "ok", ...}}``.
        evaluations: Per-strategy evaluation results from
            :func:`evaluate_baselines` / :func:`evaluate_rl_agents`.
        metrics: Metrics DataFrame from :func:`compute_strategy_metrics`.
        report_dir: Output directory. Defaults to ``ellectric/reports/rl_full_dataset``.
        cumulative_pnl_html_path: Optional path to pre-generated cumulative P&L HTML.

    Returns:
        ``{"json_path": str, "csv_path": str, "md_path": str}`` — absolute paths.
    """
    import datetime
    import json
    import subprocess
    from pathlib import Path

    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    # Auto-generate cumulative P&L chart when not provided
    if not cumulative_pnl_html_path:
        cumulative_pnl_html_path = generate_cumulative_pnl_html(evaluations, report_dir)

    # Git SHA
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, timeout=5,
        ).decode().strip()
    except Exception:
        sha = "unknown"

    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    json_path = report_dir / "evaluation_report.json"
    csv_path = report_dir / "evaluation_metrics.csv"
    md_path = report_dir / "evaluation_report.md"

    # --- Build evaluations JSON-friendly dict ---
    evals_json: dict[str, dict] = {}
    for name, ev in evaluations.items():
        evals_json[name] = {
            "strategy": ev.strategy,
            "status": ev.status,
            "error": ev.error,
            "artifact_path": ev.artifact_path,
        }

    # --- Metrics rows ---
    metrics_list: list[dict[str, Any]] = []
    if not metrics.empty:
        metrics_list = metrics.to_dict(orient="records")

    # Recursive NaN/inf → null pre-processing for valid JSON
    def _clean(val: Any) -> Any:
        if isinstance(val, float):
            return None if (np.isnan(val) or np.isinf(val)) else val
        if isinstance(val, dict):
            return {k: _clean(v) for k, v in val.items()}
        if isinstance(val, list):
            return [_clean(v) for v in val]
        return val

    report = {
        "metadata": {
            "generated_at": generated_at,
            "git_sha": sha,
            "protocol_summary": {
                "train_start": protocol.train_start,
                "train_end": protocol.train_end,
                "test_start": protocol.test_start,
                "test_end": protocol.test_end,
                "algos": list(protocol.algos),
                "baselines": list(protocol.baselines),
                "seed": protocol.seed,
                "timesteps": protocol.timesteps,
                "tier": protocol.tier,
                "price_proxy": protocol.price_proxy,
            },
        },
        "protocol": {
            "train_start": protocol.train_start,
            "train_end": protocol.train_end,
            "test_start": protocol.test_start,
            "test_end": protocol.test_end,
            "algos": list(protocol.algos),
            "baselines": list(protocol.baselines),
            "seed": protocol.seed,
            "timesteps": protocol.timesteps,
            "tier": protocol.tier,
            "price_proxy": protocol.price_proxy,
            "checkpoint_dir": protocol.checkpoint_dir,
            "report_dir": protocol.report_dir,
        },
        "training": dict(training),
        "evaluations": evals_json,
        "metrics": _clean(metrics_list),
        "artifacts": {
            "json_path": str(json_path.resolve()),
            "csv_path": str(csv_path.resolve()),
            "md_path": str(md_path.resolve()),
            "cumulative_pnl_html": cumulative_pnl_html_path or "",
        },
    }

    # --- Write JSON (atomic) ---
    tmp_json = report_dir / ".evaluation_report.json.tmp"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(_clean(report), f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp_json, json_path)

    # --- Write CSV (atomic) ---
    tmp_csv = report_dir / ".evaluation_metrics.csv.tmp"
    if not metrics.empty:
        metrics.to_csv(tmp_csv, index=False)
    else:
        if not metrics.columns.empty:
            col_names = list(metrics.columns)
        else:
            col_names = [
                "strategy", "total_pnl", "sharpe", "win_rate", "max_drawdown",
                "profit_factor", "volatility", "oracle_gap", "baseline_delta",
                "rank", "status",
            ]
        with open(tmp_csv, "w", encoding="utf-8") as f:
            f.write(",".join(col_names) + "\n")
    os.replace(tmp_csv, csv_path)

    # --- Write Markdown (atomic) ---
    tmp_md = report_dir / ".evaluation_report.md.tmp"
    lines: list[str] = []
    lines.append("# Evaluation Report\n\n")
    lines.append(f"- **generated_at**: {generated_at}\n")
    lines.append(f"- **git_sha**: {sha}\n\n")

    lines.append("## Protocol\n\n")
    lines.append("| Parameter | Value |\n|---|---|\n")
    for k, v in (
        ("train_start", protocol.train_start),
        ("train_end", protocol.train_end),
        ("test_start", protocol.test_start),
        ("test_end", protocol.test_end),
        ("algos", ", ".join(protocol.algos)),
        ("baselines", ", ".join(protocol.baselines)),
        ("seed", str(protocol.seed)),
        ("timesteps", str(protocol.timesteps)),
        ("tier", protocol.tier),
        ("price_proxy", protocol.price_proxy),
        ("checkpoint_dir", protocol.checkpoint_dir),
        ("report_dir", protocol.report_dir),
    ):
        lines.append(f"| {k} | {v} |\n")

    lines.append("\n## Training\n\n")
    if training:
        keys = ["algo", "status", "final_reward", "duration_s", "error"]
        lines.append("| " + " | ".join(keys) + " |\n")
        lines.append("| " + " | ".join(["---"] * len(keys)) + " |\n")
        for algo, info in training.items():
            status = info.get("status", "N/A")
            reward = info.get("final_reward", "N/A")
            dur = info.get("duration_s", "N/A")
            err = info.get("error", "") or ""
            lines.append(f"| {algo} | {status} | {reward} | {dur} | {err} |\n")
    else:
        lines.append("_No training results._\n")

    lines.append("\n## Rankings\n\n")
    if not metrics.empty:
        sorted_m = metrics.sort_values("rank", na_position="last")
        cols = list(sorted_m.columns)
        lines.append("| " + " | ".join(cols) + " |\n")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |\n")
        for _, row in sorted_m.iterrows():
            vs = [str(row[c]) if pd.notna(row[c]) else "" for c in cols]
            lines.append("| " + " | ".join(vs) + " |\n")
    else:
        lines.append("_No strategies evaluated._\n")

    lines.append("\n## Failure Diagnosis\n\n")
    failures = [(n, e) for n, e in evaluations.items() if e.status != "ok"]
    if failures:
        lines.append("| strategy | status | error |\n")
        lines.append("|---|---|---|\n")
        for name, ev in failures:
            lines.append(f"| {name} | {ev.status} | {ev.error or ''} |\n")
    else:
        lines.append("_All strategies completed successfully._\n")

    lines.append("\n## Artifacts\n\n")
    for label, key in (
        ("Evaluation Report (JSON)", "json_path"),
        ("Evaluation Metrics (CSV)", "csv_path"),
        ("Evaluation Report (Markdown)", "md_path"),
        ("Cumulative P&L (HTML)", "cumulative_pnl_html"),
    ):
        lines.append(f"- **{label}**: {report['artifacts'][key]}\n")

    with open(tmp_md, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp_md, md_path)

    return {
        "json_path": str(json_path.resolve()),
        "csv_path": str(csv_path.resolve()),
        "md_path": str(md_path.resolve()),
    }


__all__ = [
    "EvaluationProtocol",
    "StrategyEvaluation",
    "evaluate_baselines",
    "evaluate_rl_agents",
    "compute_strategy_metrics",
    "generate_cumulative_pnl_html",
    "write_evaluation_report",
]
