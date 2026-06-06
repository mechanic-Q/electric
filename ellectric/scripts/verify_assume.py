#!/usr/bin/env python3
"""
ASSUME 安装验证脚本
Verifies ASSUME framework installation and runs a minimal simulation.

Usage:
    python scripts/verify_assume.py
"""

import os
import sys
import shutil
import tempfile
import logging
from datetime import datetime, timedelta
from typing import Any

from dateutil import rrule as rr


def check_python_version() -> bool:
    """Check Python >= 3.11."""
    ok = sys.version_info >= (3, 11)
    if not ok:
        print(
            f"  [FAIL] Python {sys.version_info.major}.{sys.version_info.minor} < 3.11"
        )
        print("         Please upgrade to Python 3.11+")
    return ok


def check_imports() -> bool:
    """Verify ASSUME and related dependencies can be imported."""
    ok = True
    checks = []

    try:
        from assume import World  # noqa: F401
        checks.append(("ASSUME", True, None))
    except ImportError as e:
        checks.append(("ASSUME", False, str(e)))
        ok = False

    try:
        import torch  # noqa: F401
        cuda = torch.cuda.is_available()
        cuda_msg = " (CUDA available)" if cuda else " (CPU only)"
        checks.append(("PyTorch", True, f"{torch.__version__}{cuda_msg}"))
    except ImportError as e:
        checks.append(("PyTorch", False, str(e)))
        ok = False

    try:
        from stable_baselines3 import PPO  # noqa: F401
        import stable_baselines3 as sb3
        checks.append(("stable-baselines3", True, sb3.__version__))
    except ImportError as e:
        checks.append(("stable-baselines3", False, str(e)))
        ok = False

    try:
        import gymnasium  # noqa: F401
        checks.append(("gymnasium", True, gymnasium.__version__))
    except ImportError as e:
        checks.append(("gymnasium", False, str(e)))
        ok = False

    for name, success, detail in checks:
        if success:
            detail_str = f" -> version: {detail}" if detail else ""
            print(f"  [PASS] {name}{detail_str}")
        else:
            print(f"  [FAIL] {name}: {detail}")

    return ok


def check_version() -> str:
    """Return the ASSUME version string."""
    try:
        from assume import __version__
        return __version__
    except ImportError:
        try:
            from importlib.metadata import version
            return version("assume-framework")
        except ImportError:
            return "unknown"


def run_minimal_simulation() -> dict[str, Any]:
    """
    Run a minimal ASSUME simulation using inline configuration.

    Creates a temp SQLite DB to capture results, runs 48h simulation,
    then reads back clearing prices and dispatch data.

    Returns:
        dict with status, clearing_prices, dispatch, total_profit, error
    """
    logging.getLogger("assume").setLevel(logging.WARNING)

    try:
        from assume import World
        from assume.common.fast_pandas import FastIndex
        from assume.common.forecaster import DemandForecaster, PowerplantForecaster
        from assume.common.market_objects import MarketConfig, MarketProduct
        import sqlite3
        import pandas as pd
    except ImportError as e:
        return {
            "status": "failure",
            "clearing_prices": [],
            "dispatch": {},
            "total_profit": 0.0,
            "error": f"import error: {e}",
        }

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "assume_verify.db")

    try:
        start = datetime(2019, 1, 1)
        end = datetime(2019, 1, 3)

        index = FastIndex(start, end, freq="h")

        world = World(database_uri=f"sqlite:///{db_path}")
        world.setup(
            start=start,
            end=end,
            save_frequency_hours=48,
            simulation_id="verify_assume",
        )

        market_config = MarketConfig(
            market_id="EOM",
            opening_hours=rr.rrule(
                rr.HOURLY, interval=24, dtstart=start, until=end, cache=True
            ),
            opening_duration=timedelta(hours=1),
            market_mechanism="pay_as_clear",
            market_products=[
                MarketProduct(timedelta(hours=1), 24, timedelta(hours=1))
            ],
            additional_fields=["block_id", "link", "exclusive_id"],
        )

        world.add_market_operator(id="market_operator")
        world.add_market("market_operator", market_config)

        world.add_unit_operator("my_demand")
        world.add_unit(
            "demand1",
            "demand",
            "my_demand",
            {
                "min_power": 0,
                "max_power": -1000,
                "bidding_strategies": {"EOM": "demand_energy_naive"},
                "technology": "demand",
            },
            DemandForecaster(index, demand=-1000),
        )

        nuclear_forecast = PowerplantForecaster(
            index, availability=1, fuel_prices={"others": 3, "co2": 0.1}
        )
        world.add_unit_operator("my_operator")
        world.add_unit(
            "nuclear1",
            "power_plant",
            "my_operator",
            {
                "min_power": 200,
                "max_power": 1000,
                "bidding_strategies": {"EOM": "powerplant_energy_naive"},
                "technology": "nuclear",
            },
            nuclear_forecast,
        )

        world.run()

        conn = sqlite3.connect(db_path)

        clearing_prices = pd.read_sql(
            "SELECT price FROM market_meta ORDER BY time", conn
        )
        prices_list = clearing_prices["price"].tolist()

        dispatch = pd.read_sql(
            "SELECT unit, power FROM unit_dispatch WHERE power != 0", conn
        )
        dispatch_by_unit = (
            dispatch.groupby("unit")["power"].sum().abs().to_dict()
        )

        kpis = pd.read_sql("SELECT * FROM kpis", conn)
        total_cost = kpis.loc[
            kpis["variable"] == "total_cost", "value"
        ].values
        total_revenue = prices_list[0] * 1000 * len(prices_list) if prices_list else 0
        total_profit = float(
            total_cost[0] if len(total_cost) > 0 else 0
        )

        conn.close()

        return {
            "status": "success",
            "clearing_prices": prices_list,
            "dispatch": dispatch_by_unit,
            "total_profit": total_profit,
            "error": None,
        }

    except Exception as e:
        return {
            "status": "failure",
            "clearing_prices": [],
            "dispatch": {},
            "total_profit": 0.0,
            "error": str(e),
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> None:
    """Orchestrate all checks and print verification report."""
    print("=" * 50)
    print("  ASSUME 安装验证报告")
    print("=" * 50)

    all_pass = True

    print("\n[1/4] Python 版本检查")
    if not check_python_version():
        all_pass = False

    print("\n[2/4] 导入验证")
    if not check_imports():
        all_pass = False

    print("\n[3/4] 版本检查")
    ver = check_version()
    print(f"  ASSUME 版本: {ver}")

    print("\n[4/4] 最小仿真运行")
    result = run_minimal_simulation()
    if result["status"] == "success":
        prices = result["clearing_prices"]
        dispatch = result["dispatch"]
        total_profit = result["total_profit"]
        print(f"  [PASS] 最小仿真运行成功")
        print(f"         出清时段: {len(prices)} 小时")
        if prices:
            avg_price = sum(prices) / len(prices)
            print(f"         平均出清价格: {avg_price:.2f}")
        print(f"         智能体数量: {len(dispatch)}")
        if dispatch:
            for unit, power in dispatch.items():
                print(f"           - {unit}: {power:.0f} MWh")
    else:
        print(f"  [FAIL] 最小仿真运行失败")
        print(f"         错误: {result.get('error', 'unknown')}")
        all_pass = False

    print("\n" + "=" * 50)
    if all_pass:
        print("  状态: 全部通过 ✓")
    else:
        print("  状态: 部分检查未通过 ✗")
        print("  请根据上述错误信息排查问题")
    print("=" * 50)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
