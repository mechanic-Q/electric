---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-09
title: 运行代码测试与旧 API 兼容检查
priority: P0
depends_on:
  - task-01
  - task-02
  - task-03
blocks:
  - task-10
requirement_ids:
  - FR-001
  - FR-002
  - FR-003
  - FR-004
decision_ids:
  - D-006@v2
  - D-007@v2
allowed_paths:
  - tests/test_weather_features.py
  - tests/test_time_resolution_15min.py
  - tests/__init__.py
---

# Task-09: 运行代码测试与旧 API 兼容检查

## 修改文件

无代码修改。只运行验证命令。

## 覆盖来源

| 需求/决策 | 覆盖方式 |
|---|---|
| FR-001 | `test_add_tier4_weather_df_only` / `test_add_tier4_preserves_tier1_tier2_tier3` / `test_add_tier4_no_weather_df_warns` 通过 |
| FR-002 | `test_add_tier4_cache_hit_no_network` / `test_add_tier4_cache_miss_fetch_false_degrades` / `test_add_tier4_cache_miss_fetch_true_calls_fetch` 通过 |
| FR-003 | `test_add_tier4_ffill_covers_0045` / `test_add_tier4_handles_timestamp_index` 通过 |
| FR-004 | `test_get_feature_columns_tier4_includes_weather` / `test_get_feature_columns_tier4_missing_weather_dropped` 通过 |
| D-006@v2 | `test_prepare_features_tier4_default_cache` / `test_prepare_features_tier1_unchanged` 通过 + 兼容脚本验证旧签名不变 |
| D-007@v2 | cache 命中/缺失/00:45 测试通过 |

## 实现要求

### 1. 运行 weather feature 测试套件

```bash
python -m pytest tests/test_weather_features.py -v --tb=short 2>&1
```

必须输出 12 个 test 全部 PASSED。task-01 定义了以下 12 个测试：

| 组 | 测试名称 | 覆盖目标 |
|---|---|---|
| A | `test_add_tier4_weather_df_only` | weather_df 显式传入 → 返回含天气列的 df |
| A | `test_add_tier4_preserves_tier1_tier2_tier3` | 不破坏已有特征 |
| A | `test_add_tier4_handles_timestamp_index` | index-based weather_df 合并 |
| A | `test_add_tier4_no_weather_df_warns` | 无 weather_df/cache 时 warning 而非异常 |
| B | `test_add_tier4_cache_hit_no_network` | cache 命中不触网 |
| B | `test_add_tier4_cache_miss_fetch_false_degrades` | cache 缺失 + fetch_if_missing=False 降级 |
| B | `test_add_tier4_cache_miss_fetch_true_calls_fetch` | cache 缺失 + fetch_if_missing=True 触发抓取 |
| C | `test_add_tier4_ffill_covers_0045` | 00:45 等 15min 边界有值 |
| D | `test_get_feature_columns_tier4_includes_weather` | get_feature_columns("tier4") 含天气列 |
| D | `test_get_feature_columns_tier4_missing_weather_dropped` | 无 weather 列时只返 Tier1-3 列 |
| E | `test_prepare_features_tier4_default_cache` | prepare_features 含 tier4 正常 |
| E | `test_prepare_features_tier1_unchanged` | 旧 prepare_features(df, tiers=['tier1']) 行为不变 |

### 2. 运行 15min 回归测试

```bash
python -m pytest tests/test_time_resolution_15min.py -v --tb=short 2>&1
```

验证 task-02/task-03 未破坏现有 TimeConfig/standardize_frequency/lag/rolling/forecaster/env/backtester/loader 契约。已知可能跳过的测试：`test_trading_env_action_shape_and_error_message` / `test_backtester_baseline_actions_use_timeconfig`（gymnasium 未安装时 skip），skip 算通过。

### 3. 旧 API 兼容检查

在不使用新增 weather 参数的前提下，验证旧公有 API 签名与行为不变。

```python
# compatibility_check.py — 不写文件，直接 python -c 执行
from ellectric.pipeline.features import prepare_features, get_feature_columns
import pandas as pd
import numpy as np

# 旧签名：仅 positional args
ts = pd.date_range("2024-01-01", periods=96, freq="15min", tz="UTC")
df = pd.DataFrame({"timestamp": ts, "load_mw": np.arange(96.0)})

# prepare_features(df) — 无 tiers 参数
df1 = prepare_features(df)
assert "load_mw" in df1.columns
assert "hour" in df1.columns

# prepare_features(df, tiers=['tier1']) — 旧签名
df2 = prepare_features(df, tiers=["tier1"])
assert "hour" in df2.columns
assert "lag_24h" in df2.columns

# prepare_features(df, tiers=['tier1', 'tier2', 'tier3']) — 全三层
df3 = prepare_features(df, tiers=["tier1", "tier2", "tier3"])
assert "rolling_mean_24h" in df3.columns

# get_feature_columns('tier1') — 旧签名
cols1 = get_feature_columns("tier1")
assert "hour" in cols1
assert "lag_24h" in cols1

# get_feature_columns('tier3') — 旧签名
cols3 = get_feature_columns("tier3")
assert "rolling_mean_24h" in cols3
assert "rolling_std_24h" in cols3

# get_feature_columns() — 无参数默认 tier1
cols_default = get_feature_columns()
assert cols_default == cols1

print("ALL COMPATIBILITY CHECKS PASSED")
```

