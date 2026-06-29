---
id: task-01
title: 修正 Weather Tier4 ablation 特征隔离
author: lmr
created_at: 2026-06-29 20:44:11
priority: P0
depends_on: []
blocks: [task-04, task-06]
requirement_ids: [FR-01, FR-02]
decision_ids: [D-002@v1]
allowed_paths: [ellectric/scripts/validate_weather_tier4.py]
---

goal: >
  Weather 分支只使用 Tier3 + weather 列，禁止 raw Shandong
  columns（rt_price/da_price/wind_actual_mw）泄漏到 X_weather。

implementation:
  - baseline 不变：prepare_features(tiers=[1,2,3]) + X_baseline = df[tier3_cols]
  - weather 用专用 FeatureEngineer，按序 add_tier1→2→3→4_weather_features
  - X_weather = df[tier3_cols + engineer._weather_columns]，禁止全列
  - 无 weather 列时 degraded（metrics null），baseline 正常返回

acceptance:
  - X_weather 不含 rt_price/da_price/wind_actual_mw
  - X_weather.columns == tier3_cols + _weather_columns
  - weather_tier4.feature_count == baseline_tier3.feature_count + len(weather_columns)

verify:
  - rtk pytest tests/test_weather_tier4_validation.py

constraints:
  - 只改 validate_weather_tier4.py
  - 不动 FeatureEngineer/XGBoostForecaster/ShandongDataLoader 公开签名
  - JSON 只增 weather_tier4.weather_columns，不删旧字段
