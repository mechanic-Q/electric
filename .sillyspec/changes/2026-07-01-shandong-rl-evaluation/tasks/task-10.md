---
id: task-10
title: 更新/保留 full dataset 兼容测试
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: [task-07, task-09]
blocks: []
requirement_ids: [FR-07, FR-09]
decision_ids: [D-003@v1]
allowed_paths: [tests/test_train_rl_full_dataset.py, ellectric/scripts/train_rl_full_dataset.py]
---
goal: >
  确认统一评估集成不破坏 full dataset dry-run、旧报告 schema 和解释兼容逻辑。
implementation:
  - 保留现有 write_reports schema 测试断言。
  - 保留 _build_interpretation 对中文/英文 metrics 的兼容测试。
  - 补充 evaluation artifacts 与 training_report.* 共存断言。
  - 确认 dry-run 早返回且不调用 build_datasets/learn。
acceptance:
  - tests/test_train_rl_full_dataset.py 全部通过。
  - training_report.json/md 仍按旧名称生成。
  - dry-run 不执行真实数据构建或训练。
verify:
  - python -m pytest tests/test_train_rl_full_dataset.py tests/test_rl_evaluation.py -q
constraints:
  - 不删除既有测试断言。
  - 不让 dry-run 进入 build_datasets。
  - 不调用真实 sb3 learn。
