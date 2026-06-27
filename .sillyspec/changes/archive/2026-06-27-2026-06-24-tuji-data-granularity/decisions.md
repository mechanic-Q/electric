---
author: lmr
created_at: 2026-06-26 21:12:40
---

# Decisions: 图迹/山东 15min 数据粒度全面迁移

## D-001@v1: 目标是现有流程升级到 15min

- type: architecture
- status: accepted
- source: user
- question: “图迹数据粒度”具体想达成什么目标？
- answer: A：将现有小时级数据模型升级为 15min 粒度（Pipeline + 存储适配）。
- normalized_requirement: 现有数据 pipeline、预测、交易环境与接口文案应迁移到 15min 语义，而不是新增平行加载器或通用多频率平台。
- impacts: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007]
- evidence: Step 6 用户回答第 2 轮
- priority: P0

## D-002@v1: canonical 高频数据资产是山东 15min CSV

- type: data
- status: accepted
- source: code
- question: 本次迁移应围绕哪个真实高频数据资产？
- answer: 现有代码和数据文档已定义 `ShandongDataLoader` 与 `ellectric/data/shandong/山东_2024-2026_15min.csv`。
- normalized_requirement: 设计与实现以山东 15min CSV 为当前 MVP canonical 数据资产，`ShandongDataLoader` 输出标准 DataFrame 合约。
- impacts: [FR-001, FR-006, FR-007]
- evidence: `ellectric/pipeline/shandong_loader.py`, `ellectric/data/shandong/README.md`
- priority: P0

## D-003@v1: TimeConfig 是时间分辨率 SSOT，但需清理残留硬编码

- type: architecture
- status: accepted
- source: code
- question: 时间粒度迁移应新增配置系统还是复用现有入口？
- answer: 现有 `TimeConfig` 已声明为 Single Source of Truth，默认值为 15min；但 `features.py`, `price_forecaster.py`, `trading_env.py`, `cleaner.py` 仍存在硬编码窗口或小时级提示。
- normalized_requirement: 继续使用 `TimeConfig`，优先替换硬编码 `24/168/h` 语义，不引入新的通用配置系统。
- impacts: [FR-002, FR-003, FR-004, FR-005, FR-007]
- evidence: `ellectric/config.py`, `ellectric/pipeline/features.py`, `ellectric/pipeline/price_forecaster.py`, `ellectric/pipeline/trading_env.py`, `ellectric/pipeline/cleaner.py`
- priority: P0

## D-004@v1: 选择方案B：全面 15min 迁移

- type: architecture
- status: accepted
- source: user
- question: 在保守补齐、全面迁移、通用频率层三种方案中选择哪一种？
- answer: 用户选择方案B：全面 15min 迁移。
- normalized_requirement: 本变更应覆盖 pipeline、forecast、trading env、CLI/API/notebook 与文档中的 15min 语义一致性。
- impacts: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007]
- evidence: Step 8 用户回答
- priority: P0

## D-005@v1: API 数据源语义必须进入 schemas/handlers

- type: consistency
- status: accepted
- source: design-grill
- question: 设计中只提 CLI/API 文案，但真实 API 数据源选择在哪里生效？
- answer: `server.py` 只是路由层，实际契约和加载逻辑在 `service/schemas.py` 与 `service/handlers.py`；当前 handlers 固定加载 OWID，和山东 15min canonical 目标冲突。
- normalized_requirement: `ForecastRequest` / `BacktestRequest` 的 data_source 应支持或默认指向 `shandong`，handlers 根据 data_source 加载山东 15min 数据，不再忽略该字段。
- impacts: [FR-001, FR-006, FR-007]
- evidence: `ellectric/service/schemas.py`, `ellectric/service/handlers.py`, design.md Wave 4
- priority: P1
