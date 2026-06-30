---
id: task-03
title: 更新 `.gitignore` 忽略 reports / 模型 / tb_logs 产物
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: []
blocks: []
requirement_ids: [FR-08]
decision_ids: []
allowed_paths:
  - .gitignore
goal: >
  让 50k 训练产生的报告、checkpoint、TensorBoard 日志不污染 git working tree，但保留目录占位 .gitkeep。
implementation:
  - 在 .gitignore 追加 4 行规则：`ellectric/reports/rl_full_dataset/*.json`、`ellectric/reports/rl_full_dataset/*.md`、`ellectric/reports/rl_full_dataset/*.html`、`!ellectric/reports/rl_full_dataset/.gitkeep`
  - 追加 `models/rl_full_dataset/`（整目录忽略）
  - 追加 `tb_logs/rl_full_dataset_*/`（前缀目录忽略）
  - 新建空文件 ellectric/reports/rl_full_dataset/.gitkeep
acceptance:
  - `git check-ignore ellectric/reports/rl_full_dataset/training_report.json` 返回非空
  - `git check-ignore models/rl_full_dataset/ppo.zip` 返回非空
  - `git check-ignore tb_logs/rl_full_dataset_ppo/events.out` 返回非空
  - `git check-ignore ellectric/reports/rl_full_dataset/.gitkeep` 退出码 1（未忽略）
verify:
  - git check-ignore ellectric/reports/rl_full_dataset/training_report.json
  - git check-ignore -v -- ellectric/reports/rl_full_dataset/.gitkeep || true
constraints:
  - 不删除 .gitignore 现有规则
  - 不动其它目录的 ignore 规则
