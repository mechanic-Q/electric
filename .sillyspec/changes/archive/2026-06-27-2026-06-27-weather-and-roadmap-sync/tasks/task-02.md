---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-02
title: 修正 WeatherFetcher 15min 对齐边界
priority: P0
depends_on:
  - task-01
blocks:
  - task-03
  - task-09
requirement_ids:
  - FR-003
decision_ids:
  - D-007@v2
allowed_paths:
  - ellectric/fetch/weather.py
---

# Task-02: 修正 WeatherFetcher 15min 对齐边界

## 修改文件

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `ellectric/fetch/weather.py` | 仅修改 `align_to_15min()` 方法体 |

只改 `weather.py:193` 一行及相关的 docstring。保持 public signature 不变。

## 覆盖来源

| 需求/决策 | 覆盖方式 |
|-----------|----------|
| FR-003 | 小时级 weather 经 `align_to_15min()` 对齐后，每小时 4 个 15min 点（00:00/00:15/00:30/00:45）均有值 |
| D-007@v2 | 废除 `tolerance="30min"` 容差，改用无容差 `method='ffill'`，确保 00:45 不被遗漏 |

## 实现要求

### 根因

`weather.py:193`:
```python
aligned = weather.reindex(shandong_index, method="ffill", tolerance="30min")
```

`tolerance="30min"` 的含义：目标索引点与最近的前向源点之间时间差若超过 30min，ffill 结果为 NaN。

小时级 weather 示例时间轴：`00:00`, `01:00`, `02:00`, ...
15min 目标时间轴：`00:00`, `00:15`, `00:30`, `00:45`, `01:00`, ...

对于目标点 `00:45`，前向源点为 `00:00`，间距 45min > 30min → NaN。
对于目标点 `01:00`，前向源点为 `01:00`（精确匹配）→ 有值。
因此每小时第 4 个 15min 点（`:45`）全部缺失，实际对齐后每 4 行仅 3 行有效。

### 修正方案

删除 `tolerance="30min"` 参数，改用纯 ffill：

```python
aligned = weather.reindex(shandong_index, method="ffill")
```

语义变化：
- 之前：只有间距 ≤30min 才 ffill（:45 丢失）
- 之后：每个 15min 点都从最近的上一个小时 weather 值前向填充

### 保留元素

- public signature 完全不变：

  ```python
  def align_to_15min(
      self,
      weather: pd.DataFrame,
      shandong_index: pd.DatetimeIndex,
  ) -> pd.DataFrame:
  ```

- 参数名、类型、返回值类型不变
- `null_pct > 5` warning 逻辑保留（对因时间范围不对齐导致的真正缺失仍有防御作用）
- docstring 更新以反映新的对齐语义

## 接口定义

### WeatherFetcher.align_to_15min()

```python
def align_to_15min(
    self,
    weather: pd.DataFrame,
    shandong_index: pd.DatetimeIndex,
) -> pd.DataFrame:
```

- `weather`: `fetch_historical()` 返回的 DataFrame，index 为 UTC DatetimeIndex（小时级）
- `shandong_index`: 目标时间轴（15min 级 UTC DatetimeIndex）
- 返回：与 `shandong_index` 行数相同的 DataFrame，每个 15min 点都有从最近小时 weather 前向填充的值
- 当 weather 时间范围完全不含 shandong_index 范围时，`null_pct` 仍会触发 warning

### 与其他模块的隐含契约

- 此方法被 task-03 `FeatureEngineer.add_tier4_weather_features()` 调用，用于 cache 缺失时对齐 weather 数据
- task-01 的 `test_add_tier4_ffill_covers_0045` 将验证 00:45 与 00:00 值相等（同一小时）
- 本次修正使该测试从"预期失败"变为"预期通过"

## 边界处理

