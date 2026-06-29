---
author: lmr
created_at: 2026-06-29 20:40:04
---

# Proposal

## 动机

Weather Tier4 已经接入 FeatureEngineer，并已有验证脚本与报告格式，但当前报告仍是 degraded/fake-scale 状态，无法证明气象特征在山东 15min 全量数据上的真实精度影响。

本变更要把 Weather Tier4 从“可接入、可验证结构”推进到“可复现量化影响”：在全量山东数据上比较 Tier3 baseline 与 Tier3+weather，并输出可信指标、报告和日志证据。

## 关键问题

1. **现有报告不代表全量真实数据**
   - 当前 `weather_tier4_validation.json` 显示 `input_rows=96`、`weather_source=degraded`、weather metrics 为 null。
   - 这不能回答 Weather Tier4 在 71,520 行山东 15min 数据上的精度影响。

2. **现有 weather 分支可能混入 raw columns**
   - `run_ablation_experiment()` 当前从 Tier4 feature_df 中取除 `timestamp/load_mw` 外全部列作为 weather 模型特征。
   - 山东 loader 原始列可能包含价格、出力、预测等非 weather 信号，会污染“天气特征本身贡献”的结论。

3. **报告语义不够清晰**
   - `metadata.data_source` 当前复用 weather source，无法区分负荷数据源和天气来源。
   - full-run 日志路径未结构化记录，后续难以追溯验证证据。

## 变更范围

- 修正 `run_ablation_experiment()`，只比较 Tier3 columns 与 Tier3 + 实际 weather columns。
- 扩展 validation report metadata，区分 `data_source=shandong` 和 `weather_source`。
- 在报告中记录 `input_rows`、`report_scope`、`log_path`、`weather_columns`。
- 更新 Markdown 报告，加入 Impact Conclusion。
- 增加测试覆盖 raw columns 不泄漏、metadata schema、weather columns 记录。
- 更新 feature-engineer 模块文档，说明本验证是隔离 weather 特征的 ablation。
- 运行 full-run，生成 JSON/Markdown/log 证据。

## 不在范围内（显式清单）

- 不新增天气数据源。
- 不更换 Open-Meteo。
- 不改 WeatherFetcher 抓取逻辑。
- 不把 Weather Tier4 改成必选特征。
- 不调参、不做模型选择、不持久化生产模型。
- 不把价格、风光出力、日前预测等 raw columns 纳入 weather impact 实验。
- 不改 FastAPI、CLI、LLM、RL、backtester 流程。
- 不引入定时任务、daemon、队列或实时数据调度。

## 成功标准（可验证）

- `run_ablation_experiment()` 的 weather 模型特征列等于 Tier3 columns + weather columns，不含 raw Shandong columns。
- JSON 报告包含 `metadata.data_source="shandong"`、`metadata.weather_source`、`metadata.input_rows`、`metadata.report_scope`、`metadata.log_path`。
- JSON 报告包含 `experiments.weather_tier4.weather_columns`。
- `experiments.weather_tier4.feature_count == baseline_tier3.feature_count + len(weather_columns)`。
- Markdown 报告包含 Impact Conclusion，说明 MAE delta 正负与 report-only 语义。
- `rtk pytest tests/test_weather_tier4_validation.py` 通过。
- full-run 命令生成 `ellectric/reports/weather_tier4/weather_tier4_validation.json`、`.md`、`weather_tier4_impact.log`。
- 未修改 FeatureEngineer、prepare_features、XGBoostForecaster、ShandongDataLoader 的公开签名。
