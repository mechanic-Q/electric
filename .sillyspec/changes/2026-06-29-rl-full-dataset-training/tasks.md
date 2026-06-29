---
author: lmr
created_at: 2026-06-29 01:44:36
---

# Tasks

- [ ] T-001 — 实现 `build_datasets` + 价格代理 + 时段切分 (`ellectric/scripts/train_rl_full_dataset.py`) — 覆盖 FR-01, D-001@v1, D-006@v1
- [ ] T-002 — 实现 `build_features` + Tier4 cache 降级 + forecasters 训练 (`ellectric/scripts/train_rl_full_dataset.py`) — 覆盖 FR-02, D-006@v1
- [ ] T-003 — 实现 `make_env` + reward_fn=profit_only (`ellectric/scripts/train_rl_full_dataset.py`) — 覆盖 FR-03, D-002@v1
- [ ] T-004 — 实现 `train_one` + checkpoint + 异常隔离 (`ellectric/scripts/train_rl_full_dataset.py`) — 覆盖 FR-03, D-003@v1, D-005@v1
- [ ] T-005 — 实现 `run_backtest` + 6 条线对比 + plotly html (`ellectric/scripts/train_rl_full_dataset.py`) — 覆盖 FR-04, D-005@v1
- [ ] T-006 — 实现 `write_reports` JSON+MD + 原子写入 + 4 顶层字段 + train/test max_capacity (`ellectric/scripts/train_rl_full_dataset.py`) — 覆盖 FR-05, D-007@v1, D-008@v1
- [ ] T-007 — 实现 `main` CLI argparse + `--dry-run` 路径 (`ellectric/scripts/train_rl_full_dataset.py`) — 覆盖 FR-06, D-004@v1
- [ ] T-008 — 新增单元测试（fake adapter，不真调 sb3）(`tests/test_train_rl_full_dataset.py`) — 覆盖 FR-07, D-007@v1
- [ ] T-009 — 更新 `.gitignore` 忽略报告/模型/tb_logs 产物 (`.gitignore`) — 覆盖 FR-08
- [ ] T-010 — 更新 rl-trainer 模块文档加 full-dataset 入口章节 (`docs/Ellectric/modules/rl-trainer.md`) — 覆盖 FR-08
- [ ] T-011 — 更新 README + ROADMAP Phase 4 勾选 + 指向报告 (`ellectric/README.md`, `.planning/ROADMAP.md`) — 覆盖 FR-08
- [ ] T-012 — 端到端 `--dry-run` 验证 + 单元测试运行（不在 CI 跑 50k） — 覆盖 FR-01~FR-08
