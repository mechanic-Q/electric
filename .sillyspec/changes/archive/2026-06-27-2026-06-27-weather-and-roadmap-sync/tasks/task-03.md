---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-03
title: 实现 FeatureEngineer Tier4 weather + cache 集成
priority: P0
depends_on:
  - task-01
  - task-02
blocks:
  - task-04
  - task-05
  - task-06
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
  - ellectric/pipeline/features.py
---

# Task-03: 实现 FeatureEngineer Tier4 weather + cache 集成

## 修改文件

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `ellectric/pipeline/features.py` | 新增 `add_tier4_weather_features()`，扩展 `get_feature_columns('tier4')`，扩展 `prepare_features()` |

## 覆盖来源

| 需求/决策 | 覆盖方式 |
|---|---|
| FR-001 | 新增 `add_tier4_weather_features()` 方法，weather 列作为可选层 |
| FR-002 | parquet cache 优先；cache 缺失可抓取或降级 |
| FR-003 | 小时级 weather 安全对齐到 15min，fix `align_to_15min` 30min 容差缺陷 |
| FR-004 | `get_feature_columns("tier4")` 返回实际存在的 weather 列；`prepare_features(tiers=[..., "tier4"])` 工作 |
| D-006@v2 | 兼容 `prepare_features(df, tiers=list)` 旧签名，不引入 `tier` 单数字符串参数 |
| D-007@v2 | cache 默认路径 `ellectric/data/shandong/weather_2024-2026.parquet`；00:45 safe ffill 对齐 |

task-03 是 task-01（契约测试）和 task-02（WeatherFetcher 15min 对齐修正）的实现方。测试的 12 个断言必须全部通过，旧 API 兼容性必须保持。

## 实现要求

### 1. `FeatureEngineer.add_tier4_weather_features(df, weather_df=None, weather_cache_path=None, fetch_if_missing=True)`

**签名：**

```python
def add_tier4_weather_features(
    self,
    df: pd.DataFrame,
    weather_df: pd.DataFrame | None = None,
    weather_cache_path: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> pd.DataFrame:
```

**语义：**

- `df` 必须包含 `timestamp` 列（带 UTC timezone）
- `weather_df`：可直接传入气象 DataFrame。可以是 index=timestamp（`fetch_historical()` 输出格式），或含 `timestamp` 列的 DataFrame
- `weather_cache_path=None` → 使用默认 cache 路径：`ellectric/data/shandong/weather_2024-2026.parquet`
- `fetch_if_missing=True` → cache 缺失时自动调用 `WeatherFetcher.fetch_historical()` 抓取并写入 cache
- `fetch_if_missing=False` → cache 缺失时记录 warning，返回原 df，不触网
- 返回 df 包含原始列 + 已有特征列 + weather columns

**执行流程（按优先级）：**

1. `weather_df` 非 None → 直接对齐并合并（跳过 cache 和网络）
2. `weather_cache_path` 指向有效 parquet → 读取后对齐并合并
3. cache 缺失 + `fetch_if_missing=True` → 调用 `WeatherFetcher.fetch_historical()` 抓取，写 cache，对齐合并
4. 以上均不可用 → 记录 warning，返回原 df

**对齐方法：**

不再直接依赖 `WeatherFetcher.align_to_15min(tolerance="30min")`。使用内部安全对齐：

```python
def _align_weather_to_15min(weather: pd.DataFrame, target_index: pd.DatetimeIndex) -> pd.DataFrame:
    # 无 tolerance 的 forward fill，确保每小时 4 个 15min 点均获得天气值
    aligned = weather.reindex(target_index, method="ffill")
    return aligned
```

### 2. `_weather_cache_path(path)` 辅助函数

类内部方法或模块级别函数：

```python
DEFAULT_WEATHER_CACHE = "ellectric/data/shandong/weather_2024-2026.parquet"

def _resolve_weather_cache(cache_path: str | Path | None) -> Path:
    if cache_path is not None:
        return Path(cache_path)
    # 相对于项目根目录解析；若 ellectric 不在 cwd 则用 Path(__file__).resolve()
    return Path(__file__).resolve().parents[2] / DEFAULT_WEATHER_CACHE
```

### 3. `get_feature_columns('tier4')` 扩展

```python
def get_feature_columns(self, tier: str = "tier1") -> list:
    feature_map = {
        "tier1": [...],
        "tier2": [...],
        "tier3": [...],
    }
    base = feature_map.get(tier, feature_map["tier1"])
    if tier == "tier4":
        # Tier1-3 列 + 当前 df 中实际存在的 weather 列
        weather_cols = [c for c in self._weather_columns if c in self._last_df_columns]
        return feature_map["tier3"] + weather_cols
    return base
```

