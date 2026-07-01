# Weather Tier4 Validation Report

*Generated: 2026-07-01T05:11:22Z | Data source: shandong*

## Metadata

- **generated_at**: 2026-07-01T05:11:22Z
- **data_source**: shandong
- **data_version**: 1
- **time_config**: freq=15min, points_per_day=96
- **start**: None
- **end**: None
- **weather_source**: cache
- **input_rows**: 71520
- **report_scope**: full_dataset
- **log_path**: ellectric/reports/weather_tier4/weather_tier4_impact.log

## Weather Quality

- **weather_source**: cache
- **weather_features_available**: True
- **weather_column_count**: 12
- **weather_columns**: temp_jinan, ghi_jinan, wind_speed_jinan, precip_jinan, humidity_jinan, cloud_jinan, temp_qingdao, ghi_qingdao, wind_speed_qingdao, precip_qingdao, humidity_qingdao, cloud_qingdao
- **overall_missing_rate**: 0.0%
- **time_range**: start=2024-01-01 00:15:00+00:00, end=2026-01-15 00:00:00+00:00, freq=15min
- **timezone**: UTC
- **coverage_ratio**: 100.0%

## Experiment Comparison

### Metrics Comparison

| Metric | Baseline Tier3 | Weather Tier4 | Delta | Delta % |
|--------|---------------|--------------|-------|---------|
| MAE | 3368.1659 | 2661.7841 | -706.3819 | -20.97 |
| RMSE | 4958.6506 | 4057.2990 | -901.3515 | — |
| MAPE | 5.18 | 4.03 | -1.15 | — |

### Config Comparison

| Config | Baseline Tier3 | Weather Tier4 |
|--------|---------------|--------------|
| Feature Count | 11 | 23 |
| Input Rows | 71520 | 71520 |
| Sample Count | 59600 | 59600 |
| Weather Columns | — | temp_jinan, ghi_jinan, wind_speed_jinan, precip_jinan, humidity_jinan, cloud_jinan, temp_qingdao, ghi_qingdao, wind_speed_qingdao, precip_qingdao, humidity_qingdao, cloud_qingdao |

## Delta

MAE: baseline=3368.1659, weather=2661.7841, delta=-706.3819 (-20.97%)
RMSE: baseline=4958.6506, weather=4057.2990, delta=-901.3515
MAPE: baseline=5.18%, weather=4.03%, delta=-1.15%

## Impact Conclusion

MAE delta 为负，表示加入 weather 特征后预测误差下降，Weather Tier4 在本次实验中改善了负荷预测精度。
本报告为 report-only：不设硬性精度提升阈值（hard_threshold_applied=false），delta 正负如实呈现，结论仅描述本次实验观察到的事实。

## Interpretation

This validation is report-only — hard thresholds are not enforced.

Weather Tier4 features serve as an optional enhancement layer for load forecasting. This run reports metrics without requiring hard accuracy improvement thresholds. The baseline uses Tier1-3 features; the experiment adds Tier4 weather features. Model selection, feature engineering, and hyperparameter tuning may yield different results.

**Summary**: Ablation: baseline MAE=3368.17, weather MAE=2661.78, delta=-706.38 (-20.97%)

## Notes

- Weather X isolated to tier3 + weather columns; raw Shandong columns excluded
