---
author: lmr
created_at: 2026-06-23T19:10:00+08:00
---

# Requirements — 时间分辨率参数化

## 角色

| 角色 | 描述 |
|---|---|
| Pipeline Developer | 修改 5 个文件以适配 TimeConfig |
| 用户/研究者 | 切换 TimeConfig 后能直接跑 15min 现货数据 |

## 功能需求

### FR-001 — 全局配置类

**Given** 需要在小时级（24/168/"h"）和 15min（96/672/"15min"）之间切换
**When** `from ellectric.config import TimeConfig`
**Then** 类提供 3 个属性：
- `points_per_day: int = 24`
- `points_per_week: int = 168`
- `freq: str = "h"`

### FR-002 — trading_env.py 参数化

**Given** `ElectricityMarketEnv` 实例化
**When** 读取 `TimeConfig.points_per_day` / `points_per_week` / `freq`
**Then** action_space、observation_space、price_history、`pd.date_range()` 全部跟随配置变化

### FR-003 — features.py 参数化

**Given** 调用 `FeatureEngineer.add_tier1_features()` / `add_tier2_features()`
**When** 计算 `shift()` / `rolling()` 时
**Then** `shift(TimeConfig.points_per_day)`、`shift(TimeConfig.points_per_week)`、`rolling(TimeConfig.points_per_day)`、`rolling(TimeConfig.points_per_week)`

### FR-004 — forecaster.py 参数化

**Given** 调用 `persistence_forecast(df)`
**When** 执行 `shift()` 时
**Then** `df["load_mw"].shift(TimeConfig.points_per_day)`

### FR-005 — price_forecaster.py 参数化

**Given** 调用 LEAR 训练或特征工程
**When** 执行 5 处 `shift(24)` 或 `shift(168)` 时
**Then** 全部替换为 `TimeConfig.points_per_day` / `points_per_week`

### FR-006 — cleaner.py 参数化

**Given** `clean_data(df)` 调用 `standardize_frequency()`
**When** 比较频率
**Then** 比较 `freq == TimeConfig.freq`（非硬编码 "h"）；重采样目标也用 `TimeConfig.freq`

### FR-007 — 默认行为不变（brownfield）

**Given** 不修改 `TimeConfig` 默认值
**When** 运行现有 notebook 或 verify 脚本
**Then** 所有输出与变更前完全一致（24 点/天、168 点/周、"h"）

## 非功能需求

### NFR-001 — 性能
- TimeConfig 类读取不引入额外开销（属性查询 O(1)）

### NFR-002 — 代码风格
- 遵循 `CONVENTIONS.md`：类型标注、docstring、中英双语
- TimeConfig 用类属性（不用 dataclass / pydantic），保持依赖最小

### NFR-003 — 兼容性
- 不修改 `data_loader.py` / `shanxi_loader.py` / `cli/main.py` / `api/server.py`
- 不修改 `requirements.txt`

### NFR-004 — 切换原子性
- 用户只需修改 `TimeConfig` 一处即可切换全部 pipeline 行为

## 决策覆盖

| Requirement | Decision | 说明 |
|---|---|---|
| FR-001 | D-001@v1 | 全局配置单例（方案 A） |
| FR-002~FR-006 | D-002@v1 | 逐文件精确替换（方案 1） |
| FR-007 | D-003@v1 | 默认值保持 24/168/"h" 向后兼容 |
