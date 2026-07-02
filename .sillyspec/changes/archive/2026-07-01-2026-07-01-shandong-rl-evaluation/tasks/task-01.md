---
id: task-01
title: 新增评估协议与策略结果模型
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: []
blocks: [task-02, task-03, task-04, task-05, task-07, task-08, task-09]
requirement_ids: [FR-01]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [ellectric/pipeline/rl_evaluation.py]
---
goal: >
  新增评估协议与策略结果模型，为 baseline/RL 统一评估提供稳定数据契约。
implementation:
  - 新建 rl_evaluation.py，保持模块级中英 docstring 与 logger 风格。
  - 定义 EvaluationProtocol，集中 train/test、algos、baselines、seed、路径配置。
  - 定义 StrategyEvaluation，保存 strategy/status/trades/error/artifact_path。
  - 导出两个数据结构，不实现评估、指标或报告逻辑。
acceptance:
  - 可导入 EvaluationProtocol 和 StrategyEvaluation。
  - 协议默认 algos 为 ppo/sac/td3，baselines 为 persistence/mean/oracle。
  - 模块导入不触发 DataLoader、sb3 或 BacktestRunner 副作用。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 不修改 ElectricityMarketEnv reward/action。
  - 不引入新第三方依赖。
  - 保持 timestamp/load_mw/price_da DataFrame 合约。
