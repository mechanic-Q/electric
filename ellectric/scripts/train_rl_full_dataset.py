#!/usr/bin/env python3
"""
完整 96 维 RL full dataset 训练 — 山东 15min 数据 PPO/SAC/TD3 端到端训练 + 回测 + 报告

Usage:
    # Dry-run smoke test (装配验证，不调 sb3)
    python -m ellectric.scripts.train_rl_full_dataset --dry-run

    # 默认：PPO+SAC+TD3 各 50k steps
    python -m ellectric.scripts.train_rl_full_dataset

    # 单算法 + 更短训练
    python -m ellectric.scripts.train_rl_full_dataset --algos ppo --timesteps 10000

Exit codes:
    0  — 成功
    1  — 数据或特征装配失败
    2  — 报告写入失败
"""
import argparse
import importlib.util
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd

from ellectric.pipeline.data_loader import create_loader

logger = logging.getLogger(__name__)

PRICE_PROXY = "rt_price->price_da"
DEFAULT_WEATHER_CACHE = "ellectric/data/shandong/weather_2024-2026.parquet"


def build_datasets(
    train_start: str, train_end: str, test_start: str, test_end: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """返回 (train_load, train_price, test_load, test_price)."""
    df = create_loader("shandong").load_data()

    required = {"timestamp", "load_mw", "rt_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"ShandongDataLoader 缺少列: {missing}")

    df = df.copy()
    df["rt_price"] = df["rt_price"].bfill().ffill()
    if df["rt_price"].isna().any():
        raise ValueError("rt_price 仍有 null，数据不完整")

    price_df = df[["timestamp", "rt_price", "is_holiday", "is_weekend"]].copy()
    price_df = price_df.rename(columns={"rt_price": "price_da"})

    load_df = df[["timestamp", "load_mw"]].copy()

    _validate_range(load_df, train_start, train_end, test_start, test_end)

    train_load = load_df[(load_df["timestamp"] >= train_start)
                         & (load_df["timestamp"] < train_end)].reset_index(drop=True)
    test_load = load_df[(load_df["timestamp"] >= test_start)
                        & (load_df["timestamp"] < test_end)].reset_index(drop=True)
    train_price = price_df[(price_df["timestamp"] >= train_start)
                           & (price_df["timestamp"] < train_end)].reset_index(drop=True)
    test_price = price_df[(price_df["timestamp"] >= test_start)
                          & (price_df["timestamp"] < test_end)].reset_index(drop=True)

    if train_load.empty or train_price.empty:
        raise ValueError(f"训练窗口 [{train_start}, {train_end}) 无数据")
    if test_load.empty or test_price.empty:
        raise ValueError(f"回测窗口 [{test_start}, {test_end}) 无数据")

    return train_load, train_price, test_load, test_price


def _validate_range(load_df, train_start, train_end, test_start, test_end):
    ts = pd.to_datetime(load_df["timestamp"])
    data_min = ts.min()
    data_max = ts.max()
    errors = []
    if train_start < str(data_min.date()):
        errors.append(f"train_start {train_start} 早于数据起始 {data_min.date()}")
    if test_end > str(data_max.date()):
        errors.append(f"test_end {test_end} 晚于数据结束 {data_max.date()}")
    if train_end > test_start:
        errors.append(f"训练窗口结束 {train_end} 应早于回测窗口开始 {test_start}")
    if errors:
        raise ValueError("; ".join(errors))


def build_features(
    load_df: pd.DataFrame, price_df: pd.DataFrame, tier: str = "tier4",
    weather_cache_path: str | None = None,
) -> tuple[object | None, object | None, list[str], str]:
    """返回 (xgb_forecaster, lear_forecaster, feature_cols, weather_source)."""
    from ellectric.pipeline.features import prepare_features, FeatureEngineer
    from ellectric.pipeline.forecaster import XGBoostForecaster
    from ellectric.pipeline.price_forecaster import LEARForecaster

    tier_list = ["tier1", "tier2", "tier3"]
    weather_source = "skipped"
    if tier == "tier4":
        weather_source = _detect_weather_source(weather_cache_path)
        tier_list = ["tier1", "tier2", "tier3", "tier4"]

    feature_df = prepare_features(
        load_df, tiers=tier_list,
        weather_cache_path=weather_cache_path,
        fetch_if_missing=False,
    )

    engineer = FeatureEngineer()
    _ = engineer.add_tier1_features(load_df.head(1))
    feat_cols = engineer.get_feature_columns(tier)

    if weather_source in ("skipped", "degraded"):
        available = [c for c in feat_cols if c in feature_df.columns]
    else:
        available = [c for c in feat_cols if c in feature_df.columns]

    lf = pf = None
    try:
        lf = XGBoostForecaster(n_estimators=200, max_depth=6)
        train_feat = feature_df[available].dropna()
        train_target = load_df["load_mw"].loc[train_feat.index]
        lf.train_evaluate(train_feat, train_target, n_splits=3, gap=96)
    except Exception as e:
        logger.warning("XGBoost 训练失败，env 将使用 persistence 预测: %s", e)
        lf = None

    try:
        pf = LEARForecaster(alpha=0.05)
        pdf = pf.add_price_features(price_df, "tier1")
        train_pdf = pdf.dropna()
        pf.train_evaluate(train_pdf, "tier1", n_splits=3, gap=96)
    except Exception as e:
        logger.warning("LEAR 训练失败，env 将使用 persistence 预测: %s", e)
        pf = None

    return lf, pf, available, weather_source


def _detect_weather_source(weather_cache_path: str | None) -> str:
    from ellectric.pipeline.features import _resolve_weather_cache
    cache = _resolve_weather_cache(weather_cache_path)
    if cache.exists():
        logger.info("weather cache 命中: %s", cache)
        return "cache"
    logger.info("weather cache 缺失(%s)，降级到 Tier3", cache)
    return "degraded"


def make_env(
    load_df: pd.DataFrame, price_df: pd.DataFrame,
    load_forecaster=None, price_forecaster=None,
):
    """返回 ElectricityMarketEnv 实例."""
    from ellectric.pipeline.trading_env import ElectricityMarketEnv

    max_capacity = float(load_df["load_mw"].max())
    env = ElectricityMarketEnv(
        load_data=load_df,
        price_data=price_df,
        load_forecaster=load_forecaster,
        price_forecaster=price_forecaster,
        initial_cash=0.0,
        max_capacity=max_capacity,
        reward_fn="profit_only",
    )
    return env


def train_one(algo: str, env, *, timesteps: int, seed: int,
              log_dir: str, ckpt_path: str) -> dict:
    """返回 {status, final_reward, duration_s, checkpoint_path, tb_log_path, error}."""
    from ellectric.pipeline.rl_trainer import RLAgentFactory

    os.makedirs(os.path.dirname(ckpt_path), exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    result: dict = {
        "algo": algo,
        "status": "ok",
        "final_reward": None,
        "duration_s": None,
        "checkpoint_path": ckpt_path,
        "tb_log_path": log_dir,
        "error": None,
    }

    try:
        t0 = time.monotonic()
        if importlib.util.find_spec("tensorboard") is not None:
            tb_log = log_dir
        else:
            logger.warning("%s: tensorboard 未安装，跳过 TensorBoard 日志（pip install tensorboard 可启用）",
                           algo.upper())
            tb_log = None
        agent = RLAgentFactory.create(
            algo, env, tensorboard_log=tb_log, seed=seed,
        )
        train_result = agent.train(total_timesteps=timesteps)
        agent.save(ckpt_path)
        duration = time.monotonic() - t0

        result["final_reward"] = float(train_result.get("final_reward", 0.0))
        result["duration_s"] = round(duration, 1)
        logger.info("%s 训练完成: %d steps, %.1fs, reward=%.2f",
                    algo.upper(), timesteps, duration, result["final_reward"])
    except Exception as e:
        logger.error("%s 训练异常: %s", algo.upper(), e)
        result["status"] = "error"
        result["error"] = str(e)
        result["final_reward"] = None
        result["duration_s"] = None
        result["checkpoint_path"] = None

    return result


def run_backtest(
    train_results: dict, test_load: pd.DataFrame, test_price: pd.DataFrame,
    *, test_start: str, test_end: str, checkpoint_dir: str, report_dir: str,
) -> dict:
    """返回 {metrics: list[dict], cumulative_pnl_html_path: str}."""
    from ellectric.pipeline.backtester import BacktestRunner, SUPPORTED_STRATEGIES
    from ellectric.pipeline.rl_trainer import RLAgentFactory

    env_factory = lambda: make_env(test_load, test_price)
    runner = BacktestRunner(env_factory)
    results: dict[str, pd.DataFrame] = {}

    for s in SUPPORTED_STRATEGIES:
        try:
            df = runner.replay(s, test_load, test_price, test_start, test_end,
                               strategy_name=s)
            results[s] = df
            logger.info("基线 %s 回测完成: %d 条记录", s, len(df))
        except Exception as e:
            logger.warning("基线 %s 回测失败: %s", s, e)

    for algo, info in train_results.items():
        if info.get("status") == "ok":
            ckpt = os.path.join(checkpoint_dir, f"{algo}.zip")
            try:
                agent = RLAgentFactory.load(algo, ckpt)
                if hasattr(agent, "_trained"):
                    agent._trained = True
                df = runner.replay(agent, test_load, test_price, test_start, test_end,
                                   strategy_name=f"rl_{algo}")
                results[f"rl_{algo}"] = df
                logger.info("RL %s 回测完成: %d 条记录", algo, len(df))
            except Exception as e:
                logger.warning("RL %s 回测失败: %s", algo, e)
        else:
            logger.info("跳过 %s 回测（训练未成功）", algo)

    metrics_list = []
    cumulative_pnl_html = ""
    if results:
        try:
            metrics_df = runner.compare(results)
            metrics_list = metrics_df.to_dict(orient="records")

            fig = runner.plot_comparison(results)
            html_path = os.path.join(report_dir, "cumulative_pnl.html")
            os.makedirs(report_dir, exist_ok=True)
            fig.write_html(html_path, include_plotlyjs="cdn",
                           config={"responsive": True, "displaylogo": False})
            cumulative_pnl_html = html_path
            logger.info("累计 P&L 图已保存: %s", html_path)
        except Exception as e:
            logger.warning("回测对比/绘图失败: %s", e)

    return {"metrics": metrics_list, "cumulative_pnl_html_path": cumulative_pnl_html}


def write_reports(report: dict, report_dir: str | Path) -> tuple[str, str]:
    """返回 (json_path, md_path)."""
    import datetime
    import json

    report_dir = Path(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    report.setdefault("metadata", {})
    report.setdefault("training", {})
    report.setdefault("backtest", {"metrics": [], "cumulative_pnl_html_path": ""})
    report.setdefault("interpretation", {})

    report["metadata"]["generated_at"] = datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    json_path = report_dir / "training_report.json"
    tmp_json = report_dir / ".training_report.json.tmp"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp_json, json_path)

    md_lines = _render_markdown(report)
    md_path = report_dir / "training_report.md"
    tmp_md = report_dir / ".training_report.md.tmp"
    with open(tmp_md, "w", encoding="utf-8") as f:
        f.writelines(md_lines)
    os.replace(tmp_md, md_path)

    return str(json_path.resolve()), str(md_path.resolve())


def _render_markdown(report: dict) -> list[str]:
    meta = report.get("metadata", {})
    training = report.get("training", {})
    backtest = report.get("backtest", {})
    interpret = report.get("interpretation", {})

    lines: list[str] = []
    lines.append("# RL Full Dataset 训练报告\n\n")

    lines.append("## Metadata\n\n")
    lines.append("| 字段 | 值 |\n|---|---|\n")
    for k, v in meta.items():
        lines.append(f"| {k} | {v} |\n")

    lines.append("\n## Training\n\n")
    lines.append("| 算法 | 状态 | final_reward | duration_s | checkpoint_path |\n")
    lines.append("|---|---|---|---|---|\n")
    for algo, info in training.items():
        status = info.get("status", "N/A")
        reward = info.get("final_reward", "N/A")
        dur = info.get("duration_s", "N/A")
        ckpt = info.get("checkpoint_path", "N/A")
        lines.append(f"| {algo} | {status} | {reward} | {dur} | {ckpt} |\n")
        if info.get("error"):
            lines.append(f"\n> ⚠️ {algo} 异常: {info['error']}\n")

    lines.append("\n## Backtest\n\n")
    metrics = backtest.get("metrics", [])
    if metrics:
        keys = list(metrics[0].keys())
        header = "| " + " | ".join(keys) + " |\n"
        sep = "| " + " | ".join(["---"] * len(keys)) + " |\n"
        lines.append(header)
        lines.append(sep)
        for row in metrics:
            vals = [str(row.get(k, "")) for k in keys]
            lines.append("| " + " | ".join(vals) + " |\n")
    else:
        lines.append("_无回测结果_\n")

    pnl = backtest.get("cumulative_pnl_html_path", "")
    if pnl:
        lines.append(f"\n累计 P&L 图: [{pnl}]({pnl})\n")

    lines.append("\n## Interpretation\n\n")
    lines.append(f"- **hard_threshold_applied**: {interpret.get('hard_threshold_applied', False)}\n")
    lines.append(f"- **summary**: {interpret.get('summary', '')}\n")

    return lines


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="完整 96 维 RL full dataset 训练 — 山东 15min",
    )
    parser.add_argument("--train-start", default="2024-01-01")
    parser.add_argument("--train-end", default="2025-09-30")
    parser.add_argument("--test-start", default="2025-10-01")
    parser.add_argument("--test-end", default="2026-01-14")
    parser.add_argument("--timesteps", type=int, default=50000)
    parser.add_argument("--algos", default="ppo,sac,td3",
                        help="以逗号分隔的算法列表")
    parser.add_argument("--tier", default="tier4", choices=["tier3", "tier4"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report-dir", default="ellectric/reports/rl_full_dataset")
    parser.add_argument("--checkpoint-dir", default="models/rl_full_dataset")
    parser.add_argument("--tb-log-root", default="tb_logs")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅装配 smoke，不调 .learn()")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    algo_list = [a.strip() for a in args.algos.split(",")]

    logger.info("Dry-run=%s, algos=%s, timesteps=%d, tier=%s, seed=%d",
                args.dry_run, algo_list, args.timesteps, args.tier, args.seed)

    if args.dry_run:
        logger.info("DRY-RUN: 装配 smoke — 不调 sb3 .learn(), 不跑 backtest")
        logger.info("数据: ShandongDataLoader + rt_price→price_da 价格代理")
        logger.info("特征: Tier=%s, weather_cache=%s", args.tier, DEFAULT_WEATHER_CACHE)
        logger.info("窗口: train [%s, %s], test [%s, %s]",
                    args.train_start, args.train_end, args.test_start, args.test_end)
        report = {
            "metadata": _build_metadata(args, algo_list),
            "training": {a: {"status": "skipped"} for a in algo_list},
            "backtest": {"metrics": [], "cumulative_pnl_html_path": ""},
            "interpretation": {"hard_threshold_applied": False,
                               "summary": "DRY-RUN — 未执行真实训练与回测"},
        }
        report["metadata"]["price_proxy"] = PRICE_PROXY
        report["metadata"]["reward_fn"] = "profit_only"
        try:
            write_reports(report, args.report_dir)
        except Exception as e:
            logger.error("dry-run 报告写入失败: %s", e)
            return 2
        return 0

    logger.info("开始 build_datasets...")
    try:
        train_load, train_price, test_load, test_price = build_datasets(
            args.train_start, args.train_end, args.test_start, args.test_end,
        )
    except Exception as e:
        logger.error("build_datasets 失败: %s", e)
        return 1

    logger.info("开始 build_features...")
    try:
        lf, pf, feat_cols, weather_source = build_features(
            train_load, train_price, tier=args.tier,
        )
    except Exception as e:
        logger.error("build_features 失败: %s", e)
        return 1

    train_env = make_env(train_load, train_price, lf, pf)
    logger.info("训练环境就绪: action_space=%s, obs_keys=%s",
                train_env.action_space.shape, list(train_env.observation_space.keys()))

    training: dict[str, dict] = {}
    for algo in algo_list:
        ckpt = os.path.join(args.checkpoint_dir, f"{algo}.zip")
        tb_log = os.path.join(args.tb_log_root, f"rl_full_dataset_{algo}")
        training[algo] = train_one(
            algo, train_env, timesteps=args.timesteps, seed=args.seed,
            log_dir=tb_log, ckpt_path=ckpt,
        )

    logger.info("开始回测...")
    bt_results = run_backtest(
        training, test_load, test_price,
        test_start=args.test_start, test_end=args.test_end,
        checkpoint_dir=args.checkpoint_dir, report_dir=args.report_dir,
    )

    report = {
        "metadata": _build_metadata(args, algo_list),
        "training": training,
        "backtest": bt_results,
        "interpretation": _build_interpretation(training, bt_results, algo_list),
    }
    report["metadata"]["weather_source"] = weather_source
    report["metadata"]["price_proxy"] = PRICE_PROXY
    report["metadata"]["reward_fn"] = "profit_only"
    report["metadata"]["train_max_capacity_mw"] = float(train_load["load_mw"].max())
    report["metadata"]["test_max_capacity_mw"] = float(test_load["load_mw"].max())

    logger.info("写入报告...")
    try:
        write_reports(report, args.report_dir)
    except Exception as e:
        logger.error("报告写入失败: %s", e)
        return 2

    logger.info("✅ 完成。报告: %s/training_report.{json,md}", args.report_dir)
    return 0


def _build_metadata(args: argparse.Namespace, algo_list: list[str]) -> dict:
    from ellectric.config import TimeConfig
    import datetime
    try:
        import subprocess
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, timeout=5,
        ).decode().strip()
    except Exception:
        sha = "unknown"
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": sha,
        "time_config": {"freq": "15min", "points_per_day": TimeConfig.points_per_day},
        "seed": args.seed,
        "algos": algo_list,
        "timesteps_per_algo": args.timesteps,
        "train_range": [args.train_start, args.train_end],
        "test_range": [args.test_start, args.test_end],
        "tier": args.tier,
        "price_proxy": PRICE_PROXY,
        "reward_fn": "profit_only",
    }


def _build_interpretation(
    training: dict, bt_results: dict, algo_list: list[str],
) -> dict:
    ok_algos = [a for a, v in training.items() if v.get("status") == "ok"]
    metrics = bt_results.get("metrics", [])
    best = ""
    if metrics:
        def _strat(m):
            return m.get("strategy") or m.get("策略", "")
        def _ret(m):
            v = m.get("total_return", m.get("总收益"))
            try:
                return float(v) if v is not None else -float("inf")
            except (TypeError, ValueError):
                return -float("inf")
        best = _strat(max(metrics, key=_ret))
    summary = (
        f"成功 {len(ok_algos)}/{len(algo_list)} 算法训练完成。"
        f"最佳策略: {best}。"
    )
    return {"hard_threshold_applied": False, "summary": summary}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    sys.exit(main())
