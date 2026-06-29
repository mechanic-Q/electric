---
id: task-12
title: 更新 `.planning/ROADMAP.md` + `ellectric/README.md` Phase 4 持续改进勾选 + 指向报告路径
author: lmr
created_at: 2026-06-29 01:51:26
priority: P1
depends_on: [task-10]
blocks: [task-13]
requirement_ids: [FR-08]
decision_ids: []
allowed_paths:
  - .planning/ROADMAP.md
  - ellectric/README.md
goal: >
  把 Phase 4 持续改进表中"完整 96 维 RL training on full dataset"项标注为已完成首轮，并指向产物报告路径，使 ROADMAP/README 与现实一致。
implementation:
  - 在 .planning/ROADMAP.md Phase 4 "持续改进项" 列表第 1 项后追加："✅ 首轮跑通 — 见 `ellectric/reports/rl_full_dataset/training_report.md`（脚本 `ellectric/scripts/train_rl_full_dataset.py`）"
  - 在 ellectric/README.md "Phase 4: 持续改进" 段把 `- [ ] 完整 96 维 RL training on full dataset` 改为 `- [x] 完整 96 维 RL training on full dataset（见 ellectric/reports/rl_full_dataset/）`
  - 不动其它项
acceptance:
  - rg "首轮跑通" .planning/ROADMAP.md 匹配 1 行
  - rg "完整 96 维 RL training on full dataset" ellectric/README.md 行首为 `- [x]`
  - 没有引入旧表述"未跑过完整 96 维 RL"
verify:
  - rg "首轮跑通|训练入口" .planning/ROADMAP.md ellectric/README.md
constraints:
  - 不改动 Phase 1-3 既有状态描述
  - frontmatter (author/created_at) 若存在则保留原值
