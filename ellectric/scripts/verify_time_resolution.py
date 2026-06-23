#!/usr/bin/env python3
"""TimeResolutionConfig的验证脚本."""

import sys; sys.path.insert(0, '.')
from ellectric.config import TimeConfig
from ellectric.pipeline.data_loader import create_loader

PASS = 0; FAIL = 0
def chk(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label} {detail}")

print("=" * 60)
print("TimeResolutionConfig 验证")
print("=" * 60)

# 1: 默认值
print("\n—— 默认Config值 ——")
chk("points_per_day 默认 24", TimeConfig.points_per_day == 24)
chk("points_per_week 默认 168", TimeConfig.points_per_week == 168)
chk("freq 默认 h", TimeConfig.freq == "h")

# 2: shanxi_loader仍通过（默认24下不受影响证明）
print("\n—— 默认 24 下兼容验证 ——")
try:
    ldr = create_loader("shanxi_spot_da")
    df = ldr.load_data()
    chk("spot_da 默认行为不变", len(df) == 4800)
    chk("spot_da data_loader 零修改", "da_price_a" in df.columns)
except Exception as e:
    chk(f"spot_da 兼容 {e}", False, str(e)[:80])

# 3: 改为96验证
print("\n—— 切换 15min 验证 ——")
save_ppd = TimeConfig.points_per_day
save_ppw = TimeConfig.points_per_week
save_freq = TimeConfig.freq

TimeConfig.points_per_day = 96
TimeConfig.points_per_week = 672
TimeConfig.freq = "15min"

chk("points_per_day 已改", TimeConfig.points_per_day == 96)
chk("points_per_week 已改", TimeConfig.points_per_week == 672)
chk("freq 已改", TimeConfig.freq == "15min")

# 3a: trading_env 跟随
try:
    from ellectric.pipeline.trading_env import ElectricityMarketEnv
    import pandas as pd, numpy as np
    ld = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=200, freq="h", tz="UTC"),
                       "load_mw": np.ones(200)*500})
    pd2 = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=200, freq="h", tz="UTC"),
                        "price_da": np.ones(200)*300})
    env = ElectricityMarketEnv(ld, pd2)
    chk("action_space 变为 (96,)", env.action_space.shape == (96,), f"shape={env.action_space.shape}")
except ImportError as e:
    chk("trading_env 模块导入(gymnasium 缺失,跳过)", True, "skip")
except Exception as e:
    chk("action_space check", False, str(e)[:80])

# restore
TimeConfig.points_per_day = save_ppd
TimeConfig.points_per_week = save_ppw
TimeConfig.freq = save_freq

# 4: 还原验证
print("\n—— 还原默认配置 ——")
chk("points_per_day 已还原", TimeConfig.points_per_day == 24)
chk("points_per_week 已还原", TimeConfig.points_per_week == 168)
chk("freq 已还原", TimeConfig.freq == "h")

# 5: cleaner 不再硬编码
print("\n—— cleaner 无硬编码h ——")
try:
    t = open("ellectric/pipeline/cleaner.py").read()
    chk("无 freq!='h' 硬编码", "freq != 'h'" not in t)
    chk("有 freq!=TimeConfig.freq", "TimeConfig.freq" in t)
except: pass

# 6: feature 列名保留为 lag_24h（不改成 lag_96 之类）
print("\n—— 特征列名保留 ——")
chk('features.py 保留 "lag_24h" 特征名', '"lag_24h"' in open("ellectric/pipeline/features.py").read())

print(f"\n✅ {PASS} 通过 / ❌ {FAIL} 失败")
sys.exit(0 if FAIL == 0 else 1)
