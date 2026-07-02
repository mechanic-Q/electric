---
id: task-07
title: 集成 train_rl_full_dataset.py 到统一评估模块
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: [task-04, task-05, task-06]
blocks: [task-10]
requirement_ids: [FR-07]
decision_ids: [D-002@v1, D-003@v1]
allowed_paths: [ellectric/scripts/train_rl_full_dataset.py, ellectric/pipeline/rl_evaluation.py]
---
goal: >
  将 full dataset 脚本的回测/报告委托给统一评估模块，同时保持原 CLI 与旧报告兼容。
implementation:
  - 在 run_backtest 中复用 baseline/RL 评估、指标和图表产物。
  - 在 write_reports 或主流程中追加 evaluation artifacts。
  - 保留 training_report.json 与 training_report.md 输出。
  - 保持 parse_args 默认参数和 exit code 语义不变。
acceptance:
  - --dry-run 返回 0 且不进入真实训练。
  - 旧 training_report.* 继续生成。
  - full 路径可生成 evaluation_report.*。
verify:
  - python -m pytest tests/test_train_rl_full_dataset.py tests/test_rl_evaluation.py -q
constraints:
  - 不删除或重命名任何 CLI 参数。
  - 不让 dry-run 调用 build_datasets 或 learn。
  - 旧测试必须继续通过。
