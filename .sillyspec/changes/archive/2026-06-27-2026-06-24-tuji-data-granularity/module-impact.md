---
author: lmr
created_at: 2026-06-27 15:32:17
---

# Module Impact: 图迹/山东 15min 数据粒度全面迁移

## 模块影响矩阵

注：`.sillyspec/docs/Electric/modules/_module-map.yaml` 不存在，按 prompt 建议运行 scan 生成模块映射。以下基于 `docs/Ellectric/modules/` 模块卡片匹配。

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| cleaner | 逻辑变更 | `ellectric/pipeline/cleaner.py` | `standardize_frequency()` 使用 `TimeConfig.freq`，不再硬编码 `h` | false |
| feature-engineer | 逻辑变更 | `ellectric/pipeline/features.py` | lag/rolling 窗口使用 `TimeConfig.points_per_day/points_per_week` | false |
| price-forecaster | 逻辑变更 | `ellectric/pipeline/price_forecaster.py` | 电价 lag/rolling/gap 使用 TimeConfig；默认 gap=TimeConfig.points_per_day | false |
| forecaster | 逻辑变更 | `ellectric/pipeline/forecaster.py` | XGBoost gap 默认 TimeConfig；persistence 文档/日志同步 | false |
| trading-env | 逻辑变更 | `ellectric/pipeline/trading_env.py` | action/observation/docstring 使用 TimeConfig；`start >= 24` 改 TimeConfig.points_per_day | false |
| backtester | 逻辑变更 | `ellectric/pipeline/backtester.py` | 基线策略 hardcoded 24/168 改 TimeConfig | false |
| shandong_loader | 接口变更 | `ellectric/pipeline/shandong_loader.py` | metadata 明确 granularity=15min, points_per_day=96 | false |
| price-loader | 调用关系变更 | `ellectric/service/handlers.py` | handler 新增 `_load_price_data()` 统一 price 数据源 | false |
| data-loader | 调用关系变更 | `ellectric/service/handlers.py` | handler 新增 `_load_forecast_data()` 统一 load 数据源 | false |
| — | 新增 | `tests/test_time_resolution_15min.py` | 15min 时间分辨率覆盖测试 | false |
| — | 文档变更 | `docs/Ellectric/modules/*.md` | forecaster/price-forecaster/trading-env/notebooks/feature-engineer 模块卡片同步 | false |

## 未匹配文件

| 文件 | 说明 |
|------|------|
| `ellectric/config.py` | TimeConfig 类属性文档修正（默认值 15min），非模块卡片覆盖 |
| `ellectric/cli/main.py` | horizon 文案更新（小时跨度语义） |
| `ellectric/llm/tools.py` | horizon 文案更新（小时跨度语义） |
| `ellectric/scripts/run_demo.py` | gap 参数同步到 TimeConfig.points_per_day |
| `ellectric/scripts/verify_time_resolution.py` | 验证脚本硬编码断言更新 |
| `ellectric/service/handlers.py` | 主要逻辑变更：新增 helper + horizon 换算 + shandong data_source |
| `ellectric/service/schemas.py` | ExplainRequest 新增 data_source 字段；forecast/backtest schema 默认 shandong |
| `ellectric/api/server.py` | API 路由层，未修改 |
| `ellectric/README.md` | 文案更新，非模块卡片覆盖 |
