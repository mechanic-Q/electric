---
author: lmr
created_at: 2026-07-01 23:37:15
---

# Tasks

| Task | 名称 | 文件路径 | 覆盖 |
|---|---|---|---|
| task-01 | 新增评估协议数据结构 | `ellectric/pipeline/rl_evaluation.py` | FR-01, D-001@v1, D-002@v1 |
| task-02 | 实现 baseline 统一评估 | `ellectric/pipeline/rl_evaluation.py` | FR-02, D-002@v1, D-003@v1 |
| task-03 | 实现 RL checkpoint 统一评估与失败隔离 | `ellectric/pipeline/rl_evaluation.py` | FR-03, FR-04, D-002@v1, D-003@v1 |
| task-04 | 实现英文指标表 | `ellectric/pipeline/rl_evaluation.py` | FR-05, D-001@v1, D-002@v1 |
| task-05 | 实现 oracle/baseline 对比指标和排名 | `ellectric/pipeline/rl_evaluation.py` | FR-05, D-001@v1, D-002@v1 |
| task-06 | 实现 evaluation 报告生成 | `ellectric/pipeline/rl_evaluation.py` | FR-06, D-001@v1, D-002@v1 |
| task-07 | 复用累计 P&L 图输出 | `ellectric/pipeline/rl_evaluation.py`, `ellectric/pipeline/backtester.py` | FR-06, D-002@v1 |
| task-08 | 集成 full dataset 脚本 | `ellectric/scripts/train_rl_full_dataset.py` | FR-07, D-002@v1, D-003@v1 |
| task-09 | 新增独立评估入口（可选） | `ellectric/scripts/evaluate_rl_strategies.py` | FR-08, D-002@v1 |
| task-10 | 新增评估 smoke tests | `tests/test_rl_evaluation.py`, `tests/test_train_rl_full_dataset.py` | FR-09, D-001@v1, D-003@v1 |
| task-11 | 更新模块卡片（归档阶段） | `.sillyspec/docs/Ellectric/modules/backtester.md`, `.sillyspec/docs/Ellectric/modules/rl-trainer.md`, `.sillyspec/docs/Ellectric/modules/trading-env.md` | D-003@v1 |

> 任务细节、Wave 分组、依赖关系和验收命令在 plan 阶段展开。
