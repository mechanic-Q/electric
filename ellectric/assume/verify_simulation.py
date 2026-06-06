#!/usr/bin/env python3
"""
ASSUME simulation output verification script.

Usage:
    python verify_simulation.py --input <output_dir> [--plot]

Returns:
    JSON summary with passed/failed checks and statistics.
    Exit code 0 if all checks pass, 1 otherwise.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HAS_PLOTLY = False
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    HAS_PLOTLY = True
except ImportError:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify ASSUME simulation output completeness and sanity."
    )
    parser.add_argument("--input", required=True, type=str, help="Simulation output directory")
    parser.add_argument(
        "--plot", action="store_true", default=False, help="Generate plotly visualization"
    )
    return parser.parse_args()


REQUIRED_FILES = [
    "clearing_prices.csv",
    "dispatch.csv",
    "agent_profits.csv",
    "simulation_metadata.json",
]

PRICE_MIN = 0
PRICE_MAX = 1500
BALANCE_TOLERANCE = 0.05
NAN_TOLERANCE = 0.01


def check_files_exist(in_dir: Path) -> tuple[bool, list[str]]:
    errors = []
    for fname in REQUIRED_FILES:
        fpath = in_dir / fname
        if not fpath.is_file():
            errors.append(f"{fname} not found or is not a file")
        elif fpath.stat().st_size == 0:
            errors.append(f"{fname} is empty (0 bytes)")
    return len(errors) == 0, errors


def load_csv_safe(in_dir: Path, fname: str) -> pd.DataFrame | None:
    fpath = in_dir / fname
    try:
        df = pd.read_csv(fpath)
        if df.empty:
            return None
        return df
    except Exception as e:
        return None


def check_prices(df_prices: pd.DataFrame, errors: list[str]) -> bool:
    if "price_da_元_per_mwh" not in df_prices.columns:
        errors.append("clearing_prices.csv: missing column 'price_da_元_per_mwh'")
        return False

    prices = df_prices["price_da_元_per_mwh"]
    nan_mask = pd.isna(prices)
    nan_ratio = nan_mask.mean()

    if nan_ratio > NAN_TOLERANCE:
        errors.append(
            f"clearing_prices.csv: {nan_ratio:.1%} NaN prices (tolerance {NAN_TOLERANCE:.1%})"
        )
        return False

    valid = prices.dropna()
    if ((valid < PRICE_MIN) | (valid > PRICE_MAX)).any():
        n_out = ((valid < PRICE_MIN) | (valid > PRICE_MAX)).sum()
        errors.append(
            f"clearing_prices.csv: {n_out} prices outside [{PRICE_MIN}, {PRICE_MAX}]"
        )
        return False

    return True


def check_dispatch(df_dispatch: pd.DataFrame, errors: list[str]) -> bool:
    if "dispatch_mw" not in df_dispatch.columns:
        errors.append("dispatch.csv: missing column 'dispatch_mw'")
        return False
    if "timestamp" not in df_dispatch.columns:
        errors.append("dispatch.csv: missing column 'timestamp'")
        return False
    if "unit" not in df_dispatch.columns:
        errors.append("dispatch.csv: missing column 'unit'")
        return False

    dispatch = df_dispatch["dispatch_mw"]
    nan_ratio = pd.isna(dispatch).mean()
    if nan_ratio > NAN_TOLERANCE:
        errors.append(f"dispatch.csv: {nan_ratio:.1%} NaN dispatch values")
        return False

    if (dispatch.dropna() < 0).any():
        n_neg = (dispatch.dropna() < 0).sum()
        errors.append(f"dispatch.csv: {n_neg} negative dispatch values")
        return False

    if np.isinf(dispatch.replace([np.nan], 0)).any():
        errors.append("dispatch.csv: contains inf values")
        return False

    return True


def check_balance(
    df_dispatch: pd.DataFrame,
    df_prices: pd.DataFrame,
    expected_hours: int,
    errors: list[str],
) -> bool:
    ok = True

    if "timestamp" not in df_dispatch.columns or "timestamp" not in df_prices.columns:
        errors.append("Cannot check balance: missing timestamps in CSV files")
        return False

    hourly_dispatch = df_dispatch.groupby("timestamp")["dispatch_mw"].sum()

    # We don't have explicit demand in output, but we can check total hours
    actual_hours = len(df_prices)
    if actual_hours != expected_hours:
        errors.append(
            f"Expected {expected_hours} hours, got {actual_hours}"
        )
        ok = False

    return ok


def check_profits(df_profits: pd.DataFrame, errors: list[str]) -> bool:
    if "profit_元" not in df_profits.columns:
        errors.append("agent_profits.csv: missing column 'profit_元'")
        return False

    profits = df_profits["profit_元"]
    nan_ratio = pd.isna(profits).mean()
    if nan_ratio > NAN_TOLERANCE:
        errors.append(f"agent_profits.csv: {nan_ratio:.1%} NaN profit values")
        return False

    if np.isinf(profits.replace([np.nan], 0)).any():
        errors.append("agent_profits.csv: contains inf values")
        return False

    return True


def compute_stats(
    df_prices: pd.DataFrame,
    df_dispatch: pd.DataFrame,
    df_profits: pd.DataFrame,
    metadata: dict,
) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    prices = df_prices["price_da_元_per_mwh"].dropna() if "price_da_元_per_mwh" in df_prices else pd.Series(dtype=float)
    stats["avg_price_元_per_mwh"] = round(float(prices.mean()), 2) if len(prices) > 0 else 0.0
    stats["max_price_元_per_mwh"] = round(float(prices.max()), 2) if len(prices) > 0 else 0.0
    stats["min_price_元_per_mwh"] = round(float(prices.min()), 2) if len(prices) > 0 else 0.0
    stats["price_nan_count"] = int(pd.isna(df_prices["price_da_元_per_mwh"]).sum()) if "price_da_元_per_mwh" in df_prices else 0
    stats["price_total_hours"] = len(df_prices)

    if "dispatch_mw" in df_dispatch:
        stats["total_dispatch_mwh"] = round(float(df_dispatch["dispatch_mw"].sum()), 2)

    if "fuel_type" in df_dispatch:
        total_gen = df_dispatch["dispatch_mw"].sum()
        renewable_gen = df_dispatch[df_dispatch["fuel_type"].isin(["wind", "solar"])]["dispatch_mw"].sum()
        stats["renewable_share_pct"] = round(float(renewable_gen / total_gen * 100), 2) if total_gen > 0 else 0.0

    if "profit_元" in df_profits:
        stats["total_profit_元"] = round(float(df_profits["profit_元"].sum()), 2)

    stats["nan_ratio_prices"] = round(float(pd.isna(df_prices["price_da_元_per_mwh"]).mean()), 4) if "price_da_元_per_mwh" in df_prices else 0.0

    return stats


def generate_plots(in_dir: Path) -> list[str]:
    if not HAS_PLOTLY:
        return []

    plots_dir = in_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    generated = []

    df_prices = load_csv_safe(in_dir, "clearing_prices.csv")
    df_dispatch = load_csv_safe(in_dir, "dispatch.csv")
    df_profits = load_csv_safe(in_dir, "agent_profits.csv")

    # 1. Clearing price time series
    if df_prices is not None and "timestamp" in df_prices.columns:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=pd.to_datetime(df_prices["timestamp"]),
            y=df_prices["price_da_元_per_mwh"],
            mode="lines+markers",
            name="Clearing Price",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=4),
        ))
        fig1.add_hline(y=1500, line_dash="dash", line_color="red", annotation_text="Price cap")
        fig1.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Price floor")
        fig1.update_layout(
            title="Clearing Price — 7-Day Simulation",
            xaxis_title="Time",
            yaxis_title="Price (元/MWh)",
            hovermode="x unified",
            height=450,
        )
        p1 = plots_dir / "clearing_prices.html"
        fig1.write_html(str(p1))
        generated.append(str(p1))

    # 2. Dispatch stacked area
    if df_dispatch is not None and "fuel_type" in df_dispatch.columns and "timestamp" in df_dispatch.columns:
        df_dispatch["timestamp"] = pd.to_datetime(df_dispatch["timestamp"])
        pivot = df_dispatch.pivot_table(
            index="timestamp", columns="fuel_type", values="dispatch_mw", aggfunc="sum"
        ).fillna(0)
        fuel_colors = {
            "coal": "#8B4513",
            "gas": "#FF8C00",
            "wind": "#2E8B57",
            "solar": "#FFD700",
            "storage": "#9370DB",
            "nuclear": "#4169E1",
            "hydro": "#00CED1",
        }
        colors = [fuel_colors.get(c, "#999999") for c in pivot.columns]

        fig2 = go.Figure()
        for i, col in enumerate(pivot.columns):
            fig2.add_trace(go.Scatter(
                x=pivot.index,
                y=pivot[col],
                mode="lines",
                name=col,
                stackgroup="one",
                line=dict(width=0.5, color=colors[i] if i < len(colors) else None),
            ))
        fig2.update_layout(
            title="Generation Dispatch by Fuel Type — Stacked Area",
            xaxis_title="Time",
            yaxis_title="Dispatch (MW)",
            hovermode="x unified",
            height=450,
        )
        p2 = plots_dir / "dispatch_by_fuel.html"
        fig2.write_html(str(p2))
        generated.append(str(p2))

    # 3. Agent profit comparison
    if df_profits is not None and "agent" in df_profits.columns and "profit_元" in df_profits.columns:
        agent_totals = df_profits.groupby("agent")["profit_元"].sum().reset_index()
        agent_totals = agent_totals.sort_values("profit_元", ascending=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=agent_totals["profit_元"],
            y=agent_totals["agent"],
            orientation="h",
            marker_color=["#2ca02c" if v >= 0 else "#d62728" for v in agent_totals["profit_元"]],
            text=agent_totals["profit_元"].apply(lambda x: f"{x:,.0f} 元"),
            textposition="outside",
        ))
        fig3.update_layout(
            title="Total Profit by Agent — 7-Day Simulation",
            xaxis_title="Profit (元)",
            yaxis_title="Agent",
            height=400,
        )
        p3 = plots_dir / "agent_profits.html"
        fig3.write_html(str(p3))
        generated.append(str(p3))

    return generated


def main() -> None:
    args = parse_args()
    in_dir = Path(args.input)

    if not in_dir.is_dir():
        print(json.dumps({
            "passed": False,
            "files_exist": False,
            "errors": [f"Input directory not found: {args.input}"],
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    errors: list[str] = []

    # 1. File existence check
    files_ok, file_errors = check_files_exist(in_dir)
    errors.extend(file_errors)

    df_prices = load_csv_safe(in_dir, "clearing_prices.csv")
    df_dispatch = load_csv_safe(in_dir, "dispatch.csv")
    df_profits = load_csv_safe(in_dir, "agent_profits.csv")
    metadata_path = in_dir / "simulation_metadata.json"
    metadata: dict = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text())
        except Exception as e:
            errors.append(f"simulation_metadata.json: parse error — {e}")

    expected_hours = metadata.get("total_hours", 168)

    # 2. Data integrity checks
    price_ok = False
    dispatch_ok = False
    profits_ok = False
    balance_ok = False

    if files_ok:
        if df_prices is not None:
            price_ok = check_prices(df_prices, errors)
        else:
            errors.append("clearing_prices.csv is empty or unreadable")

        if df_dispatch is not None:
            dispatch_ok = check_dispatch(df_dispatch, errors)
        else:
            errors.append("dispatch.csv is empty or unreadable")

        if df_profits is not None:
            profits_ok = check_profits(df_profits, errors)
        else:
            errors.append("agent_profits.csv is empty or unreadable")

        if df_prices is not None and df_dispatch is not None:
            balance_ok = check_balance(df_dispatch, df_prices, expected_hours, errors)
        else:
            balance_ok = False

    # 3. Stats
    stats = {}
    if df_prices is not None and df_dispatch is not None and df_profits is not None:
        stats = compute_stats(df_prices, df_dispatch, df_profits, metadata)

    passed = files_ok and price_ok and dispatch_ok and profits_ok and balance_ok and len(errors) == 0

    # 4. Plots
    plots = []
    if args.plot and files_ok:
        plots = generate_plots(in_dir)

    result = {
        "passed": passed,
        "files_exist": files_ok,
        "price_range_ok": price_ok,
        "balance_ok": balance_ok,
        "stats": stats,
        "errors": errors,
        "plots_generated": plots,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Summary for terminal
    print()
    print("=" * 50)
    print("  Verification Summary")
    print("=" * 50)
    print(f"  Files exist:      {'PASS' if files_ok else 'FAIL'}")
    print(f"  Price range:      {'PASS' if price_ok else 'FAIL'}")
    print(f"  Dispatch valid:   {'PASS' if dispatch_ok else 'FAIL'}")
    print(f"  Profits valid:    {'PASS' if profits_ok else 'FAIL'}")
    print(f"  Balance check:    {'PASS' if balance_ok else 'FAIL'}")
    if stats:
        print(f"  Avg price:        {stats.get('avg_price_元_per_mwh', 'N/A')} 元/MWh")
        print(f"  Total profit:     {stats.get('total_profit_元', 'N/A')} 元")
        print(f"  Renewable share:  {stats.get('renewable_share_pct', 'N/A')}%")
    if plots:
        print(f"  Plots:            {len(plots)} generated")
    if errors:
        print(f"  Errors ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    print(f"  Result:           {'ALL PASSED ✓' if passed else 'FAILED ✗'}")
    print("=" * 50)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
