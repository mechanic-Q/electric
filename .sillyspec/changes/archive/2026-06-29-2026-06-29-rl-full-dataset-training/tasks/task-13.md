---
id: task-13
title: 运行 `pytest tests/test_train_rl_full_dataset.py` + `python -m ellectric.scripts.train_rl_full_dataset --dry-run` 全部通过
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06, task-07, task-08, task-09, task-10, task-11, task-12]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-005@v1, D-006@v1, D-007@v1, D-008@v1]
allowed_paths: []
goal: >
  端到端验证：pytest 全绿、--dry-run 退出 0、生成的 dry-run 报告 metadata 字段齐全，确认本变更交付物完整。
implementation:
  - 激活 venv（ellectric/.venv）
  - 运行 pytest tests/test_train_rl_full_dataset.py -q，确认通过且无 sb3 真训练副作用
  - 运行 python -m ellectric.scripts.train_rl_full_dataset --dry-run，确认退出 0
  - 检查产物 ellectric/reports/rl_full_dataset/training_report.json：4 顶层字段齐全、metadata.price_proxy、metadata.reward_fn、metadata.train_max_capacity_mw、metadata.test_max_capacity_mw 全部存在
  - 检查 rg "首轮跑通" .planning/ROADMAP.md 和 README Phase 4 勾选
acceptance:
  - pytest 退出码 0
  - dry-run 命令退出码 0
  - dry-run 后 training_report.json 解析为 dict 且包含 metadata/training/backtest/interpretation 四键
  - metadata.price_proxy == "rt_price->price_da"
  - metadata.reward_fn == "profit_only"
verify:
  - pytest tests/test_train_rl_full_dataset.py -q
  - python -m ellectric.scripts.train_rl_full_dataset --dry-run
  - python -c "import json,pathlib; r=json.loads(pathlib.Path('ellectric/reports/rl_full_dataset/training_report.json').read_text()); assert set(r)>={'metadata','training','backtest','interpretation'}"
constraints:
  - 不执行真实 50k 训练（人工本地或可选 Action）
  - 不修改任何源码，仅运行验证
  - 失败时 rollback 到对应 task 修正，不在本 task 内修复
