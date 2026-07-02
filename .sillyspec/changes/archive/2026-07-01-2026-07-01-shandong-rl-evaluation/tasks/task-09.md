---
id: task-09
title: 新增评估 smoke tests
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06]
blocks: [task-10]
requirement_ids: [FR-09]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths: [tests/test_rl_evaluation.py, tests/test_train_rl_full_dataset.py]
---
goal: >
  用 fake runner/agent 和小 DataFrame 覆盖统一评估框架，不触发真实训练。
implementation:
  - 构造固定 seed 的 tiny load/price/trades fixture。
  - monkeypatch BacktestRunner 与 RLAgentFactory.load。
  - 测试 baseline/RL 成功、失败隔离、指标列和报告 schema。
  - 断言评估路径不调用 stable-baselines3 learn。
acceptance:
  - tests/test_rl_evaluation.py 可单独通过。
  - JSON 报告包含 metadata/protocol/training/evaluations/metrics/artifacts。
  - error 策略保留 status/error，ok 策略进入指标表。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 不依赖网络、真实 weather cache 或真实 checkpoint。
  - 不执行长训练。
  - 随机数据固定 seed。