注意：`get_feature_columns("tier4")` 需要访问实例状态。设计选择：
- `_weather_columns` 在 `add_tier4_weather_features` 调用后记录
- 未调用 `add_tier4` 前 `get_feature_columns("tier4")` 返回 Tier3 列

### 4. `prepare_features()` 扩展

```python
def prepare_features(
    df: pd.DataFrame,
    tiers: list | None = None,
    weather_df: pd.DataFrame | None = None,
    weather_cache_path: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> pd.DataFrame:
    if tiers is None:
        tiers = ["tier1"]

    engineer = FeatureEngineer()
    for tier in tiers:
        if tier == "tier1":
            df = engineer.add_tier1_features(df)
        elif tier == "tier2":
            df = engineer.add_tier2_features(df)
        elif tier == "tier3":
            df = engineer.add_tier3_features(df)
        elif tier == "tier4":
            # 确保 Tier1-3 已执行（可能调用者只传了 ['tier4']）
            if "tier1" not in tiers:
                df = engineer.add_tier1_features(df)
            if "tier2" not in tiers:
                df = engineer.add_tier2_features(df)
            if "tier3" not in tiers:
                df = engineer.add_tier3_features(df)
            df = engineer.add_tier4_weather_features(
                df,
                weather_df=weather_df,
                weather_cache_path=weather_cache_path,
                fetch_if_missing=fetch_if_missing,
            )

    return df
```

兼容性核心：额外参数全为默认值；`tiers` 不含 `"tier4"` 时走完全旧路径。

### 5. 项目根目录解析

默认 cache 路径 `ellectric/data/shandong/weather_2024-2026.parquet` 是相对于项目根目录的。使用 `Path(__file__).resolve()` 向上溯源定位 ellectric 包所在根目录，而非假设 `os.getcwd()`。

```python
def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]  # features.py → pipeline → ellectric → root
```

## 接口定义

### 新增方法

```python
def add_tier4_weather_features(
    self,
    df: pd.DataFrame,
    weather_df: pd.DataFrame | None = None,
    weather_cache_path: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> pd.DataFrame:
    """添加 Tier4 气象特征。

    Args:
        df: 包含 timestamp 列的 DataFrame
        weather_df: 可选，直接传入气象 DataFrame。
                    index 可为 timestamp 或含 timestamp 列。
        weather_cache_path: parquet cache 路径，None 使用默认
        fetch_if_missing: cache 缺失时是否自动抓取

    Returns:
        含 weather columns 的 DataFrame，或原 df（降级时）
    """
```

## 边界处理

1. **weather_df 为空 DataFrame**：`weather_df.columns` 为空时，返回无 weather 列的原 df，记录 debug 日志
2. **weather_df 只有部分城市/变量**：只合并 weather 列的子集，不报错；`get_feature_columns('tier4')` 只返回实际存在的列
3. **00:45 缺失**：采用 `reindex(target_index, method='ffill')` 无 tolerance 的 safe ffill，确保每小时 4 个 15min 点均获得天气值；不依赖 `align_to_15min(tolerance='30min')`
4. **timestamp index vs 列**：weather_df 的 index 为 DatetimeIndex 时直接用于对齐；有 `timestamp` 列时先 `set_index('timestamp')` 再对齐
5. **UTC timezone 对齐**：df 的 timestamp 和 weather 的 index 均应带 UTC tz。若存在 Asia/Shanghai → UTC 偏移，pandas reindex 自动处理
6. **cache 文件损坏**：非 parquet 格式 / 空文件 → `pd.read_parquet()` 可能抛出异常，用 try/except 捕获，记录 warning，返回原 df
7. **fetch_if_missing=True 但网络失败**：`WeatherFetcher.fetch_historical()` 内已有 try/except（返回空 DataFrame），对齐后无 weather 列可合并，记录 warning，返回原 df
8. **get_feature_columns("tier4") 在 add_tier4 前调用**：无 `_weather_columns` 或 `_last_df_columns` → 返回 Tier3 特征列列表
9. **prepare_features 只传 ['tier4']**：内部先执行 Tier1→Tier3 再执行 Tier4，调用者不用手动组合
10. **prepare_features 旧签名向后兼容**：只用 `(df,)` 或 `(df, tiers=['tier1'])` 调用时，weather 参数不被使用，行为与 task-03 之前完全一致

## 非目标

- 不修改 `WeatherFetcher` 核心抓取 API（`fetch_historical`/`align_to_15min` 保持 public，但 Tier4 内部不使用 `align_to_15min` 的 `tolerance='30min'` 路径）
- 不新增独立 `weather_features.py` 模块（职责仍放在 FeatureEngineer 内）
- 不训练模型、不承诺 weather 特征提升精度
- 不改变 `WeatherFetcher` 类的 import 路径或公开属性
- 不修改 `__init__.py` 导出（FeatureEngineer 已从 `ellectric.pipeline` 可见）
- 不做多城市扩展（济南/青岛之外的城市不在本轮）
- 不做 weather 特征缓存自动过期/版本管理

