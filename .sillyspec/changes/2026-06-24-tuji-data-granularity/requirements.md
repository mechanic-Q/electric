---
author: lmr
created_at: 2026-06-26 21:12:40
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 学习者 | 通过 notebook、CLI、API 运行山东 15min 电力数据预测/回测流程。 |
| 开发者 | 维护 pipeline、forecast、trading env、API/CLI/文档的一致时间分辨率语义。 |
| 课程作者 | 依赖稳定的数据合约和文档，编排 AI+电力交易学习路径。 |

## 功能需求

### FR-001: 山东 15min 数据作为 canonical 高频数据资产

覆盖决策：D-001@v1, D-002@v1, D-004@v1, D-005@v1

Given 项目存在 `ellectric/data/shandong/山东_2024-2026_15min.csv`
When 学习者或系统通过 `ShandongDataLoader.load_data()` 加载数据
Then 返回 DataFrame 包含 `timestamp`, `load_mw`, `rt_price`, `da_price`, `province`, `source`, `granularity`，且 `granularity == "15min"`

Given API/CLI/LLM 路径需要默认高频学习数据
When 未显式指定其他兼容数据源
Then 默认数据源应指向或等效使用 `shandong`

### FR-002: TimeConfig 作为时间分辨率唯一来源

覆盖决策：D-001@v1, D-003@v1, D-004@v1

Given 代码需要表达一天、一周或目标频率
When 实现 lag、rolling、gap、action shape 或 frequency alignment
Then 必须使用 `TimeConfig.points_per_day`, `TimeConfig.points_per_week`, `TimeConfig.freq`，不得新增独立硬编码 `24/168/h` 作为点数来源

Given `TimeConfig` 默认配置
When 读取其类属性
Then `points_per_day == 96`, `points_per_week == 672`, `freq == "15min"`

### FR-003: 清洗频率规范化不强制小时级降采样

覆盖决策：D-001@v1, D-003@v1, D-004@v1

Given 输入 DataFrame 时间戳为规则 15min 间隔
When 调用 `standardize_frequency(df)`
Then 输出仍保持 15min 粒度，不应被 resample 到小时级

Given 输入 DataFrame 频率和 `TimeConfig.freq` 不一致
When 调用 `standardize_frequency(df)`
Then 系统应按 `TimeConfig.freq` 对齐或报告，不能静默固定到 `"h"`

### FR-004: 特征与预测窗口按 15min 点数计算

覆盖决策：D-001@v1, D-003@v1, D-004@v1

Given 15min 负荷数据至少包含 96 个时间点
When 调用 `FeatureEngineer.add_tier1_features(df)`
Then `lag_24h` 使用 `shift(TimeConfig.points_per_day)`，即 96 点

Given 15min 负荷数据至少包含 672 个时间点
When 调用 `FeatureEngineer.add_tier2_features(df)`
Then `lag_168h` 使用 `shift(TimeConfig.points_per_week)`，即 672 点

Given 15min 数据构造滚动统计
When 调用 Tier3 或价格特征工程
Then 24h rolling 使用 96 点窗口，7d trend 使用 672 点窗口

Given XGBoost 或 LEAR 训练使用 TimeSeriesSplit gap
When 默认训练 15min 数据
Then gap 应与 24h lag 防泄漏语义一致，即默认 96 点或显式由调用方传入 96

### FR-005: TradingEnv 使用 96 点/日动作与观测

覆盖决策：D-001@v1, D-003@v1, D-004@v1

Given `TimeConfig.points_per_day == 96`
When 初始化 `ElectricityMarketEnv`
Then `action_space.shape == (96,)`，`load_forecast_24h` 和 `price_forecast_24h` 的 shape 也为 `(96,)`

Given 用户传入错误长度 action
When 调用 `env.step(action)`
Then 报错信息应引用 `TimeConfig.points_per_day` 或当前点数，不应写死 “24 维”

Given `TimeConfig.points_per_week == 672`
When 构建 price history observation
Then `price_history_168h` shape 为 `(672,)`

### FR-006: 接口与文档保持 15min 语义一致

覆盖决策：D-001@v1, D-004@v1, D-005@v1

Given 用户通过 CLI/API/LLM 查询 forecast horizon
When 输入 `horizon=24`
Then 系统解释为 24 小时时间跨度，而不是 24 个 15min 数据点

Given 代码文档、README、module cards、notebooks 描述当前 MVP
When 用户阅读或运行学习路径
Then 文案应明确当前 canonical 数据为山东 15min，不应把主路径误写为小时级或 OWID 年级数据

Given API handler 收到 `data_source="shandong"`
When 执行 forecast/backtest/explain 路径
Then 应使用山东 15min 数据加载路径或明确返回不支持错误，不能忽略字段固定使用 OWID

### FR-007: 15min 迁移具备最小验证覆盖

覆盖决策：D-001@v1, D-003@v1, D-004@v1, D-005@v1

Given 新增测试文件 `tests/test_time_resolution_15min.py`
When 运行项目测试
Then 应覆盖 TimeConfig 默认值、15min frequency preservation、lag/rolling 窗口、TradingEnv action shape、schema/handler 数据源语义

Given 本变更只做文档与小范围代码迁移
When 验证完成
Then 不应要求真实外部 API、GPU、Docker 或商业数据访问

## 非功能需求

- 兼容性：保留现有 public class/function 名称；保留 `lag_24h`、`load_forecast_24h` 等字段名作为时间跨度语义。
- 可回退：OWID/ChineseDataLoader/EmberLoader 兼容路径不删除，旧数据可显式指定使用。
- 可测试：核心迁移通过小型合成 15min DataFrame 测试，不依赖完整 CSV。
- 可维护：不引入通用多频率平台；优先替换硬编码常量，保持实现简单。
- 文档一致性：所有用户可见说明必须区分“小时跨度”和“15min 点数”。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007 | 用户确认目标为现有流程升级到 15min。 |
| D-002@v1 | FR-001, FR-006, FR-007 | 确认山东 15min CSV 是 canonical 高频数据资产。 |
| D-003@v1 | FR-002, FR-003, FR-004, FR-005, FR-007 | 确认 TimeConfig 是 SSOT，硬编码需清理。 |
| D-004@v1 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007 | 用户选择全面 15min 迁移方案。 |
| D-005@v1 | FR-001, FR-006, FR-007 | Design Grill 确认 API 数据源语义必须进入 schema/handler。 |
