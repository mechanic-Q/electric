---
plan_level: full
author: lmr
created_at: 2026-06-30 04:08:00
---

# 实现计划：风/光功率独立预测模块

## 来源

来自 `design.md`：新增 wind/solar 两类轻量 XGBoost 预测器，复用 Tier1-4 特征，接入 forecast API/CLI/LLM 查询链路；本轮不修改 RL observation space。

## Spike 前置验证

| Spike | 验证内容 | 不通过后果 |
|---|---|---|
| spike-01 | 确认山东 loader 输出 `wind_actual_mw`, `solar_actual_mw`, `wind_forecast_mw`, `solar_forecast_mw` | 若任一实际列缺失，对应 forecaster 降级或 scope 缩小 |
| spike-02 | 确认现有 `run_forecast` 扩展 model_type 不破坏 load/price | 若 schema 耦合过强，改为独立 validate script 先交付 |

## Wave 1（pipeline core）

- [ ] task-01: 新增 `renewable_forecaster.py` 基础结构与共享训练评估逻辑（覆盖：FR-01, FR-02, FR-03, D-001@v1, D-003@v1）
- [ ] task-02: 实现 Tier1-4 特征构建与缺 weather 降级（覆盖：FR-04, D-004@v1）
- [ ] task-03: 新增 renewable forecaster 单元测试骨架与 fake data（覆盖：FR-08）

## Wave 2（integration）

- [ ] task-04: 扩展 service schema/handler 支持 `model_type=wind|solar`（覆盖：FR-06）
- [ ] task-05: 扩展 API/CLI/LLM forecast 查询入口（覆盖：FR-06）

## Wave 3（validation/report）

- [ ] task-06: 新增 `validate_renewable_forecaster.py` 与 JSON/Markdown/log 报告产物（覆盖：FR-05, FR-07）
- [ ] task-07: 新增模块文档 `renewable-forecaster.md`（覆盖：D-002@v1）

## 验收

- `rtk pytest tests/test_renewable_forecaster.py` 通过。
- `python -m ellectric.scripts.validate_renewable_forecaster --no-fetch` 生成 full-run 报告。
- `python -m ellectric.cli.main forecast wind 24` 可运行。
- `python -m ellectric.cli.main forecast solar 24` 可运行。
- load/price forecast 旧行为不变。
- 未修改 `trading_env.py` observation space。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01 | wind+solar forecaster tests |
| D-002@v1 | task-07 | module doc 明确不接入 RL |
| D-003@v1 | task-01 | XGBoost 模型实现 |
| D-004@v1 | task-02, task-06 | degraded weather report |

## Wave 可行性校验

- Wave 1 先交付 pipeline core，避免集成层依赖空实现。
- Wave 2 只接入已有 forecast 三通道，不触碰 RL。
- Wave 3 在 core + integration 后做真实 full-run 证据。
- 无循环依赖。

## 自检

✓ 输出明确标注 plan_level: full
✓ 有 spike、wave、验收、覆盖矩阵
✓ 所有 D-xxx@vN 在计划中可追踪
✓ task 使用 checkbox 格式
✓ 未引入不在范围内的 RL observation 变更