## 参考

- `ellectric/pipeline/features.py` — 现有 FeatureEngineer + prepare_features 实现
- `ellectric/fetch/weather.py` — WeatherFetcher 类、fetch_historical() 输出格式（index=timestamp, 城市列 _jinan/_qingdao）、align_to_15min() 缺陷
- `tests/test_weather_features.py` — task-01 契约测试（12 个测试，全部预期通过）
- `ellectric/config.py:TimeConfig` — `points_per_day=96`, `points_per_week=672`
- `design.md:101-158` — 接口定义、数据模型、兼容策略

## TDD 步骤

1. 确认 task-02 已完成（WeatherFetcher 15min 对齐修正，如果没有 task-02 则内部 safe ffill 替代）
2. 在 `FeatureEngineer.__init__` 中初始化 `self._weather_columns = []`
3. 在 `FeatureEngineer.add_tier4_weather_features` 中实现优先级 4 级逻辑：
   - 步骤 1: 解析 weather_cache_path（默认或显式）
   - 步骤 2: `weather_df` 直接使用逻辑
   - 步骤 3: cache 读取逻辑（`pd.read_parquet` + try/except）
   - 步骤 4: fetch_if_missing 抓取逻辑（WeatherFetcher 实例化 + fetch_historical + 写 cache）
   - 步骤 5: 内部安全对齐（reindex + ffill，无 tolerance）
   - 步骤 6: 合并 weather 列到 df
   - 步骤 7: 记录 `self._weather_columns = [实际合并的 weather 列]`
   - 步骤 8: 记录 `self._last_df_columns = [df.columns]` 用于 get_feature_columns
4. 在 `get_feature_columns` 中新增 `tier == "tier4"` 分支
5. 在 `prepare_features` 中新增 `"tier4"` case
6. 运行 `pytest tests/test_weather_features.py -v` 确认 12 个测试通过
7. 运行 `pytest tests/ -x --timeout=60` 确认无回归（需 `pytest-timeout` 可用，否则手动跳过网络测试）
8. 检查旧 API 兼容：`python -c "from ellectric.pipeline.features import prepare_features; df=__import__('pandas').DataFrame({'timestamp': __import__('pandas').date_range('2024-01-01', periods=96, freq='15min', tz='UTC'), 'load_mw': [100]*96}); df2=prepare_features(df, tiers=['tier1']); print(df2.columns.tolist())"`

## 验收标准表格

| # | 标准 | 验证方式 | 覆盖 |
|---|---|---|---|
| 1 | `test_add_tier4_weather_df_only` 通过 | `pytest tests/test_weather_features.py::test_add_tier4_weather_df_only -v` | FR-001 |
| 2 | `test_add_tier4_preserves_tier1_tier2_tier3` 通过 | pytest 通过 | FR-001 |
| 3 | `test_add_tier4_handles_timestamp_index` 通过 | pytest 通过 | FR-003 |
| 4 | `test_add_tier4_no_weather_df_warns` 通过 | pytest 通过 | FR-001 |
| 5 | `test_add_tier4_cache_hit_no_network` 通过 | pytest 通过 | FR-002, D-007@v2 |
| 6 | `test_add_tier4_cache_miss_fetch_false_degrades` 通过 | pytest 通过 | FR-002, D-007@v2 |
| 7 | `test_add_tier4_cache_miss_fetch_true_calls_fetch` 通过 | pytest 通过 | FR-002, D-007@v2 |
| 8 | `test_add_tier4_ffill_covers_0045` 通过 | pytest 通过 | FR-003, D-007@v2 |
| 9 | `test_get_feature_columns_tier4_includes_weather` 通过 | pytest 通过 | FR-004, D-006@v2 |
| 10 | `test_get_feature_columns_tier4_missing_weather_dropped` 通过 | pytest 通过 | FR-004, D-006@v2 |
| 11 | `test_prepare_features_tier4_default_cache` 通过 | pytest 通过 | FR-001, FR-003, D-006@v2 |
| 12 | `test_prepare_features_tier1_unchanged` 通过 | pytest 通过 | D-006@v2 |
| 13 | Tier1-3 旧测试全通过无回归 | `pytest tests/ -x --timeout=60 -k "not weather"` (排除 weather 测试) | D-006@v2 |
| 14 | 旧 `prepare_features(df, tiers=['tier1'])` 调用行为不变 | 脚本验证返回列不含天气列 | D-006@v2 |
| 15 | 不修改 `weather.py`、`__init__.py`、已存在的 `config.py` | `git diff --name-only` 仅包含 `features.py` | — |
