---
author: lmr
created_at: 2026-06-28 00:57:11
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 学习者 | 运行验证脚本，阅读报告，理解 Weather Tier4 对负荷预测的影响 |
| 开发者 | 维护验证脚本、测试和报告 schema |
| 后续自动化流程 | 读取 JSON 报告，未来可在此基础上增加硬阈值或 CI 检查 |

## 功能需求

### FR-01: 可复现验证脚本入口

覆盖决策：D-003@v1

Given 项目环境已安装核心依赖，且默认山东 15min 数据存在  
When 学习者运行 `python ellectric/scripts/validate_weather_tier4.py`  
Then 脚本加载默认数据，执行 Weather Tier4 validation，并生成 JSON 和 Markdown 报告。

Given 学习者指定 `--output-dir`  
When 脚本完成运行  
Then 报告写入指定目录，且返回/打印报告路径。

### FR-02: Weather 数据质量报告

覆盖决策：D-002@v1, D-003@v1

Given weather cache 存在或 Open-Meteo 抓取成功  
When 脚本构造 Tier4 特征  
Then JSON 报告的 `weather_quality` 包含 weather_source、weather_features_available、weather_columns、weather_column_count、missing_rate_by_column、overall_missing_rate、notes。

Given weather 数据合并到 15min 负荷时间轴  
When 报告生成  
Then 报告记录时间范围、时区、覆盖范围和对齐后缺失情况。

### FR-03: Baseline vs Tier4 指标对比

覆盖决策：D-001@v1, D-003@v1

Given 默认山东 15min 数据可加载  
When 脚本运行实验  
Then 脚本使用同一默认数据、同一模型配置、同一 TimeSeriesSplit 语义比较 baseline_tier3 与 weather_tier4。

Given `XGBoostForecaster.train_evaluate()` 返回 predictions 和 actuals  
When 脚本计算指标  
Then JSON 报告包含 MAE、RMSE、MAPE，以及 mae_delta、rmse_delta、mape_delta、mae_delta_pct。

Given 交叉验证评估样本数小于输入行数  
When 报告生成  
Then `input_rows` 表示原始输入行数，`sample_count` 表示参与 actual/prediction 指标计算的样本数。

### FR-04: Report-only 验收语义

覆盖决策：D-001@v1, D-002@v1

Given Weather Tier4 指标未优于 baseline  
When 脚本完成运行  
Then 脚本不因精度未提升而失败，报告中 `hard_threshold_applied=false`。

Given weather cache 缺失且 `--no-fetch` 被使用  
When 脚本构造 Tier4 特征  
Then 脚本记录 degraded，`weather_features_available=false`，并仍输出 baseline 结果和报告。

### FR-05: 报告格式稳定

覆盖决策：D-003@v1

Given 验证脚本完成运行  
When 开发者或自动化流程读取 JSON 报告  
Then 报告包含 `metadata`、`weather_quality`、`experiments`、`interpretation` 四个顶层字段。

Given Markdown 报告生成  
When 学习者打开报告  
Then 报告以文字说明 weather 质量检查、指标对比、delta 和“无硬阈值”解释。

### FR-06: 兼容现有 API 和行为

覆盖决策：D-002@v1

Given 未运行新增验证脚本  
When 现有 notebooks、测试、API 或 CLI 使用 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster`  
Then 行为与变更前保持一致。

Given 现有测试 `tests/test_weather_features.py` 运行  
When 新增验证脚本后执行测试  
Then 原有 Weather Tier4 契约测试仍通过。

## 非功能需求

- 兼容性：不得修改现有公开 API 签名。
- 可回退：新增报告为派生产物，可删除后重新生成。
- 可测试：脚本核心逻辑拆成可测试函数，测试不依赖真实网络。
- 可复现：报告记录数据源、时间范围、TimeConfig、feature_count、sample_count。
- 可解释：Markdown 报告说明 Weather Tier4 是可选增强，不保证精度提升。
- 轻量化：不引入后台进程、数据库或新服务。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-03, FR-04 | 指标只报告，不设硬性提升阈值 |
| D-002@v1 | FR-02, FR-04, FR-06 | Tier4 可选增强，缺失时降级且保持兼容 |
| D-003@v1 | FR-01, FR-02, FR-03, FR-05 | 采用脚本化验证和 JSON/Markdown 报告 |
