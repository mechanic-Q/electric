---
id: task-08
title: 新增独立评估入口
author: lmr
created_at: 2026-07-01 23:40:18
priority: P1
depends_on: [task-04, task-05, task-06]
blocks: []
requirement_ids: [FR-08]
decision_ids: [D-002@v1]
allowed_paths: [ellectric/scripts/evaluate_rl_strategies.py, ellectric/pipeline/rl_evaluation.py]
---
goal: >
  新增只评估已有 checkpoint 的 CLI，便于不重跑训练也能生成统一评估报告。
implementation:
  - 新增 argparse 入口，支持 algos、baselines、窗口、路径和 dry-run。
  - 复用 build_datasets/make_env 或 EvaluationProtocol 构建评估上下文。
  - 调用统一 baseline/RL 评估、指标和报告函数。
  - dry-run 输出空评估报告，不加载真实 checkpoint。
acceptance:
  - --dry-run 返回 0 并生成可解析报告。
  - 缺 checkpoint 时对应策略 error，baseline 仍评估。
  - 默认报告目录为 ellectric/reports/rl_full_dataset。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 可选入口不阻塞 train_rl_full_dataset。
  - 不新增 pip 依赖。
  - 不调用训练或 learn。
