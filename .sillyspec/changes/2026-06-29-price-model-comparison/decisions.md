---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Decisions: 电价模型对比报告

## Current Decisions

### D-001@v1: DNN baseline 使用 PyTorch MLP

**决策**: 不安装 TensorFlow/epftoolbox DNN，本项目内实现轻量 PyTorch MLP。

**理由**: 主环境已有 PyTorch（RL 依赖），避免 TensorFlow 与 ASSUME/PyTorch 环境冲突。

### D-002@v1: 首轮只用山东数据

**决策**: 本轮不引入 epftoolbox 5 个海外数据集。

**理由**: 项目主线已经切到山东 15min 真实数据；先保证业务语境一致。

### D-003@v1: DNN 不调参刷榜

**决策**: 固定小模型默认配置，用于比较和教学，不做 hyperparameter search。

**理由**: 目标是模型对比与统计检验，不是追求最佳 leaderboard。

### D-004@v1: LEAR 保持默认 price 模型

**决策**: 新增 DNN 和 compare script，不改变现有 `PriceForecaster` 默认行为。

**理由**: 保持现有 API/CLI 兼容。

## Unresolved

无。
