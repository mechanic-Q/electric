---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Decisions: 风/光功率独立预测模块

## Current Decisions

### D-001@v1: 范围包含 wind + solar

**决策**: 同时实现风电和光伏预测器。

**理由**: 山东数据已同时包含风/光实际与预测列；一起实现能完整补齐新能源出力预测维度。

### D-002@v1: 先不接入 RL observation space

**决策**: 本轮只做独立预测模块和 forecast 接口，不修改 `trading_env.py` 观测空间。

**理由**: 接入 RL 会触发 96 维 full dataset retraining，范围大且会拖慢本轮。

### D-003@v1: 使用 XGBoost 轻量模型

**决策**: 不实现深度状态空间模型，使用 XGBoost 作为第一版。

**理由**: 与项目“轻量级模型、普通开发机可运行”约束一致。

### D-004@v1: Weather Tier4 是可选增强层

**决策**: 优先使用 Tier1-3 + weather；weather 不可用时降级到 Tier1-3。

**理由**: 保持离线可复现，不因 weather cache 缺失阻塞训练。

## Unresolved

无。
