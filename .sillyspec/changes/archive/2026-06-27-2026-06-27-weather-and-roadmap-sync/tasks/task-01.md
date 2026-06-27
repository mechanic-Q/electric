---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-01
title: 新增 weather feature 契约测试
priority: P0
depends_on: []
blocks:
  - task-02
  - task-03
  - task-09
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
  - tests/__init__.py
  - tests/conftest.py
---

# Task-01: 新增 weather feature 契约测试

## 修改文件

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `tests/test_weather_features.py` | 全部测试代码，先写失败测试 |
| 可选 | `tests/__init__.py` | 若不存在 `import` 兼容问题则保持不动 |

只写测试文件。不写 `features.py`、`weather.py` 或其导入链中任何模块的实现。

## 覆盖来源

| 需求/决策 | 覆盖方式 |
|---|---|
| FR-001 | Tier4 方法调用测试：`FeatureEngineer.add_tier4_weather_features(df, weather_df=...)` 返回包含 weather columns 的 DataFrame |
| FR-002 | cache 命中不触网 + cache 缺失且 `fetch_if_missing=False` 降级 + cache 缺失且 `fetch_if_missing=True` 调用 `WeatherFetcher.fetch_historical()` |
| FR-003 | 00:45 边界 ffill 对齐 + timestamp index/列两种输入 |
| FR-004 | `get_feature_columns("tier4")` + `prepare_features(df, tiers=[..., "tier4"])` |
| D-006@v2 | `prepare_features(df, tiers=["tier1"])` 旧行为不变 |
| D-007@v2 | cache 策略 + 00:45 safe ffill |

## 实现要求

### 测试层设计

测试分 5 组（每组一段注释分隔 + 独立函数），严格按此顺序：

### Group A: Tier4 显式 weather_df 合并（FR-001, FR-003）

```python
# ── Group A: Tier4 explicit weather_df merge (FR-001, FR-003) ──

def test_add_tier4_weather_df_only():
    """weather_df 显式传入时，返回 DataFrame 包含天气列。"""
    ...

def test_add_tier4_preserves_tier1_tier2_tier3():
    """Tier4 不破坏已存在的 Tier1-3 特征。"""
    ...

def test_add_tier4_handles_timestamp_index():
    """weather_df 的 index 为 timestamp（兼容 `fetch_historical()` 输出格式）。"""
    ...

def test_add_tier4_no_weather_df_warns():
    """weather_df 与 cache 均未提供时记录 warning 而非抛异常。"""
    ...
```

### Group B: Cache 命中/缺失策略（FR-002, D-007@v2）

```python
# ── Group B: Cache hit/miss (FR-002, D-007@v2) ──

def test_add_tier4_cache_hit_no_network():
    """cache parquet 存在时从文件读取，不触网。"""
    ...

def test_add_tier4_cache_miss_fetch_false_degrades():
    """cache 缺失 + fetch_if_missing=False 不抛异常，返回原 df。"""
    ...

def test_add_tier4_cache_miss_fetch_true_calls_fetch():
    """cache 缺失 + fetch_if_missing=True 触发 WeatherFetcher.fetch_historical() 调用。"""
    ...
```

### Group C: 15min 边界对齐（FR-003, D-007@v2）

```python
# ── Group C: 15min boundary alignment (FR-003, D-007@v2) ──

def test_add_tier4_ffill_covers_0045():
    """小时级 weather 数据正确填充到 00:15, 00:30, 00:45 三个子点。"""
    ...
```

### Group D: get_feature_columns tier4（FR-004, D-006@v2）

```python
# ── Group D: get_feature_columns tier4 (FR-004, D-006@v2) ──

def test_get_feature_columns_tier4_includes_weather():
    """DataFrame 有 weather columns 时 get_feature_columns("tier4") 返回包含它们。"""
    ...

def test_get_feature_columns_tier4_missing_weather_dropped():
    """DataFrame 无 weather columns 时 get_feature_columns("tier4") 只返回 Tier1-3 列。"""
    ...
```

### Group E: prepare_features 兼容性（FR-001, FR-003, D-006@v2）

