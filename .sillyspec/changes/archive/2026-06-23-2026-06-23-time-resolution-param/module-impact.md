---
author: lmr
created_at: 2026-06-23T23:45:00+08:00
---

# Module Impact — 时间分辨率参数化

## 变更概述

`time-resolution-param` (PR #8)：引入 `TimeConfig` 全局配置类，将 pipeline 5 文件中硬编码的 24/168/`"h"` 替换为可配置引用。一处修改全局切换 hourly ↔ 15min。

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|---|---|---|---|---|
| config | 新增 | `ellectric/config.py` (新增) | `TimeConfig` 类 — 3 属性 | false |
| trading-env | 接口变更 | `ellectric/pipeline/trading_env.py` (28 处) | obs/action shape、n_hours、lag windows、freq、persistence | false |
| feature-engineer | 接口变更 | `ellectric/pipeline/features.py` (2 处) | shift(24)/shift(168) → TimeConfig | false |
| forecaster | 接口变更 | `ellectric/pipeline/forecaster.py` (1 处) | shift(24) → TimeConfig | false |
| price-forecaster | 接口变更 | `ellectric/pipeline/price_forecaster.py` (5 处) | shift × 价格/负荷/风电/光伏 → TimeConfig | false |
| cleaner | 接口变更 | `ellectric/pipeline/cleaner.py` (2 处) | freq 比较 + 重采样目标 → TimeConfig | false |
| scripts | 新增 | `ellectric/scripts/verify_time_resolution.py` (新增) | 15 项验证脚本 | false |

## 下游影响分析

- **不修改** `data_loader.py` / `shanxi_loader.py` / `cli/main.py` / `api/server.py`
- **不修改** `requirements.txt`（无新依赖）
- **默认值兼容**：所有现有调用方不感知此变更（TimeConfig 默认 24/168/"h"）
- **切换方式**：用户修改 `TimeConfig.points_per_day` / `points_per_week` / `freq` 三个属性即可全局生效

## 验证结论

```
python ellectric/scripts/verify_time_resolution.py
✅ 15 通过 / ❌ 0 失败

python ellectric/scripts/verify_shanxi_loader.py
✅ 24 通过 / ❌ 0 失败 (回归)
```

PR #8 已 merge 到 master（`a0e3ca7`）。