### 4. 确认无真实 Open-Meteo 网络调用

```bash
# 确认 weather 测试文件没有任何真实 URL 或网络请求
python -m pytest tests/test_weather_features.py -v --tb=short 2>&1 | grep -i "open-meteo\|api.open-meteo\|HTTPRequest\|urllib\|requests.get"
# 若输出为空 → 无真实网络调用
# 若有输出 → task-01 或 task-03 泄露了真实 API 调用
```

若测试代码使用了 `monkeypatch` / `unittest.mock` / `tmp_path` 阻断网络和文件 IO，则此项自动满足。

### 5. local.yaml 环境适配

当前 `test_strategy: skip` 且 `commands.test` 未启用。因此本 task 手动执行 targeted pytest。跑完所有验证后，若全部通过，在 task-09 完成报告中记录实际命令输出摘要。

不需要回写 local.yaml（`test_strategy: skip` 仅表示 CI 不自动跑全量测试，不影响手动验证）。

## 接口定义

N/A。本任务不定义新接口，只验证已存在的接口契约。

## 边界处理

1. **测试 environment 未安装**: `tests/` 目录 import 涉及 gymnasium 的测试会 skip（`test_trading_env_action_shape_and_error_message`、`test_backtester_baseline_actions_use_timeconfig`）— skip 算通过，不视为失败
2. **weather cache parquet 文件不在预期位置**: task-01 使用 `tmp_path` / `monkeypatch` 避免依赖真实文件；若测试 fixture 意外指向真实路径，需确保测试用 fake cache 而非真实文件
3. **get_feature_columns 在 add_tier4 之前调用返回 tier3 列**: 兼容场景中 `get_feature_columns("tier4")` 无状态时返回 Tier3 列列表；兼容脚本不调用 tier4 方法
4. **prepare_features(df, tiers=['tier1']) 新增参数对旧调用无影响**: 兼容脚本只传 df + tiers，不传 weather_* 参数，验证调用不因新增参数默认值而报错
5. **导入链中非 weather 模块变更导致测试失败**: task-02 只改 `weather.py` 一行，task-03 只改 `features.py`。若 `test_time_resolution_15min.py` 失败，说明 task-02/task-03 的变更意外影响了非目标代码路径
6. **测试超时**: 带真实网络 IO 的测试若逃逸 mock，可能因 Open-Meteo 不可用而超时；pytest 默认无超时。若出现 hang，用 `pytest-timeout` 插件或手工杀掉进程。本地验证时加 `--timeout=30` 预防（需 `pytest-timeout` 已安装）
7. **新旧两种 `get_feature_columns` 签名冲突**: `features.py:180` 的 `def get_feature_columns(self, tier: str = "tier1")` 与 `price_forecaster.py:193` 同名方法重名但独立；兼容脚本只测试 `from ellectric.pipeline.features import get_feature_columns`
8. **多个 Python 版本环境**: 若当前 venv 非 Python 3.11，OpenSTEF 相关导入可能失败，但本 task 不导入 OpenSTEF，主要依赖 pandas/scikit-learn/xgboost，3.10~3.12 均兼容
9. **测试顺序依赖**: 12 个 weather 测试函数应独立（无共享状态），兼容脚本也是独立执行；若测试 A 在测试 B 之后才通过说明状态泄漏，需定位 bug
10. **pytest --collect-only 与实际运行数量不一致**: task-01 写了 12 个测试函数；若 collect 数量 ≠ 12，说明 task-01 未正确实现

## 非目标

- 不改写任何测试或源码
- 不修复测试失败（失败意味着前序 task 未正确完成）
- 不修改 `local.yaml` 或 `pytest.ini`
- 不安装新 Python 依赖（如 `pytest-timeout` 可选安装）
- 不运行 lint / ruff / mypy
- 不做 benchmark / performance 测试
- 不运行 notebook 中的测试
- 不提交 git commit

## 参考

