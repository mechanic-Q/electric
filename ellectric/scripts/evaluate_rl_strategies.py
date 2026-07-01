#!/usr/bin/env python3
"""
独立评估入口 — 跳过训练，只评估已有 checkpoint + 基线策略。

Usage:
    # Dry-run: 生成空报告
    python -m ellectric.scripts.evaluate_rl_strategies --dry-run

    # 真实评估
    python -m ellectric.scripts.evaluate_rl_strategies

    # 评估部分算法
    python -m ellectric.scripts.evaluate_rl_strategies --algos ppo,sac

Exit codes:
    0  — 成功
    1  — 数据或评估失败
"""
import argparse
import logging
import os
import sys
from pathlib import Path

from ellectric.pipeline.rl_evaluation import (
    EvaluationProtocol,
    StrategyEvaluation,
    compute_strategy_metrics,
    evaluate_baselines,
    evaluate_rl_agents,
    write_evaluation_report,
)
from ellectric.scripts.train_rl_full_dataset import build_datasets, make_env

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="独立评估入口 — 跳过训练，只评估已有 checkpoint + 基线策略",
    )
    parser.add_argument("--train-start", default="2024-01-01")
    parser.add_argument("--train-end", default="2025-09-30")
    parser.add_argument("--test-start", default="2025-10-01")
    parser.add_argument("--test-end", default="2026-01-14")
    parser.add_argument("--algos", default="ppo,sac,td3",
                        help="以逗号分隔的算法列表")
    parser.add_argument("--baselines", default="baseline_persistence,baseline_mean,oracle",
                        help="以逗号分隔的基线策略列表")
    parser.add_argument("--tier", default="tier4", choices=["tier3", "tier4"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--checkpoint-dir", default="models/rl_full_dataset")
    parser.add_argument("--report-dir", default="ellectric/reports/rl_full_dataset")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅生成 metadata 报告，不加载 checkpoint")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    algo_list = [a.strip() for a in args.algos.split(",")]
    baseline_list = [b.strip() for b in args.baselines.split(",")]

    protocol = EvaluationProtocol(
        train_start=args.train_start,
        train_end=args.train_end,
        test_start=args.test_start,
        test_end=args.test_end,
        algos=tuple(algo_list),
        baselines=tuple(baseline_list),
        seed=args.seed,
        tier=args.tier,
        checkpoint_dir=args.checkpoint_dir,
        report_dir=args.report_dir,
    )

    logger.info("dry_run=%s, algos=%s, baselines=%s, tier=%s",
                args.dry_run, algo_list, baseline_list, args.tier)

    if args.dry_run:
        logger.info("DRY-RUN: 生成空评估报告，不加载 checkpoint")
        evals: dict[str, StrategyEvaluation] = {}
        for b in baseline_list:
            evals[b] = StrategyEvaluation(strategy=b, status="skipped")
        for a in algo_list:
            evals[f"rl_{a}"] = StrategyEvaluation(strategy=f"rl_{a}", status="skipped")
        metrics = compute_strategy_metrics(evals)
        paths = write_evaluation_report(protocol, {}, evals, metrics, args.report_dir)
        logger.info("报告已写入: %s", paths)
        return 0

    logger.info("加载数据...")
    try:
        train_load, train_price, test_load, test_price = build_datasets(
            args.train_start, args.train_end, args.test_start, args.test_end,
        )
    except Exception as e:
        logger.error("build_datasets 失败: %s", e)
        return 1

    env_factory = lambda: make_env(test_load, test_price)

    from ellectric.pipeline.backtester import BacktestRunner
    runner = BacktestRunner(env_factory)

    logger.info("评估基线策略...")
    baseline_results = evaluate_baselines(
        runner, baseline_list, test_load, test_price,
        args.test_start, args.test_end,
    )

    logger.info("评估 RL 策略...")
    rl_results = evaluate_rl_agents(
        runner, algo_list, args.checkpoint_dir, test_load, test_price,
        args.test_start, args.test_end,
    )

    all_evaluations = {**baseline_results, **rl_results}
    metrics = compute_strategy_metrics(all_evaluations)

    logger.info("写入报告...")
    paths = write_evaluation_report(protocol, {}, all_evaluations, metrics, args.report_dir)
    logger.info("完成。报告: %s", paths)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    sys.exit(main())
