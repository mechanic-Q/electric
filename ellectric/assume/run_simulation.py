#!/usr/bin/env python3
"""
ASSUME 7-day simulation runner for Chinese provincial market.

Usage:
    python run_simulation.py --config configs/assume_china_config.yaml [--output <dir>] [--seed <n>]

Outputs (4 files):
    clearing_prices.csv  — hourly clearing prices
    dispatch.csv         — generation dispatch per unit
    agent_profits.csv    — cumulative profit per agent
    simulation_metadata.json — config summary, runtime, status
"""

import argparse
import hashlib
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_simulation")

HAS_ASSUME = False
try:
    from assume import World  # noqa: F401
    HAS_ASSUME = True
except ImportError:
    pass

INTERRUPTED = False


def _signal_handler(signum: int, frame: Any) -> None:
    global INTERRUPTED
    if INTERRUPTED:
        logger.warning("Force exit...")
        sys.exit(1)
    INTERRUPTED = True
    logger.warning("Interrupt received — saving partial results...")


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ASSUME 7-day simulation with Chinese provincial market config."
    )
    parser.add_argument(
        "--config", required=True, type=str, help="Path to YAML config file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: outputs/simulations/<timestamp>)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    return parser.parse_args()


def resolve_output_dir(base: str | None) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if base is None:
        base = f"outputs/simulations/{ts}"
    candidate = Path(base)
    if candidate.exists():
        suffix = 1
        while True:
            candidate = Path(f"{base}_{suffix:03d}")
            if not candidate.exists():
                break
            suffix += 1
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        raw = f.read()
    try:
        config = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        lines = raw.split("\n")
        if hasattr(e, "problem_mark") and e.problem_mark is not None:
            lineno = e.problem_mark.line + 1
            context = "\n".join(lines[max(0, lineno - 3) : lineno + 2])
            logger.error("YAML syntax error at line %d:\n%s", lineno, context)
        else:
            logger.error("YAML parse error: %s", e)
        raise

    required_keys = ["market", "generation_mix", "demand", "agents", "simulation"]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {missing}")

    for fuel in config["generation_mix"].values():
        if "capacity_mw" not in fuel or "marginal_cost" not in fuel:
            raise KeyError(f"generation_mix entry missing 'capacity_mw' or 'marginal_cost': {fuel}")

    return config


def _build_units(config: dict, rng: np.random.Generator) -> list[dict]:
    units = []
    for fuel_type, params in config["generation_mix"].items():
        n_units = max(1, int(params["capacity_mw"] // 1000))
        unit_capacity = params["capacity_mw"] / n_units
        for i in range(n_units):
            cost_noise = rng.uniform(-5, 5)
            units.append({
                "name": f"{fuel_type}_{i + 1}",
                "fuel_type": fuel_type,
                "capacity_mw": unit_capacity,
                "marginal_cost": max(0, params["marginal_cost"] + cost_noise),
            })
    units.sort(key=lambda u: u["marginal_cost"])
    return units


def _generate_hourly_demand(
    config: dict, timestamps: pd.DatetimeIndex, rng: np.random.Generator
) -> np.ndarray:
    base_demand = config["demand"]["total_demand_mw"]
    # Diurnal profile: peak ~14:00-16:00, trough ~03:00-05:00
    hour = timestamps.hour.to_numpy()
    # Sine wave: peak at hour 15 (hour 15 = 15/24*2pi = ~3.93 rad)
    diurnal_factor = 0.5 + 0.5 * np.sin((hour - 3) * 2 * np.pi / 24)
    diurnal_factor = 0.75 + 0.25 * diurnal_factor  # range [0.75, 1.0] of base
    demand = base_demand * diurnal_factor
    # Add small noise
    noise = rng.normal(0, base_demand * 0.01, size=len(timestamps))
    demand = demand + noise
    return demand


def _merit_order_dispatch(
    units: list[dict],
    demand: np.ndarray,
    price_limits: dict,
    rng: np.random.Generator,
    timestamps: pd.DatetimeIndex,
) -> tuple:
    n_hours = len(demand)
    price_series = np.full(n_hours, np.nan)
    dispatch_records = []
    profit_records = []
    renewable_types = {"wind", "solar"}

    total_dispatch = np.zeros(n_hours)
    renewable_dispatch = np.zeros(n_hours)

    max_unit_capacity = max(u["capacity_mw"] for u in units)
    # Must-run generation (wind/solar get dispatched first)
    must_run = [u for u in units if u["fuel_type"] in renewable_types]
    thermal = [u for u in units if u["fuel_type"] not in renewable_types]

    for h in range(n_hours):
        hour_of_day = timestamps[h].hour
        remaining = demand[h]
        hour_dispatch = []
        cleared_price = price_limits["min"]

        # Dispatch must-run first (wind/solar at near-zero marginal cost)
        for u in must_run:
            avail = u["capacity_mw"] * rng.uniform(0.3, 0.9)
            dispatch = min(avail, remaining)
            if dispatch > 0:
                remaining -= dispatch
                hour_dispatch.append((u["name"], u["fuel_type"], dispatch))
                renewable_dispatch[h] += dispatch
                if remaining <= 0:
                    break

        if remaining > 0:
            # Dispatch thermal in merit order
            for u in thermal:
                if remaining <= 0:
                    break
                dispatch = min(u["capacity_mw"], remaining)
                remaining -= dispatch
                hour_dispatch.append((u["name"], u["fuel_type"], dispatch))
                cleared_price = u["marginal_cost"]

        # Check if demand was met
        if remaining > 0:
            cleared_price = price_limits["max"]
            logger.warning("Hour %s: demand not fully met (shortfall %.0f MW)", timestamps[h], remaining)

        # Enforce price limits
        cleared_price = max(price_limits["min"], min(price_limits["max"], cleared_price))
        price_series[h] = cleared_price
        total_dispatch[h] = demand[h] - remaining

        for name, fuel_type, d in hour_dispatch:
            dispatch_records.append({
                "timestamp": timestamps[h],
                "unit": name,
                "dispatch_mw": round(d, 2),
                "fuel_type": fuel_type,
            })

    # Compute agent profits
    agent_configs = config.get("agents", [{"type": "naive"}])
    agent_strategies = {
        "learning": "PPO",
        "naive": "marginal_cost",
        "strategic": "strategic",
    }

    # Dispatch by fuel type per hour
    dispatch_df = pd.DataFrame(dispatch_records)
    if len(dispatch_df) > 0:
        hourly_by_fuel = (
            dispatch_df.groupby(["timestamp", "fuel_type"])["dispatch_mw"].sum().reset_index()
        )
    else:
        hourly_by_fuel = pd.DataFrame(columns=["timestamp", "fuel_type", "dispatch_mw"])

    for agent_cfg in agent_configs:
        agent_type = agent_cfg["type"]
        strategy = agent_strategies.get(agent_type, "unknown")
        markup = 1.0
        if agent_type == "learning":
            markup = rng.uniform(0.95, 1.15)
        elif agent_type == "strategic":
            markup = rng.uniform(1.05, 1.25)

        for h in range(n_hours):
            # Distribute dispatch to agents proportionally
            total_gen = total_dispatch[h]
            agent_share = total_gen / len(agent_configs)
            agent_cost = 150  # average marginal cost
            if len(dispatch_df) > 0:
                hour_fuel = hourly_by_fuel[
                    hourly_by_fuel["timestamp"] == timestamps[h]
                ]
                if len(hour_fuel) > 0:
                    avg_cost = np.average(
                        [u["marginal_cost"] for u in units if u["fuel_type"] in hour_fuel["fuel_type"].values],
                        weights=hour_fuel["dispatch_mw"].values[:1] if len(hour_fuel) > 0 else [1],
                    ) if len(hour_fuel) > 0 else 150
                    agent_cost = avg_cost if not np.isnan(avg_cost) else 150

            revenue = agent_share * price_series[h] * markup
            cost = agent_share * agent_cost
            profit = revenue - cost
            profit_records.append({
                "timestamp": timestamps[h],
                "agent": agent_type,
                "profit_元": round(profit, 2),
                "strategy": strategy,
            })

    return price_series, dispatch_records, profit_records, renewable_dispatch


def run_builtin_simulation(
    config: dict, output_dir: Path, seed: int
) -> dict:
    start_time = datetime(2023, 7, 1, 0, 0, 0)
    duration_days = config["simulation"]["duration_days"]
    end_time = start_time + timedelta(days=duration_days)
    timestamps = pd.date_range(start=start_time, end=end_time, freq="h", inclusive="left")

    rng = np.random.default_rng(seed)
    units = _build_units(config, rng)
    demand = _generate_hourly_demand(config, timestamps, rng)
    price_limits = config["market"].get("price_limits", {"min": 0, "max": 1500})

    price_series, dispatch_records, profit_records, renewable_dispatch = (
        _merit_order_dispatch(units, demand, price_limits, rng, timestamps)
    )

    df_prices = pd.DataFrame({
        "timestamp": timestamps,
        "price_da_元_per_mwh": price_series,
    })
    df_prices.to_csv(output_dir / "clearing_prices.csv", index=False)

    df_dispatch = pd.DataFrame(dispatch_records)
    if len(df_dispatch) > 0:
        df_dispatch = df_dispatch.sort_values(["timestamp", "unit"])
    df_dispatch.to_csv(output_dir / "dispatch.csv", index=False)

    df_profits = pd.DataFrame(profit_records)
    if len(df_profits) > 0:
        df_profits = df_profits.sort_values(["timestamp", "agent"])
    df_profits.to_csv(output_dir / "agent_profits.csv", index=False)

    total_profit = df_profits["profit_元"].sum() if len(df_profits) > 0 else 0.0
    avg_price = float(np.nanmean(price_series))
    renewable_share = float(
        renewable_dispatch.sum() / demand.sum() * 100 if demand.sum() > 0 else 0
    )

    metadata = {
        "config_file": str(config.get("_config_path", "unknown")),
        "scenario": config.get("scenario", "baseline"),
        "duration_days": duration_days,
        "total_hours": len(timestamps),
        "start_time": start_time.isoformat() + "Z",
        "end_time": end_time.isoformat() + "Z",
        "seed": seed,
        "status": "completed" if not INTERRUPTED else "interrupted",
        "completed_at": datetime.now().isoformat() + "Z",
        "total_profit_元": round(total_profit, 2),
        "average_clearing_price_元_per_mwh": round(avg_price, 2),
        "renewable_share_pct": round(renewable_share, 2),
    }

    with open(output_dir / "simulation_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata


def run_assume_simulation(config_path: str, output_dir: Path, seed: int) -> dict:
    from assume import World

    world = World(yaml_config=config_path)
    world.run(duration_days=7, granularity="1h")
    results = world.get_results()

    df_prices = pd.DataFrame(results.get("clearing_prices", []))
    df_prices.to_csv(output_dir / "clearing_prices.csv", index=False)

    df_dispatch = pd.DataFrame(results.get("dispatch", []))
    df_dispatch.to_csv(output_dir / "dispatch.csv", index=False)

    df_profits = pd.DataFrame(results.get("agent_profits", []))
    df_profits.to_csv(output_dir / "agent_profits.csv", index=False)

    timestamps = df_prices["timestamp"] if "timestamp" in df_prices else []
    price_series = df_prices["price_da_元_per_mwh"] if "price_da_元_per_mwh" in df_prices else []
    total_profit = df_profits["profit_元"].sum() if "profit_元" in df_profits else 0.0
    avg_price = float(price_series.mean()) if len(price_series) > 0 else 0.0

    metadata = {
        "config_file": config_path,
        "duration_days": 7,
        "total_hours": len(timestamps),
        "seed": seed,
        "status": "completed",
        "completed_at": datetime.now().isoformat() + "Z",
        "total_profit_元": round(total_profit, 2),
        "average_clearing_price_元_per_mwh": round(avg_price, 2),
    }

    with open(output_dir / "simulation_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata


def main() -> None:
    args = parse_args()
    output_dir = resolve_output_dir(args.output)
    seed = args.seed

    logger.info("Loading config: %s", args.config)
    config = load_config(args.config)
    config["_config_path"] = args.config

    logger.info("Output directory: %s", output_dir)
    logger.info("Seed: %d", seed)

    start_wall = time.time()

    try:
        if HAS_ASSUME:
            logger.info("Using ASSUME World API")
            metadata = run_assume_simulation(args.config, output_dir, seed)
        else:
            logger.info("ASSUME not available — using built-in simulation engine")
            metadata = run_builtin_simulation(config, output_dir, seed)
    except Exception:
        logger.exception("Simulation failed")
        metadata = {
            "config_file": args.config,
            "status": "failed",
            "completed_at": datetime.now().isoformat() + "Z",
            "error": "Simulation failed — see logs above",
        }
        with open(output_dir / "simulation_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        sys.exit(1)

    elapsed = time.time() - start_wall
    metadata["elapsed_seconds"] = round(elapsed, 2)
    with open(output_dir / "simulation_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    files = ["clearing_prices.csv", "dispatch.csv", "agent_profits.csv", "simulation_metadata.json"]
    hashes = {}
    for fname in files:
        fpath = output_dir / fname
        if fpath.exists():
            hashes[fname] = hashlib.sha256(fpath.read_bytes()).hexdigest()

    with open(output_dir / "checksums.sha256", "w") as f:
        for fname, h in hashes.items():
            f.write(f"{h}  {fname}\n")

    logger.info("=" * 50)
    logger.info("Simulation %s", metadata["status"])
    logger.info("  Duration: %d days (%d hours)", config["simulation"]["duration_days"], metadata["total_hours"])
    logger.info("  Avg clearing price: %.2f 元/MWh", metadata.get("average_clearing_price_元_per_mwh", 0))
    logger.info("  Total profit: %.2f 元", metadata.get("total_profit_元", 0))
    logger.info("  Elapsed: %.1f s", elapsed)
    logger.info("  Output: %s", output_dir)
    logger.info("=" * 50)

    sys.exit(0 if metadata["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
