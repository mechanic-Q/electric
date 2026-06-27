---
author: lmr
created_at: 2026-06-26 21:25:00
plan_level: full
---

# 实现计划

## Wave 1 — 时间分辨率合约收敛

TimeConfig 是 SSOT，所有后续任务依赖它对频率和窗口语义的一致表达。

- [x] T-001: 校准 TimeConfig 文档与默认值（覆盖：FR-002, D-003@v1）
  - 文件：`ellectric/config.py`, `ellectric/scripts/verify_time_resolution.py`
  - 修正 config.py 文档字符串，确认默认值 96/672/15min
  - 同步更新 verify_time_resolution.py 中硬编码的 24/h 断言
- [x] T-002: 修正清洗频率规范化逻辑（覆盖：FR-003, D-003@v1, D-004@v1）
  - 文件：`ellectric/pipeline/cleaner.py`
  - `standardize_frequency()` 使用 `TimeConfig.freq` 对齐，删除 `resample("h")` 降采样路径
- [x] T-007: 补强山东 15min loader metadata 合约（覆盖：FR-001, D-002@v1）
  - 文件：`ellectric/pipeline/shandong_loader.py`
  - metadata 明确 `granularity=15min`、`points_per_day=96`

## Wave 2 — Pipeline 与 Forecast/Trading 迁移

依赖 Wave 1 完成（TimeConfig 已校准）。各任务之间无交叉依赖，可并行执行。

- [x] T-003: 迁移负荷特征窗口到 TimeConfig（覆盖：FR-004, D-003@v1, D-004@v1）
  - 文件：`ellectric/pipeline/features.py`
  - `lag_24h` 使用 `shift(TimeConfig.points_per_day)`，`lag_168h` 使用 `shift(TimeConfig.points_per_week)`；rolling 窗口使用 96/672 点；保留字段名表示时间跨度
- [x] T-004: 迁移电价特征窗口与训练 gap（覆盖：FR-004, D-003@v1, D-004@v1）
  - 文件：`ellectric/pipeline/price_forecaster.py`
  - `lag_24h_price/lag_168h_price/rolling_mean_24h_price/price_trend_7d` 使用 TimeConfig；训练 gap 与 24h 防泄漏语义一致
- [x] T-005: 迁移负荷预测训练 gap 与文案（覆盖：FR-004, D-003@v1, D-004@v1）
  - 文件：`ellectric/pipeline/forecaster.py`
  - 日志/文档说明中点数语义改为 15min；gap 默认值 96
- [x] T-006: 迁移 TradingEnv 动作与观测维度语义（覆盖：FR-005, D-003@v1, D-004@v1）
  - 文件：`ellectric/pipeline/trading_env.py`
  - action/observation shape 使用 TimeConfig；错误信息引用 `TimeConfig.points_per_day` 而非写死 "24 维"

## Wave 3 — 接口层迁移

依赖 Wave 1（TimeConfig）。Wave 2 非必须前置，但建议 Wave 2 完成后进入以确保语义一致。

- [x] T-008: 更新 service schema 数据源与 horizon 语义（覆盖：FR-006, D-005@v1）
  - 文件：`ellectric/service/schemas.py`
  - `ForecastRequest.data_source` 默认 `"shandong"`；`horizon` 说明明确为小时跨度
- [x] T-009: 更新 service handlers 使用 shandong data_source（覆盖：FR-001, FR-006, D-002@v1, D-005@v1）
  - 文件：`ellectric/service/handlers.py`
  - 根据 `req.data_source` 选择山东 15min loader，不再固定加载 OWID
- [x] T-010: 更新 CLI/API/LLM 用户可见文案（覆盖：FR-006, D-005@v1）
  - 文件：`ellectric/cli/main.py`, `ellectric/api/server.py`, `ellectric/llm/tools.py`
  - 粒度描述、错误信息与 15min 语义一致

## Wave 4 — 文档与测试

与 Wave 1-3 可并行。

- [x] T-011: 更新 README、module docs、notebook 15min 语义（覆盖：FR-006, D-001@v1, D-004@v1）
  - 文件：`ellectric/README.md`, `docs/Ellectric/modules/*.md`, `ellectric/notebooks/*.ipynb`
  - 文案明确山东 15min 为当前 MVP canonical 路径
- [x] T-012: 新增 15min 时间分辨率测试（覆盖：FR-007, D-003@v1, D-005@v1）
  - 文件：`tests/test_time_resolution_15min.py`
  - 覆盖 TimeConfig 默认值、15min frequency preservation、lag/rolling 窗口、TradingEnv action shape

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D |
|---|---|---|---|---|---|
| T-001 | 校准 TimeConfig 文档与默认值 | W1 | P0 | — | FR-002, D-003@v1 |
| T-002 | 修正清洗频率规范化 | W1 | P0 | — | FR-003, D-003@v1, D-004@v1 |
| T-007 | 补强山东 loader metadata | W1 | P1 | — | FR-001, D-002@v1 |
| T-003 | 迁移负荷特征窗口 | W2 | P0 | T-001 | FR-004, D-003@v1, D-004@v1 |
| T-004 | 迁移电价特征窗口与 gap | W2 | P0 | T-001 | FR-004, D-003@v1, D-004@v1 |
| T-005 | 迁移负荷预测 gap 与文案 | W2 | P1 | T-001 | FR-004, D-003@v1, D-004@v1 |
| T-006 | 迁移 TradingEnv 维度语义 | W2 | P0 | T-001 | FR-005, D-003@v1, D-004@v1 |
| T-008 | 更新 service schema | W3 | P1 | T-001 | FR-006, D-005@v1 |
| T-009 | 更新 service handlers | W3 | P0 | T-001, T-008 | FR-001, FR-006, D-002@v1, D-005@v1 |
| T-010 | 更新 CLI/API/LLM 文案 | W3 | P2 | T-009 | FR-006, D-005@v1 |
| T-011 | 更新文档与 notebook | W4 | P2 | — | FR-006, D-001@v1, D-004@v1 |
| T-012 | 新增 15min 测试 | W4 | P0 | — | FR-007, D-003@v1, D-005@v1 |

## 关键路径

T-001 → T-003/T-004/T-005/T-006 → T-008 → T-009 → T-010（最长路径）

T-001 是唯一阻滞点，完成后 Wave 2 可并行执行。

## 全局验收标准

- [x] `TimeConfig` 默认值确认 points_per_day=96, points_per_week=672, freq="15min"
- [x] 15min 数据经 `standardize_frequency()` 后不被降采样到小时级
- [x] 负荷/电价 lag 与 rolling 特征按 TimeConfig 点数计算
- [x] `TradingEnv.action_space.shape == (96,)`
- [x] `ForecastRequest.data_source` 默认 `"shandong"`
- [x] Handler 根据 `data_source="shandong"` 加载山东 15min 数据
- [x] CLI/API/LLM 文案中 `horizon=24` 表示 24 小时跨度
- [x] 新增测试验证频率、lag、rolling、action shape
- [x] 不破坏现有 public API 名称

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | T-011 | AC: README/docs 文案 |
| D-002@v1 | T-007, T-009 | AC: ShandongDataLoader metadata, handler data_source |
| D-003@v1 | T-001, T-002, T-003, T-004, T-005, T-006, T-012 | AC: TimeConfig 默认值, 硬编码清理 |
| D-004@v1 | T-002, T-003, T-004, T-005, T-006, T-011 | AC: 全面 15min 迁移 |
| D-005@v1 | T-008, T-009, T-010, T-012 | AC: schema handler data_source |
