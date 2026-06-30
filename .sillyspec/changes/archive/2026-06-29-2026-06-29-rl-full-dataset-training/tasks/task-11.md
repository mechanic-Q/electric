---
id: task-11
title: 更新 `docs/Ellectric/modules/rl-trainer.md` 增加「full-dataset 训练入口」章节
author: lmr
created_at: 2026-06-29 01:51:26
priority: P1
depends_on: [task-10]
blocks: [task-13]
requirement_ids: [FR-08]
decision_ids: []
allowed_paths:
  - docs/Ellectric/modules/rl-trainer.md
goal: >
  在 rl-trainer 模块卡片末尾补一段「full-dataset 训练入口」，指向新脚本、报告路径、CLI 用法与 --dry-run，方便后续 agent 直接复用。
implementation:
  - 读取 docs/Ellectric/modules/rl-trainer.md
  - 在 "## 人工备注" 之前插入新章节 "## full-dataset 训练入口"
  - 章节内容：CLI 命令示例（默认 + --algos 子集 + --dry-run）、报告输出路径表、报告 4 字段说明、checkpoint 与 tb_logs 路径
  - 章节链接到 .sillyspec/changes/2026-06-29-rl-full-dataset-training/design.md 与 ellectric/reports/rl_full_dataset/training_report.md
acceptance:
  - 文件含 "## full-dataset 训练入口" 标题
  - 章节含 `python -m ellectric.scripts.train_rl_full_dataset --dry-run` 命令
  - 章节含报告路径 `ellectric/reports/rl_full_dataset/training_report.json`
verify:
  - rg "full-dataset 训练入口" docs/Ellectric/modules/rl-trainer.md
  - rg "ellectric/reports/rl_full_dataset" docs/Ellectric/modules/rl-trainer.md
constraints:
  - 不修改已有"定位/契约摘要/关键逻辑/注意事项/人工备注"段
  - frontmatter schema_version 不变
