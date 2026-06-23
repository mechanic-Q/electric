#!/usr/bin/env python3
"""
验证脚本 — 山西现货数据接入 (task-07)
===========================================
覆盖: FR-009 (优雅降级), NFR-001 (性能 <5s)

用法:
    python ellectric/scripts/verify_shanxi_loader.py
"""

import sys, time, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING)

from ellectric.pipeline.data_loader import create_loader

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  {detail}")

print("=" * 60)
print("山西现货数据接入 — 验证")
print("=" * 60)

# ── spot_da ──
print("\n── ShanxiSpotDaLoader ──")
loader = create_loader("shanxi_spot_da")
t0 = time.time()
df = loader.load_data()
elapsed = time.time() - t0

check("类型正确", type(loader).__name__ == "ShanxiSpotDaLoader", f"got {type(loader).__name__}")
check("行数 >= 4000", len(df) >= 4000, f"got {len(df)}")
check("列名正确", list(df.columns) == ['timestamp', 'da_price_a', 'da_price_b', 'load_mw', 'province', 'source', 'granularity'], f"got {list(df.columns)}")
check("timestamp UTC", str(df['timestamp'].dtype) in ('datetime64[ns, UTC]', 'datetime64[us, UTC]'), f"got {df['timestamp'].dtype}")
check("load_mw 全 NaN", df['load_mw'].isna().all(), f"non-null: {df['load_mw'].notna().sum()}")
check("province = shanxi", (df['province'] == 'shanxi').all())
check("granularity = 15min", (df['granularity'] == '15min').all())
check("性能 < 5s", elapsed < 5.0, f"{elapsed:.2f}s")
meta = loader.get_metadata()
check("get_metadata 非空", meta.get('source') is not None, f"meta={meta.get('source')}")

# ── spot_rt ──
print("\n── ShanxiSpotRtLoader ──")
loader = create_loader("shanxi_spot_rt")
t0 = time.time()
df = loader.load_data()
elapsed = time.time() - t0

check("类型正确", type(loader).__name__ == "ShanxiSpotRtLoader")
check("行数 >= 4000", len(df) >= 4000, f"got {len(df)}")
check("列名正确", list(df.columns) == ['timestamp', 'rt_energy_demand', 'rt_energy_supply', 'load_mw', 'province', 'source', 'granularity'])
check("load_mw = rt_energy_demand", (df['load_mw'] == df['rt_energy_demand']).all(), f"mismatch count: {(df['load_mw'] != df['rt_energy_demand']).sum()}")
check("性能 < 5s", elapsed < 5.0, f"{elapsed:.2f}s")

# ── month_settle ──
print("\n── ShanxiMonthSettleLoader ──")
loader = create_loader("shanxi_month_settle")
t0 = time.time()
df = loader.load_data()
elapsed = time.time() - t0

check("类型正确", type(loader).__name__ == "ShanxiMonthSettleLoader")
check("行数 >= 2000", len(df) >= 2000, f"got {len(df)}")
check("列名正确", list(df.columns) == ['timestamp', 'time_point', 'settle_day_price', 'settle_rt_price', 'load_mw', 'province', 'source', 'granularity'])
check("load_mw 全 NaN", df['load_mw'].isna().all())
check("granularity = daily-point", (df['granularity'] == 'daily-point').all())
check("性能 < 5s", elapsed < 5.0, f"{elapsed:.2f}s")

# ── 优雅降级 ──
print("\n── 优雅降级 ──")
loader = create_loader("shanxi_spot_da")
df = loader.load_data(start="2099-01")
check("start=2099-01 返回空 DataFrame", len(df) == 0, f"got {len(df)} rows")

df = loader.load_data(end="2000-01")
check("end=2000-01 返回空 DataFrame", len(df) == 0, f"got {len(df)} rows")

# ── 兼容性 ──
print("\n── 兼容性 ──")
for src in ["owid", "ember"]:
    try:
        loader = create_loader(src)
        check(f"create_loader({src!r}) 成功", True, type(loader).__name__)
    except Exception as e:
        check(f"create_loader({src!r}) 成功", False, str(e)[:80])

# ── 总结 ──
print()
print(f"✅ {PASS} 通过 / ❌ {FAIL} 失败")
sys.exit(0 if FAIL == 0 else 1)
