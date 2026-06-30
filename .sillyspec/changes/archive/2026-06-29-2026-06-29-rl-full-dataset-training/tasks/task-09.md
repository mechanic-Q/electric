---
id: task-09
title: 实现 `write_reports` JSON+MD + 原子写入 + 4 顶层字段 + train/test max_capacity
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-02, task-07, task-08]
blocks: [task-10]
requirement_ids: [FR-05]
decision_ids: [D-007@v1, D-008@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  把 metadata + training + backtest + interpretation 4 段写入 JSON 与 Markdown，沿用 weather-tier4-validation 报告范式，使用 tmp+rename 原子写入。
implementation:
  - 函数签名 `write_reports(report: dict, report_dir: Path) -> tuple[str, str]`
  - report["metadata"] 必含：generated_at(ISO8601 UTC)、git_sha(git rev-parse HEAD 失败留 "unknown")、time_config(freq/points_per_day)、seed、algos、timesteps_per_algo、train_range、test_range、tier、weather_source、reward_fn、price_proxy、train_max_capacity_mw、test_max_capacity_mw
  - report["training"][algo] 必含：status、final_reward、duration_s、checkpoint_path、tb_log_path、error
  - report["backtest"] 必含：metrics(list)、cumulative_pnl_html_path
  - report["interpretation"] 必含：hard_threshold_applied: false、summary
  - 写 JSON：mkdir -p report_dir；写入 report_dir/.training_report.json.tmp 后 os.replace 到 training_report.json
  - 渲染 Markdown：4 段对应 4 个 H2，metadata/training 用表格，backtest 用 metrics 表格，interpretation 段落；同样 tmp+rename
acceptance:
  - test_write_reports_json_schema：JSON 4 顶层字段齐全，metadata 含 13 必需子字段（包括 train/test max_capacity）
  - test_write_reports_atomic：写入过程中无 .tmp 文件残留
  - test_write_reports_md_sections：Markdown 含 "## Metadata"/"## Training"/"## Backtest"/"## Interpretation"
verify:
  - pytest tests/test_train_rl_full_dataset.py -q -k write_reports
constraints:
  - 不依赖外部模板引擎（手写 f-string 即可）
  - git_sha 解析失败不抛异常
  - JSON 使用 ensure_ascii=False, indent=2