```python
# ── Group E: prepare_features tier4 + backward compat (FR-001, FR-003, D-006@v2) ──

def test_prepare_features_tier4_default_cache():
    """prepare_features(df, tiers=[..., 'tier4']) 使用默认 cache path 工作。"""
    ...

def test_prepare_features_tier1_unchanged():
    """prepare_features(df, tiers=['tier1']) 与旧调用行为一致（不新增 weather 参数）。"""
    ...
```

### 每个测试函数必须包含失败断言

在被测函数/类还未实现时，测试必须能运行但断言失败。例如：

```python
def test_add_tier4_weather_df_only():
    df = _sample_load_df(96)
    weather_df = _fake_weather_hourly()
    eng = FeatureEngineer()
    result = eng.add_tier4_weather_features(df, weather_df=weather_df)
    assert "temp_jinan" in result.columns  # ← 此断言预期失败
```

## 接口定义

测试层面对以下方法签名做契约断言：

### FeatureEngineer.add_tier4_weather_features()

```python
def add_tier4_weather_features(
    self,
    df: pd.DataFrame,
    weather_df: pd.DataFrame | None = None,
    weather_cache_path: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> pd.DataFrame: ...
```

语义约束（测试必须验证）：
- `df` 有 `timestamp` 列
- `weather_df` 可为 `pd.DataFrame`（index 为 timestamp 或含 `timestamp` 列），可为 `None`
- `weather_cache_path=None` 时指向默认 cache 路径
- `fetch_if_missing=False` 且 cache 缺失 → 记录 warning、返原 df、不触网
- 返回 DataFrame 包含原始列 + 已有特征列 + 天气列

### FeatureEngineer.get_feature_columns()

```python
def get_feature_columns(self, tier: str = "tier1") -> list: ...
```

- `tier="tier4"` 返回 Tier1-3 特征列 + 当前 df 中实际存在的 weather columns
- weather columns 不存在时不返回（不构造假列名）

### prepare_features()

```python
def prepare_features(
    df: pd.DataFrame,
    tiers: list | None = None,
    weather_df: pd.DataFrame | None = None,
    weather_cache_path: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> pd.DataFrame: ...
```

- `tiers` 含 `"tier4"` → 按序执行 Tier1→Tier4
- `tiers` 不含 `"tier4"` → 完全旧行为，不依赖 weather 参数

## 边界处理

1. **空 weather_df**: `weather_df` 为空的 `pd.DataFrame()` → 返回无 weather columns 的原 df
2. **weather_df 只有部分城市/变量**: 只添加存在的列，不报错
3. **00:45 缺失**: 使用带 `30min` 容差的 `reindex(method='ffill', tolerance='30min')` 会导致 00:45 为 NaN；测试必须确保 Tier4 对齐方案修复此问题（验证 `ffill` 无容差或恰当容差覆盖整小时）
4. **天气列与特征列同名冲突**: 假设不冲突，不覆盖
5. **cache 文件损坏** (非 parquet /空文件) → 不抛异常，记录 warning，返原 df
6. **Tier4 在 Tier1/2/3 之前调用**: 期望 `prepare_features` 内部保证执行顺序；直接调用 `add_tier4_weather_features` 只合并 weather 列不添加基础特征
7. **UTC timestamp 与 Asia/Shanghai timestamp**: 假设 df 的 timestamp 带 UTC tz，在 reindex 时 pandas 自动处理 timezone 对齐
8. **fetch_if_missing=True 但网络失败**: 同 cache 缺失 + fetch_if_missing=False 行为 — warning + 原 df 返回
9. **get_feature_columns("tier4") 在未调用 add_tier4 前调用**: 返回 Tier1-3 列，不包含天气列（无状态，基于当前 df 推算）
10. **prepare_features old signature 向前兼容**: 只用 `(df,)` 和 `(df, tiers=['tier1'])` 调用，不引入 `tier` 字符串新签名

## 非目标

