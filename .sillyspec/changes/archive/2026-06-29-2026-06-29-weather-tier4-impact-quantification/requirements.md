---
author: lmr
created_at: 2026-06-29 20:40:04
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 开发者 | 运行验证脚本和测试，确认 Weather Tier4 影响量化可信 |
| 学习者 | 阅读 Markdown 报告，理解天气特征是否改善负荷预测 |
| 维护者 | 依赖 JSON 报告和日志追踪 full-run 证据，避免未来回归 |

## 功能需求

### FR-01: Weather-only ablation 特征隔离

覆盖决策：D-002@v1

Given 输入 DataFrame 包含 `timestamp`、`load_mw`、Tier 特征可生成所需基础列，并可能包含 `rt_price`、`da_price`、`wind_actual_mw` 等 raw columns
When 调用 `run_ablation_experiment(load_df, weather_cache=..., fetch_if_missing=...)`
Then baseline 模型只使用 Tier3 feature columns
And weather 模型只使用 Tier3 feature columns + 实际 weather columns
And weather 模型不使用 `rt_price`、`da_price`、`wind_actual_mw` 等 raw columns

Given 无可用 weather columns
When 调用 `run_ablation_experiment(...)`
Then baseline_tier3 仍正常返回
And weather_tier4 标记 degraded，metrics 为 null

### FR-02: 指标 delta 与 weather columns 记录

覆盖决策：D-001@v1, D-002@v1

Given baseline_tier3 与 weather_tier4 都产生 predictions/actuals
When `run_ablation_experiment()` 计算结果
Then 返回 MAE、RMSE、MAPE
And 返回 `mae_delta = weather_mae - baseline_mae`
And 返回 `mae_delta_pct = mae_delta / baseline_mae * 100`，baseline MAE 为 0 时为 null
And `experiments.weather_tier4.weather_columns` 列出本次真正加入模型的 weather 列
And `weather_tier4.feature_count == baseline_tier3.feature_count + len(weather_columns)`

### FR-03: 报告 metadata 区分数据源和天气源

覆盖决策：D-001@v1, D-003@v1, D-004@v1

Given `run_validation()` 成功加载山东 15min 数据
When 构建 validation result
Then `metadata.data_source == "shandong"`
And `metadata.weather_source` 为 `cache|fetch|explicit|degraded` 之一
And `metadata.weather_source == weather_quality.weather_source`
And `metadata.input_rows == len(load_df)`
And `metadata.report_scope` 为 `full_dataset` 或 `custom_range`
And `metadata.log_path` 为 full-run 日志路径或测试场景中的 null

### FR-04: Markdown 报告解释 impact conclusion

覆盖决策：D-001@v1

Given validation result 包含 baseline/weather metrics 和 delta
When 写入 Markdown 报告
Then 报告包含 Impact Conclusion 段落
And 段落说明 MAE delta 为负表示 weather 改善、为正表示 weather 退化
And 段落说明本验证是 report-only，不设置硬性精度提升门槛

Given weather_tier4 degraded
When 写入 Markdown 报告
Then 报告说明 weather features unavailable 或 training failed
And baseline 结果仍可读

### FR-05: Full-run 证据产物

覆盖决策：D-003@v1, D-004@v1

Given 本地存在 `ellectric/data/shandong/weather_2024-2026.parquet`
When 运行 `python ellectric/scripts/validate_weather_tier4.py --no-fetch --output-dir ellectric/reports/weather_tier4 2>&1 | tee ellectric/reports/weather_tier4/weather_tier4_impact.log`
Then 生成 `ellectric/reports/weather_tier4/weather_tier4_validation.json`
And 生成 `ellectric/reports/weather_tier4/weather_tier4_validation.md`
And 生成 `ellectric/reports/weather_tier4/weather_tier4_impact.log`
And 报告不是 degraded/fake-scale 证据，除非日志明确说明 cache 缺失或训练失败并已修复/记录

### FR-06: API 兼容与回退

覆盖决策：D-001@v1, D-004@v1

Given 现有代码调用 `run_validation()` 或 `run_ablation_experiment()` 的旧参数
When 本变更完成后继续调用
Then 参数签名保持兼容
And JSON 报告只增加字段，不删除旧字段
And weather cache 缺失且 `--no-fetch` 时 baseline 不阻断
And FeatureEngineer、prepare_features、XGBoostForecaster、ShandongDataLoader 的公开签名不变

## 非功能需求

- 兼容性：不修改现有公开函数参数；报告字段只增不删。
- 可回退：weather 缺失时降级为 baseline-only 报告，不阻断脚本。
- 可测试：新增单元测试覆盖 raw column 不泄漏、metadata 扩展、weather columns 记录。
- 可复现：最终验证优先使用本地 weather cache 和 `--no-fetch`，不依赖网络。
- 可追溯：full-run 日志保存在 `ellectric/reports/weather_tier4/weather_tier4_impact.log`。
- 性能边界：允许 full-run 较慢，但 unit tests 必须快速且不触网。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-02, FR-03, FR-04, FR-06 | report-only，不设硬性精度提升阈值 |
| D-002@v1 | FR-01, FR-02 | Weather impact 只允许 Tier3 + weather columns，不混入 raw columns |
| D-003@v1 | FR-03, FR-05 | full-run 证据日志写入 reports 目录并进入 metadata |
| D-004@v1 | FR-03, FR-05, FR-06 | full-run 优先离线 cache，不依赖网络 |
