---
author: lmr
created_at: 2026-06-26 21:12:40
---

# Design: 图迹/山东 15min 数据粒度全面迁移

## 背景

Electric 当前 MVP 已从年级/小时级学习数据推进到山东 15 分钟级现货数据：`ellectric/data/shandong/山东_2024-2026_15min.csv`，覆盖 2024-01-01 至 2026-01-14，745 天 × 96 点/日。代码中已经存在 `ShandongDataLoader` 和 `TimeConfig`，但仍残留部分小时级假设，例如滚动窗口写死 `24/168`、错误信息写死 `24 维`、文档/CLI/API 仍使用小时级表达。

本变更解决的问题：把现有小时级数据模型迁移到 15min 粒度，确保 pipeline、预测、交易环境、接口文案与测试对齐同一个时间分辨率语义。

## 设计目标

- FR-001: 山东 15min 数据作为当前 canonical 高频数据资产，加载结果稳定输出 `timestamp`, `load_mw`, `rt_price`, `da_price` 和出力相关列。
- FR-002: `TimeConfig` 继续作为时间分辨率 Single Source of Truth，统一表达 `points_per_day=96`, `points_per_week=672`, `freq="15min"`。
- FR-003: 清洗与频率规范化不再把非小时级数据强制重采样到小时级。
- FR-004: 负荷特征、电价特征、持续法预测、LEAR/XGBoost 训练窗口全部使用 `TimeConfig`，不再写死 24/168 点窗口。
- FR-005: 交易环境的 observation/action 维度使用 96 点/日、672 点/周，用户文案保留“未来 24h/过去 168h”的业务含义。
- FR-006: CLI/API/notebook/README 中的粒度、维度、错误信息与 15min 语义一致。
- FR-007: 新增最小测试覆盖 15min lag、rolling、frequency、trading action shape。

## 非目标

- 不做通用多频率平台，不新增复杂 runtime 配置系统。
- 不自动把低质量小时级数据插值成可训练的 15min 真值数据。
- 不引入数据库、消息队列或生产级数据版本治理。
- 不重写模型架构，不新增大模型、深度学习或 RL 新算法。
- 不改真实市场结算逻辑，仅保持学习型模拟。

## 拆分判断

无需拆分。原因：本变更围绕单一目标“现有小时级流程迁移到 15min 粒度”，涉及多个文件但属于同一数据合约迁移，不存在 3+ 个可独立交付功能模块、3+ 角色视图、跨页面状态流转，也不是模板 × 数据的批量任务。

## 总体方案

### Wave 1: 时间分辨率合约收敛

保留 `TimeConfig` 作为唯一入口，修正其文档与真实默认值一致。代码中所有表示“一天/一周点数”的地方统一使用 `TimeConfig.points_per_day` 和 `TimeConfig.points_per_week`；所有表示 pandas 目标频率的地方统一使用 `TimeConfig.freq`。不新增通用频率抽象，避免把当前迁移扩大成框架工程。

### Wave 2: Pipeline 与特征迁移

`ShandongDataLoader` 继续负责 15min CSV 的字段映射、`24:00` 修正和 metadata 注入。`cleaner.standardize_frequency()` 改为按 `TimeConfig.freq` 对齐，不能再把推断出的非小时级数据重采样到 `h`。`features.py` 和 `price_forecaster.py` 的 lag/rolling 窗口迁移到 `TimeConfig`，尤其是 `rolling_mean_24h`, `rolling_std_24h`, `rolling_mean_24h_price`, `7d_price_mean` 等字段名保持业务含义，窗口值变为 96/672 点。

### Wave 3: Forecast 与 Trading 迁移

`persistence_forecast()` 已使用 `TimeConfig.points_per_day`，需要同步日志与文档。`XGBoostForecaster` 和 `PriceForecaster` 的默认 `gap`、训练说明、评估图文案改成 15min 语义。`TradingEnv` 的 `action_space`、forecast observation、price history 使用 `TimeConfig`，错误信息从“24 维”改为“TimeConfig.points_per_day 维”。内部 key 可暂保留 `load_forecast_24h` 等名称，因为它表达时间跨度 24h，不表达数组长度 24。

### Wave 4: 接口、Notebook、文档与测试

