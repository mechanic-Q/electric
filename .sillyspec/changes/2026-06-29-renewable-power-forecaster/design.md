---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Design: 风/光功率独立预测模块

## 背景

山东 15min 数据已经包含风电与光伏实际/预测列：`wind_actual_mw`, `solar_actual_mw`, `wind_forecast_mw`, `solar_forecast_mw`。当前项目没有独立的新能源出力预测模块，导致图迹画像中的“风功率预测”能力缺口仍存在。

## 设计目标

- 新增 wind/solar 两类可独立训练、评估、预测的轻量模型。
- 复用现有 Tier1-4 特征工程，尤其 weather Tier4。
- 接入现有 forecast API/CLI/LLM 查询链路。
- 先不修改 RL observation space，降低范围。

## 非目标

- 不做深度状态空间模型。
- 不改 trading_env observation space。
- 不重训 PPO/SAC/TD3。
- 不新增外部数据源。

## 决策/方案选择

- **方案选择**: wind + solar 同时实现，使用 XGBoost 轻量模型。
- **不选方案**: 不做深度状态空间模型，不接入 RL observation space。
- **取舍理由**: 山东数据已有 wind/solar 实际与预测列，双模型一次补齐新能源预测能力；接入 RL 会触发全量重训，拆到后续更安全。
- **执行策略**: 先独立预测 + API/CLI 查询 + full-run 报告，后续如需要再扩展 RL env。

## 总体方案

### 模块结构

新增 `ellectric/pipeline/renewable_forecaster.py`：

- `_BaseRenewableForecaster`
  - 负责通用 XGBoost 训练、预测、TimeSeriesSplit 评估、metrics。
- `WindPowerForecaster`
  - target: `wind_actual_mw`
  - baseline: `wind_forecast_mw`（如存在）
- `SolarPowerForecaster`
  - target: `solar_actual_mw`
  - baseline: `solar_forecast_mw`（如存在）

### 特征

- Tier1: hour/day/month/weekend/lag_24h。
- Tier2: holiday/lag_168h。
- Tier3: rolling/harmonic。
- Tier4: weather columns（temp/ghi/wind_speed/precip/humidity/cloud × jinan/qingdao）。

weather 缺失时降级到 Tier1-3，并在报告中记录 degraded note。

### 指标

- MAE
- RMSE
- nRMSE = RMSE / (max(y) - min(y))，若分母为 0 则 None。

### 接入点

- service: `run_forecast(model_type="wind"|"solar")`
- API: 复用 `/predict`
- CLI: `forecast wind 24`, `forecast solar 24`
- LLM: 扩展 `query_forecast` docstring，让 agent 知道 model_type 可选项。

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 新增 | `ellectric/pipeline/renewable_forecaster.py` |
| 修改 | `ellectric/service/schemas.py` |
| 修改 | `ellectric/service/handlers.py` |
| 修改 | `ellectric/api/server.py` |
| 修改 | `ellectric/cli/main.py` |
| 修改 | `ellectric/llm/tools.py` |
| 新增 | `ellectric/scripts/validate_renewable_forecaster.py` |
| 新增 | `tests/test_renewable_forecaster.py` |
| 新增 | `docs/Ellectric/modules/renewable-forecaster.md` |
| 生成 | `ellectric/reports/renewable_forecaster/validation.json` |
| 生成 | `ellectric/reports/renewable_forecaster/validation.md` |
| 生成 | `ellectric/reports/renewable_forecaster/validation.log` |

## 兼容策略

- 只扩展 forecast model_type，不改变 load/price 行为。
- 若某数据列缺失，返回明确错误或 degraded 报告，不 silent fail。
- 不修改现有 forecaster/trading_env/rl_trainer 公开签名。

## 风险

| 风险 | 缓解 |
|---|---|
| 光伏夜间大量 0 影响指标 | nRMSE + 按小时分段统计 |
| weather cache 缺失 | Tier1-3 降级路径 |
| forecast API schema 变宽 | Literal/enum 测试覆盖 |
| RL 接入诱发重训范围 | 本轮明确不接入 RL |

## 验收

- wind/solar full-run 报告生成。
- CLI/API 可预测 wind/solar。
- Tests 通过。
- 文档说明本轮不接入 RL observation。
