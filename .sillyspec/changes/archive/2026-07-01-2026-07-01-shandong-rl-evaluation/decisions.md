---
author: lmr
created_at: 2026-07-01 23:37:15
---

# Decisions

## D-001@v1: 主目标限定为增强对比评估

- type: boundary
- priority: P1
- status: accepted
- supersedes:
- source: user + docs
- question: 本次 RL 优化最优先改善什么？
- answer: 用户选择“增强对比评估”。
- normalized_requirement: 统一评估协议、基线、指标、报告和失败诊断；不优先追求收益最大化，不重定义 reward/action。
- impacts: [FR-01, FR-04, FR-05, FR-06, FR-09, task-01, task-04, task-06]
- evidence: 用户在 brainstorm step 6 选择“增强对比评估”；模块卡片显示 backtester 已有基线与基础指标。

## D-002@v1: 选择方案 B — 统一对比评估框架

- type: architecture
- priority: P1
- status: accepted
- supersedes:
- source: user
- question: 采用最小脚本、统一框架，还是训练/奖励优化 + 对比？
- answer: 用户选择“方案B（推荐）”。
- normalized_requirement: 新增统一评估模块，集中处理 EvaluationProtocol、策略集合、指标层、报告生成；full dataset 脚本复用该模块。
- impacts: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, task-01, task-02, task-03, task-06, task-09]
- evidence: brainstorm step 8 用户选择“方案B（推荐）”。

## D-003@v1: 保留现有环境/回测兼容路径

- type: compatibility
- priority: P1
- status: accepted
- supersedes:
- source: code + docs
- question: 是否为了评估而修改 `ElectricityMarketEnv` reward/action 或 `BacktestRunner.compare()` 输出？
- answer: 不修改环境交易逻辑；`BacktestRunner.compare()` 保留旧行为，新评估指标以新增函数提供。
- normalized_requirement: baseline 和 RL 都继续通过 `BacktestRunner.replay()` 生成 trades；旧中文指标接口保持可用；新增英文指标与报告不破坏旧 notebook/脚本。
- impacts: [FR-02, FR-03, FR-07, FR-09, task-02, task-03, task-09, task-11]
- evidence: `ellectric/pipeline/trading_env.py`、`ellectric/pipeline/backtester.py`、`ellectric/scripts/train_rl_full_dataset.py` 现有接口。