CLI/API 中用户可见参数仍以小时为单位描述，例如 `horizon=24` 表示 24 小时时间跨度；内部如需要点数，应换算成 `horizon_hours * TimeConfig.points_per_day / 24`。API 契约实际由 `service/schemas.py` 和 `service/handlers.py` 承担：`ForecastRequest.data_source` / `BacktestRequest.data_source` 需要支持或默认指向 `shandong`，handler 不能继续无视 data_source 后固定加载 OWID。Notebook 与 README 更新为山东 15min 学习路径。新增测试用小型 15min DataFrame 验证：1 天 = 96 点、1 周 = 672 点、lag/rolling/standardize_frequency/trading action shape 均符合预期。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `ellectric/config.py` | 修正文档与默认值一致，明确 15min 当前默认。 |
| 修改 | `ellectric/pipeline/cleaner.py` | `standardize_frequency()` 使用 `TimeConfig.freq`，删除强制小时级重采样逻辑。 |
| 修改 | `ellectric/pipeline/features.py` | rolling/lag 统一使用 `TimeConfig`；保留业务字段名。 |
| 修改 | `ellectric/pipeline/price_forecaster.py` | 价格特征 rolling、7d 均值、默认 gap 和说明迁移到 15min。 |
| 修改 | `ellectric/pipeline/forecaster.py` | 日志/注释/说明与 15min 点数一致。 |
| 修改 | `ellectric/pipeline/trading_env.py` | action/observation 维度错误信息和内部切片语义统一 96/672 点。 |
| 修改 | `ellectric/pipeline/shandong_loader.py` | 如需补充 metadata，明确 granularity 和 points_per_day。 |
| 修改 | `ellectric/cli/main.py` | 用户文案说明 horizon 为小时跨度，内部点数不写死。 |
| 修改 | `ellectric/service/schemas.py` | Forecast/Backtest data_source 默认值与描述支持山东 15min；horizon 保持小时语义。 |
| 修改 | `ellectric/service/handlers.py` | Forecast/Backtest/Explain 根据 data_source 使用山东 15min loader，不再固定 OWID。 |
| 修改 | `ellectric/api/server.py` | API 文案/响应说明与 15min 时间跨度一致。 |
| 修改 | `ellectric/llm/tools.py` | 工具说明中预测 horizon 保留小时语义，必要时传递 data_source。 |
| 修改 | `ellectric/README.md` | 当前 MVP 与学习路径保持山东 15min 口径。 |
| 修改 | `docs/Ellectric/modules/*.md` | 模块文档中的小时级/24维/168小时残留说明同步。 |
| 修改 | `ellectric/notebooks/*.ipynb` | Notebook 文案和示例窗口改为 15min 语义。 |
| 新增 | `tests/test_time_resolution_15min.py` | 覆盖 TimeConfig、lag、rolling、frequency、TradingEnv action shape。 |

## 接口定义

### 既有配置接口

```python
class TimeConfig:
    points_per_day: int = 96
    points_per_week: int = 672
    freq: str = "15min"
```

本变更不要求新增 public API。实现时优先替换硬编码常量，不引入通用频率配置层。

### 既有数据加载接口

```python
class DataLoader(ABC):
    def load_data(self, ...) -> pd.DataFrame: ...
    def get_metadata(self) -> dict: ...
```

`ShandongDataLoader.load_data()` 输出 DataFrame 必须包含：

```text
timestamp: datetime64[ns, UTC]
load_mw: float64
rt_price: float64
da_price: float64
province: "shandong"
source: "user-provided-csv"
granularity: "15min"
```

### 既有 API Schema 接口

```python
class ForecastRequest(BaseModel):
    model_type: Literal["load", "price"]
    horizon: int = 24
    data_source: str = "shandong"

class BacktestRequest(BaseModel):
    start_date: date
    finish_date: date  # 设计文档别名；实现使用既有字段
    strategy: Literal[...]
    data_source: str = "shandong"
```

`horizon` 表示小时跨度，不表示返回点数。15min 数据下 24 小时应对应最多 96 个时间点。

### 既有特征接口

```python
FeatureEngineer.add_tier1_features(df) -> pd.DataFrame
FeatureEngineer.add_tier2_features(df) -> pd.DataFrame
FeatureEngineer.add_tier3_features(df) -> pd.DataFrame
PriceForecaster.add_price_features(df, tier="tier1") -> pd.DataFrame
```

字段名如 `lag_24h`, `lag_168h`, `rolling_mean_24h` 表示时间跨度，不表示固定 24/168 个数据点。

