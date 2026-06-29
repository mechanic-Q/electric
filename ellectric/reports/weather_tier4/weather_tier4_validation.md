# Weather Tier4 Validation Report

*Generated: 2026-06-29T13:09:15Z | Data source: shandong*

## Metadata

- **generated_at**: 2026-06-29T13:09:15Z
- **data_source**: shandong
- **data_version**: 1
- **time_config**: freq=15min, points_per_day=96
- **start**: None
- **end**: None
- **weather_source**: degraded
- **input_rows**: 96
- **report_scope**: full_dataset
- **log_path**: —

## Weather Quality

- **weather_source**: degraded
- **weather_features_available**: False
- **weather_column_count**: 0
- **weather_columns**: (none)
- **overall_missing_rate**: 0.0%
- **time_range**: start=2026-01-01 00:00:00+00:00, end=2026-01-01 23:45:00+00:00, freq=15min
- **timezone**: UTC
- **coverage_ratio**: 0.0%
- **notes**:
  - Weather source is degraded: no weather data available
  - No weather columns found in feature_df after merge

## Experiment Comparison

### Metrics Comparison

| Metric | Baseline Tier3 | Weather Tier4 | Delta | Delta % |
|--------|---------------|--------------|-------|---------|
| MAE | 10.0000 | — | — | — |
| RMSE | 15.0000 | — | — | — |
| MAPE | 5.00 | — | — | — |

### Config Comparison

| Config | Baseline Tier3 | Weather Tier4 |
|--------|---------------|--------------|
| Feature Count | 30 | 35 |
| Input Rows | 96 | 96 |
| Sample Count | 86 | 0 |
| Weather Columns | — | — |

## Delta

No significant improvement observed in this run.

## Impact Conclusion

Weather 分支不可用或训练失败，Impact 无法量化；baseline 结果仍可用作参考。
本报告为 report-only：不设硬性精度提升阈值（hard_threshold_applied=false），delta 正负如实呈现，结论仅描述本次实验观察到的事实。

## Interpretation

This validation is report-only — hard thresholds are not enforced.

Weather Tier4 features serve as an optional enhancement layer for load forecasting. This run reports metrics without requiring hard accuracy improvement thresholds. The baseline uses Tier1-3 features; the experiment adds Tier4 weather features. Model selection, feature engineering, and hyperparameter tuning may yield different results.

**Summary**: Ablation: degraded (weather features unavailable or training failed)

## Notes

- Weather source is degraded: no weather data available
- No weather columns found in feature_df after merge
- No weather data available
