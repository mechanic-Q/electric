---
id: task-04
title: 实现英文策略指标表与排名
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: [task-02, task-03]
blocks: [task-05, task-06, task-07, task-08, task-09]
requirement_ids: [FR-05]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [ellectric/pipeline/rl_evaluation.py]
---
goal: >
  基于 StrategyEvaluation 集合生成稳定英文指标表，用于 RL 与 baseline 公平比较。
implementation:
  - 从 ok 策略 trades 计算 total_pnl、sharpe、win_rate、max_drawdown。
  - 计算 profit_factor、volatility、oracle_gap、baseline_delta、rank。
  - 对 error/skipped 策略保留 status/error，指标为空值。
  - 空输入返回含固定列的空 DataFrame。
acceptance:
  - 输出列完整且英文列名稳定。
  - oracle 或 baseline 缺失时 gap/delta 为空且不崩溃。
  - 失败策略出现在表中并保留 status/error。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 不替换 BacktestRunner.compare。
  - NaN/inf 需能被报告层处理。
  - 不新增 pandas/numpy 外依赖。