- 不写入任何 `add_tier4_weather_features` 实现逻辑
- 不修改 `features.py`、`weather.py`、`__init__.py` 等源码文件
- 不创建真实 parquet cache 文件（用 `tmp_path` / `monkeypatch` / `io.BytesIO`）
- 不测试 Open-Meteo 网络连通性
- 不修改 `test_time_resolution_15min.py`
- 不考虑 `pytest.mark` 或 fixtures 之外的测试框架配置
- 不添加 `conftest.py` 全局 fixture（除非已有模式证明必要）

## 参考

- `tests/test_time_resolution_15min.py` — 本项目 pytest 模式（纯函数、`_sample_load_df` helper、`monkeypatch`、`tmp_path`、原始 `assert`）
- `ellectric/pipeline/features.py` — `FeatureEngineer`、`prepare_features`、现有 Tier1-3 `get_feature_columns` 签名
- `ellectric/fetch/weather.py` — `WeatherFetcher.fetch_historical()` 输出格式（index=timestamp, 城市列），`align_to_15min()` 现有 `tolerance="30min"` 缺陷
- `ellectric/config.py` — `TimeConfig.points_per_day=96, points_per_week=672`

## TDD 步骤

1. 创建 `tests/test_weather_features.py`
2. 实现 Group A（4 个测试函数）：只写断言失败（无实现）
3. 实现 Group B（3 个测试函数）：cache 策略签约
4. 实现 Group C（1 个测试函数）：00:45 边界签约
5. 实现 Group D（2 个测试函数）：get_feature_columns tier4 签约
6. 实现 Group E（2 个测试函数）：prepare_features 兼容性签约
7. 运行 `pytest tests/test_weather_features.py --collect-only` 确认测试发现 12 个
8. 运行 `pytest tests/test_weather_features.py -v` 确认全部失败（因无实现）

## 验收标准表格

| # | 标准 | 验证方式 | 覆盖 |
|---|---|---|---|
| 1 | `test_add_tier4_weather_df_only` 断言 weather columns 出现在返回 df | pytest 预期失败 | FR-001 |
| 2 | `test_add_tier4_preserves_tier1_tier2_tier3` 断言基础特征列不被清除 | pytest 预期失败 | FR-001 |
| 3 | `test_add_tier4_handles_timestamp_index` 断言 index-based weather_df 正确合并 | pytest 预期失败 | FR-003 |
| 4 | `test_add_tier4_no_weather_df_warns` 断言 log warning 而非异常 | pytest 预期失败 | FR-001 |
| 5 | `test_add_tier4_cache_hit_no_network` 断言 cache 文件读完、未调用 `fetch_historical` | pytest 预期失败 | FR-002, D-007@v2 |
| 6 | `test_add_tier4_cache_miss_fetch_false_degrades` 断言返回 df 无 weather 列 | pytest 预期失败 | FR-002, D-007@v2 |
| 7 | `test_add_tier4_cache_miss_fetch_true_calls_fetch` 断言 `fetch_historical` 被 mock 记录 | pytest 预期失败 | FR-002, D-007@v2 |
| 8 | `test_add_tier4_ffill_covers_0045` 断言 00:45 与 00:00 的值相等（同一小时） | pytest 预期失败 | FR-003, D-007@v2 |
| 9 | `test_get_feature_columns_tier4_includes_weather` 断言返回列表包含 `temp_jinan` | pytest 预期失败 | FR-004, D-006@v2 |
| 10 | `test_get_feature_columns_tier4_missing_weather_dropped` 断言不包含不存在的天气列 | pytest 预期失败 | FR-004, D-006@v2 |
| 11 | `test_prepare_features_tier4_default_cache` 断言 `prepare_features(df, tiers=[..., 'tier4'])` 返回含天气列的 df | pytest 预期失败 | FR-001, FR-003, D-006@v2 |
| 12 | `test_prepare_features_tier1_unchanged` 断言旧签名调用返回不含天气列的基础 df | pytest 预期失败 | D-006@v2 |
| 13 | pytest 发现 12 个测试用例 | `pytest --collect-only` 输出 | — |
| 14 | 全部测试由于无实现而失败 | `pytest -v` 输出全 FAIL 或 ERROR | — |
| 15 | 不写入任何非 `tests/` 的源码文件 | `git diff --name-only` 检查 | — |