- `tests/test_weather_features.py` — task-01 创建的 12 个契约测试
- `tests/test_time_resolution_15min.py` — 现有回归测试（12 个测试函数）
- `ellectric/pipeline/features.py:180-192` — `get_feature_columns()` 现有签名
- `ellectric/pipeline/features.py:197-226` — `prepare_features()` 现有签名（task-03 会扩展）
- `.sillyspec/local.yaml:15` — `test_strategy: skip`
- `plan.md:28-29,43-44` — Wave 4 定位、依赖关系
- `plan.md:62-71` — 全局验收标准中 task-09 相关项

## TDD 步骤

```bash
# 步骤 1: 确认前序 task 已完成
# git log --oneline -5 看 task-01/task-02/task-03 是否已提交

# 步骤 2: 收集 weather 测试用例数
python -m pytest tests/test_weather_features.py --collect-only -q 2>&1 | tail -5
# 预期: 12 tests collected

# 步骤 3: 运行 weather 测试
python -m pytest tests/test_weather_features.py -v --tb=short 2>&1
# 预期: 12 passed

# 步骤 4: 运行 15min 回归
python -m pytest tests/test_time_resolution_15min.py -v --tb=short 2>&1
# 预期: 全部 passed (含 skip 的 gymnasium 测试)

# 步骤 5: 旧 API 兼容检查
python -c "
from ellectric.pipeline.features import prepare_features
from ellectric.pipeline.features import get_feature_columns
import pandas as pd, numpy as np
ts = pd.date_range('2024-01-01', periods=96, freq='15min', tz='UTC')
df = pd.DataFrame({'timestamp': ts, 'load_mw': np.arange(96.0)})
df1 = prepare_features(df)
assert 'hour' in df1.columns
df2 = prepare_features(df, tiers=['tier1'])
assert 'lag_24h' in df2.columns
df3 = prepare_features(df, tiers=['tier1', 'tier2', 'tier3'])
assert 'rolling_mean_24h' in df3.columns
cols1 = get_feature_columns('tier1')
assert 'hour' in cols1
cols3 = get_feature_columns('tier3')
assert 'rolling_mean_24h' in cols3
assert get_feature_columns() == cols1
print('ALL COMPATIBILITY CHECKS PASSED')
"

# 步骤 6: 确认无真实 Open-Meteo 调用
python -m pytest tests/test_weather_features.py -v --tb=short 2>&1 | grep -ci 'open-meteo'
# 预期: 0

# 步骤 7: 统一输出摘要
echo '=== Weather Feature Tests ==='
python -m pytest tests/test_weather_features.py --tb=short -q 2>&1 | tail -2
echo '=== 15min Regression Tests ==='
python -m pytest tests/test_time_resolution_15min.py --tb=short -q 2>&1 | tail -2
echo '=== API Compatibility ==='
python -c "...（如上）..."
```

所有 7 步连续执行。若任一步失败，记录失败命令和输出，不跳过。

## 验收标准表格

| # | 标准 | 验证方式 | 覆盖 |
|---|---|---|---|
| 1 | 12 个 weather 测试全部 collected | `pytest --collect-only -q` 输出 "12 tests collected" | FR-001~FR-004 |
| 2 | 12 个 weather 测试全部 passed | `pytest -v --tb=short` 输出全 PASSED | FR-001~FR-004 |
| 3 | `test_time_resolution_15min.py` 全部通过（skip 不计入失败） | `pytest -v --tb=short` 输出预期结果 | 回归 |
| 4 | `prepare_features(df)` 无参数调用正常工作 | python -c 断言通过 | D-006@v2 |
| 5 | `prepare_features(df, tiers=['tier1'])` 返回含 hour/lag_24h 的 df | python -c 断言通过 | D-006@v2 |
| 6 | `prepare_features(df, tiers=['tier1','tier2','tier3'])` 全层正常 | python -c 断言通过 | D-006@v2 |
| 7 | `get_feature_columns('tier1')` 返回 tier1 特征列表 | python -c 断言通过 | D-006@v2 |
| 8 | `get_feature_columns('tier3')` 返回含 rolling 特征的列表 | python -c 断言通过 | D-006@v2 |
| 9 | `get_feature_columns()` 默认值 = `get_feature_columns('tier1')` | python -c 断言通过 | D-006@v2 |
| 10 | weather 测试未真实调用 Open-Meteo API | grep 搜索 "open-meteo" 在 pytest 输出中为 0 | 非功能 |
| 11 | 旧 `get_feature_columns` 签名 `(self, tier: str = "tier1")` 兼容 | `inspect.signature` 验证或 python -c 直接调用 | D-006@v2 |
| 12 | `local.yaml` 中 `test_strategy: skip` 不影响本 task | 手动执行 targeted pytest，不依赖 CI 配置 | 环境 |