1. **weather 时间范围小于 shandong_index**: 时间范围外无前向源点 → 真实 NaN，不受 ffill 影响，由 null_pct warning 保护
2. **weather 时间范围大于 shandong_index**: 多余部分自然截断（reindex 只保留目标索引中的点），无副作用
3. **weather 完全为空 (0 行)**: reindex 返回全 NaN 帧，null_pct = 100%，触发 warning，调用方需处理（Tier4 降级策略覆盖）
4. **weather index 带 Asia/Shanghai tz 而非 UTC**: pandas reindex 对 tz-aware index 自动对齐到 UTC 当量，不影响 ffill 计算结果
5. **shandong_index 含重复时间戳**: reindex 行为取决于具体数据；假设调用方时间轴已去重（Tier4 调用前由 ShandongDataLoader 保证）
6. **weather index 非 monotonic**: reindex 前未排序可能导致意外结果；但 `fetch_historical()` 返回已通过 `_merge_cities` 中的 `sort_index()` 保证 monotonic
7. **ffill 后 null_pct 略大于 0**: 不抛异常，仅 logging warning（由调用方决定是否降级）
8. **tolerance 移除后回退行为**: 旧代码调用者（暂无实际调用点，仅 graphify 索引）不会因 signature 不变而 break
9. **极端情况——weather 只有一行数据**: ffill 将该行值传播到目标时间轴全部行，逻辑正确但数据无意义——由调用方负责确保时间范围匹配
10. **method='ffill' 与 limit 参数**: 当前不设 limit，允许跨多缺失小时 ffill；若未来需要限制 ffill 跨度，由 Tier4 对齐层决定，`align_to_15min` 保持简单

## 非目标

- 不改变 `fetch_historical()`、`_fetch_city()`、`_merge_cities()` 或其他方法
- 不添加新方法或新参数
- 不改变 `__init__` 签名或类属性
- 不修改 `WeatherFetcher` 的缓存、网络重试或降级逻辑
- 不新增测试文件（测试由 task-01 的 `test_add_tier4_ffill_covers_0045` 覆盖）
- 不修改 `features.py`、`config.py` 或其他模块

## 参考

- `weather.py:177-197` — `align_to_15min()` 完整定义（待修改目标）
- `weather.py:170-173` — `_merge_cities()` 中已有 `ffill(limit=6)` 对 `method='ffill'` 风格的前置参考
- `tasks/task-01.md` — Group C `test_add_tier4_ffill_covers_0045` 是此 fix 的测试契约
- `design.md:168` — R-04b 风险登记
- `decisions.md:105-116` — D-007@v2 决策详情

## TDD 步骤

1. 确认 task-01 测试已写好且 `test_add_tier4_ffill_covers_0045` 预期失败（因当前实现有 tolerance 缺陷，该测试直接调用 Tier4 链路间接验证 `align_to_15min` 行为；或独立编写验证）
2. 修改 `weather.py:193`: 将 `tolerance="30min"` 删除，改为无容差 `method="ffill"`
3. 更新 `align_to_15min()` 的 docstring，删除关于 tolerance 的隐含说明，明确 00:45 等边界已被覆盖
4. 运行 `pytest tests/test_weather_features.py::test_add_tier4_ffill_covers_0045 -v` 确认测试通过
5. 运行完整测试套件 `pytest tests/ -v` 确认回归通过
6. 运行 `git diff ellectric/fetch/weather.py` 确认变更仅限目标行 + docstring

## 验收标准表格

| # | 标准 | 验证方式 | 覆盖 |
|---|------|----------|------|
| 1 | `tolerance="30min"` 参数被移除 | `grep 'tolerance.*30min' ellectric/fetch/weather.py` 返回空 | D-007@v2 |
| 2 | `align_to_15min()` public signature 不变 | 参数名、类型、返回值不变，tolerance 未出现在新签名中 | FR-003 |
| 3 | 00:45 与 00:00 值相等（同一 hour ffill） | task-01 `test_add_tier4_ffill_covers_0045` 通过 | FR-003, D-007@v2 |
| 4 | 所有现有测试通过 | `pytest tests/ -v` 无新增失败 | FR-003 |
| 5 | `null_pct > 5` warning 保留 | 代码含 `logger.warning` 且逻辑不变 | FR-003 |
| 6 | 仅 `weather.py` 被修改 | `git diff --stat` 只显示 `weather.py` 且行数变化 ≤ 5 行 | — |
| 7 | docstring 更新反映无容差 ffill 语义 | `grep 'tolerance' ellectric/fetch/weather.py` 仅在 docstring 描述移除原因时出现 | — |
