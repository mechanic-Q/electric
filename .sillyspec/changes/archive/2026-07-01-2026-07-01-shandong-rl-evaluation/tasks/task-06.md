---
id: task-06
title: 复用累计 P&L 图并记录 artifact 路径
author: lmr
created_at: 2026-07-01 23:40:18
priority: P1
depends_on: [task-02, task-03, task-05]
blocks: [task-07, task-08, task-09]
requirement_ids: [FR-06]
decision_ids: [D-002@v1]
allowed_paths: [ellectric/pipeline/rl_evaluation.py, ellectric/pipeline/backtester.py]
---
goal: >
  复用 BacktestRunner.plot_comparison 输出 cumulative_pnl.html，并把路径写入 evaluation artifacts。
implementation:
  - 从 ok 策略提取 trades 结果集合。
  - 调用 BacktestRunner.plot_comparison 生成现有 Plotly 图。
  - 写 report_dir/cumulative_pnl.html 或指定路径。
  - 将 html 路径写入 write_evaluation_report 返回值和 JSON artifacts。
acceptance:
  - 成功 trades 存在时生成 cumulative_pnl.html。
  - 无成功 trades 时跳过 HTML 但其他报告正常生成。
  - JSON artifacts.cumulative_pnl_html 与实际文件一致。
verify:
  - python -m pytest tests/test_rl_evaluation.py -q
constraints:
  - 不重写图表样式或新增可视化依赖。
  - 不修改 BacktestRunner.plot_comparison 签名。
  - HTML 输出路径可配置。