## 数据模型

无数据库表结构变更。DataFrame 合约如下：

| 列 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `timestamp` | datetime64[ns, UTC] | 是 | 15min 对齐时间戳。 |
| `load_mw` | float64 | 是 | 直调负荷实际值。 |
| `rt_price` | float64 | 否 | 实时价格，主要价格信号。 |
| `da_price` | float64 | 否 | 日前价格，约 25% 覆盖率。 |
| `is_holiday` | int | 否 | 山东数据原始节假日标记。 |
| 周末标记列 | int | 否 | 山东数据原始周末标记。 |
| `granularity` | str | 否 | 固定为 `15min`。 |
| `province` | str | 否 | 固定为 `shandong`。 |

## 兼容策略

- 保留现有 public class/function 名称，不重命名 `DataLoader`, `ShandongDataLoader`, `FeatureEngineer`, `XGBoostForecaster`, `PriceForecaster`, `TradingEnv`。
- 保留 `lag_24h`、`load_forecast_24h` 等字段名，因为它们表达 24 小时时间跨度；仅修正内部数组长度和窗口点数。
- CLI/API 的 `horizon` 仍按小时解释，避免破坏用户调用；内部需要点数时显式转换。
- 不删除 OWID/ChineseDataLoader/EmberLoader；旧低频数据路径可继续存在，但当前 MVP 以山东 15min 路径为主。
- 若输入数据频率不是 `TimeConfig.freq`，清洗层应报告或按配置对齐，不能默默降采样到小时级。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 字段名 `lag_24h` 被误解为 24 个点而不是 24 小时 | P1 | 在 design/docs/tests 中明确字段名表示时间跨度，窗口使用 `TimeConfig.points_per_day`。 |
| R-02 | `da_price` 75% 缺失导致价格模型误判为脏数据 | P1 | README/Notebook 强调这是数据发布粒度导致的预期稀疏，价格信号优先用 `rt_price`。 |
| R-03 | TradingEnv 错误信息和 shape 不一致 | P1 | 测试覆盖 action shape=96，错误信息引用 `TimeConfig.points_per_day`。 |
| R-04 | Notebook JSON 修改噪声大 | P2 | 只改必要文本/代码 cell，避免输出重跑造成大 diff。 |
| R-05 | 旧小时级示例数据与 15min 默认配置混用 | P1 | 明确当前 MVP 默认山东 15min；旧数据路径仅保留兼容，不作为主要 notebook 路径。 |

## 决策追踪

- D-001@v1 覆盖 FR-001, FR-002, FR-003, FR-004, FR-005：用户确认目标是将现有小时级数据模型升级到 15min 粒度。
- D-002@v1 覆盖 FR-001：代码/文档确认 canonical 高频数据资产为山东 15min CSV 与 `ShandongDataLoader`。
- D-003@v1 覆盖 FR-002, FR-004, FR-007：代码确认 `TimeConfig` 是 SSOT，但仍需清理硬编码窗口。
- D-004@v1 覆盖全部 FR：用户选择方案B，全面 15min 迁移。
- D-005@v1 覆盖 FR-001, FR-006, FR-007：Design Grill 确认 API 数据源语义必须落实到 `service/schemas.py` 与 `service/handlers.py`。

未解决决策：无。剩余实现风险见风险登记。

## 自审

| 检查项 | 结果 | 说明 |
|---|---|---|
| 需求覆盖 | 通过 | 覆盖用户选择 A：现有小时级流程升级到 15min。 |
| Grill 覆盖 | 通过 | design 引用 D-001@v1 至 D-005@v1。 |
| 约束一致性 | 通过 | 不引入生产系统、数据库或大模型。 |
| 真实性 | 通过 | 文件、类、方法来自现有代码；测试文件标注新增。 |
| YAGNI | 通过 | 明确不做通用多频率平台。 |
| 验收标准 | 通过 | FR-007 指向可测试项。 |
| 非目标清晰 | 通过 | 明确不做插值真值、通用平台、模型重写。 |
| 兼容策略 | 通过 | 保留 public API 和小时跨度字段名。 |
| 风险识别 | 通过 | 识别字段名、缺失价格、shape、notebook diff、旧数据混用风险。 |
| 特殊契约表 | 通过 | 本变更不涉及长期运行会话或租约类状态流。 |
