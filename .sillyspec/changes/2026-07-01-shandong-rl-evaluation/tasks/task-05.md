---
id: task-05
title: 实现 evaluation 报告文件输出
author: lmr
created_at: 2026-07-01 23:40:18
priority: P0
depends_on: [task-04]
blocks: [task-06, task-07, task-08, task-09]
requirement_ids: [FR-06]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [ellectric/pipeline/rl_evaluation.py]
---
goal: >
  将协议、训练、评估、指标和失败诊断写成 json/csv/md 三类 evaluation 报告。
implementation:
  - 写 evaluation_report.json，包含 metadata/protocol/training/evaluations/metrics/artifacts。
  - 写 evaluation_metrics.csv，保存英文指标表。
  - 写 evaluation_report.md，展示协议、排名、失败诊断、artifact 路径。
  - 使用临时文件加 os.replace，返回产物路径字典。
acceptance:
  - 三个文件存在且非空。
  - JSON schema 可解析并包含失败策略 error。
  - Markdown 包含 Failure Diagnosis 和 Artifacts。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 不删除或覆盖 training_report.*。
  - report_dir 支持 tmp_path 覆盖。
  - 默认输出目录为 ellectric/reports/rl_full_dataset。
