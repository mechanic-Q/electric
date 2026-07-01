---
id: task-02
title: 实现 baseline 统一评估与失败隔离
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: [task-01]
blocks: [task-04, task-05, task-06, task-09]
requirement_ids: [FR-02, FR-04]
decision_ids: [D-002@v1, D-003@v1]
allowed_paths: [ellectric/pipeline/rl_evaluation.py]
---
goal: >
  让 baseline 策略统一通过 BacktestRunner.replay 评估，并将单策略失败隔离为 status/error。
implementation:
  - 遍历 EvaluationProtocol.baselines。
  - 每个 baseline 调用 runner.replay(strategy_name, load_data, price_data, start, end)。
  - 成功返回 StrategyEvaluation(status="ok", trades=df)。
  - 捕获异常并返回 StrategyEvaluation(status="error", error=str(exc))，继续下一个策略。
acceptance:
  - baseline 成功时 trades 非空并包含 pnl_hourly。
  - 某一 baseline 抛错时其他 baseline 继续评估。
  - 返回结果包含每个 baseline 的 status 和 error/trades。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 不改 BacktestRunner.compare 中文列名。
  - 不吞掉原始错误文本。
  - 不就地修改 load_data/price_data。
