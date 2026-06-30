---
id: task-01
title: 创建 `ellectric/scripts/train_rl_full_dataset.py` 骨架 + argparse + `--dry-run` 入口
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: []
blocks: [task-04, task-05]
requirement_ids: [FR-06]
decision_ids: [D-004@v1, D-007@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  建立单 CLI 入口的脚本骨架，含 argparse 参数、模块级函数空声明、`--dry-run` 短路退出，使后续 task 可填充各阶段逻辑而不影响入口形态。
implementation:
  - 创建 ellectric/scripts/train_rl_full_dataset.py，模块级 docstring + author/created_at 注释头
  - 定义模块级函数空声明: build_datasets / build_features / make_env / train_one / run_backtest / write_reports
  - argparse 入参按 design.md §7 CLI 表全部到位：--train-start/--train-end/--test-start/--test-end/--timesteps/--algos/--tier/--seed/--report-dir/--checkpoint-dir/--tb-log-root/--dry-run
  - main(argv) 解析参数，--dry-run 时仅打印计划摘要后 return 0；非 --dry-run 时 raise NotImplementedError 占位待后续 task 填充
  - 文件末尾 `if __name__ == "__main__": sys.exit(main())`
acceptance:
  - `python -m ellectric.scripts.train_rl_full_dataset --dry-run` 退出码 0
  - `python -m ellectric.scripts.train_rl_full_dataset --help` 显示全部 12 个 CLI 参数
  - 文件结构匹配 design.md §7 接口定义
verify:
  - python -m ellectric.scripts.train_rl_full_dataset --help
  - python -m ellectric.scripts.train_rl_full_dataset --dry-run
constraints:
  - 不调任何 pipeline 函数（占位即可）
  - 不引入 logger 之外的副作用 import
  - 保持中文 docstring 风格与 validate_weather_tier4.py 一致
