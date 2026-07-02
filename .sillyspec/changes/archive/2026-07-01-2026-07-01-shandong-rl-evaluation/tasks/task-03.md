---
id: task-03
title: 实现 RL checkpoint 统一评估与失败隔离
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: [task-01]
blocks: [task-04, task-05, task-06, task-09]
requirement_ids: [FR-03, FR-04]
decision_ids: [D-002@v1, D-003@v1]
allowed_paths: [ellectric/pipeline/rl_evaluation.py]
---
goal: >
  让 PPO/SAC/TD3 checkpoint 统一加载并 replay，缺失或失败只影响对应策略。
implementation:
  - 遍历 EvaluationProtocol.algos 并解析 checkpoint 路径。
  - 使用 RLAgentFactory.load 加载已有模型。
  - 加载成功后调用 runner.replay(agent, ..., strategy_name=f"rl_{algo}")。
  - 捕获 checkpoint 缺失、加载失败、replay 失败并写 status/error。
acceptance:
  - fake checkpoint + fake agent 能生成 ok 策略结果。
  - 缺失 checkpoint 记录 error，不影响其他 algo。
  - 评估路径不调用 train 或 learn。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 不触发任何训练。
  - 不改变 RLAgentFactory.load 签名。
  - 保留 deterministic replay 行为。
