---
id: task-05
title: 实现 `build_features` + Tier4 cache 降级 + forecasters 训练
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-01]
blocks: [task-06]
requirement_ids: [FR-02]
decision_ids: [D-006@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  在训练窗口拟合 XGBoost 负荷 + LEAR 电价 forecaster，并解析 Tier4 weather 来源；cache 缺失时静默降级为 Tier3，weather_source 字段记录实际来源。
implementation:
  - 函数签名 `build_features(load_df, price_df, tier="tier4", weather_cache_path=None) -> (xgb_forecaster, lear_forecaster, feature_cols, weather_source)`
  - 调用 `prepare_features(load_df, tiers=tier_list, weather_cache_path=weather_cache_path, fetch_if_missing=False)`；tier_list 由 tier 决定（tier3 → [tier1,tier2,tier3]；tier4 → [tier1,tier2,tier3,tier4]）
  - tier="tier3" 时 weather_source="skipped"；tier="tier4" 时根据 FeatureEngineer 内部状态推断 "cache" 或 "degraded"（实现：检查默认 cache 路径 exists 且 prepare_features 后 df 含 weather 列 → "cache"；否则 "degraded"）
  - 用 `engineer.get_feature_columns(tier)` 取列表
  - 实例化并训练 `XGBoostForecaster()` (load) + `LEARForecaster()` (price)；仅在训练窗口数据上 fit
  - 返回 4 元组
acceptance:
  - test_build_features_tier3_no_weather：tier="tier3" 时 weather_source=="skipped"，feature_cols 不含 temp_*
  - test_build_features_tier4_cache_hit：cache 存在时 weather_source=="cache"
  - test_build_features_tier4_degraded：cache 路径指向不存在文件时 weather_source=="degraded"，不抛异常
verify:
  - pytest tests/test_train_rl_full_dataset.py -q -k build_features
constraints:
  - 不调 WeatherFetcher 的网络抓取（fetch_if_missing=False 强制）
  - 不修改 prepare_features / FeatureEngineer 公开 API
  - forecaster 训练失败 → 允许返回 None forecaster + 在 weather_source 后追加 "(forecaster-failed)" 标记；下游 env 可接受 None
