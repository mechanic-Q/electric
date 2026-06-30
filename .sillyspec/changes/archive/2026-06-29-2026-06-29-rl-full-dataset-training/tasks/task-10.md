---
id: task-10
title: 实现 `main()` 串接 Wave 1-4 + 退出码语义
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-04, task-05, task-06, task-07, task-08, task-09]
blocks: [task-11, task-12, task-13]
requirement_ids: [FR-06]
decision_ids: [D-004@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  把所有阶段函数串成 main(argv)，支持 --dry-run / --algos 子集 / Tier 切换 / 端到端可复现，按数据/特征/报告失败分别返回退出码 0/1/2。
implementation:
  - argparse 解析后：若 --dry-run，仅执行 build_datasets + build_features + make_env(train) 装配 smoke，写入仅含 metadata+interpretation 的精简 JSON 后 return 0
  - 非 dry-run：依次 build_datasets → build_features → make_env(train) → for algo in args.algos: train_one(algo, env, ...) → run_backtest → 组装 report dict → write_reports
  - report["training"] 中 args.algos 之外的算法保留 status="skipped" 占位
  - 数据/特征装配异常 → logger.error + return 1；write_reports IO 异常 → return 2；其它正常返回 0
  - report["metadata"] 同时记 train_max_capacity_mw = train_load.load_mw.max() 与 test_max_capacity_mw = test_load.load_mw.max()
  - 主入口 `if __name__ == "__main__": sys.exit(main())`
acceptance:
  - test_main_dry_run_exit_0：--dry-run 退出码 0，且 fake_agent_factory 未被调用
  - test_main_data_load_failure_exit_1：monkeypatch build_datasets 抛异常时退出码 1
  - test_main_algos_subset：--algos ppo 时 report["training"]["sac"].status=="skipped"
verify:
  - pytest tests/test_train_rl_full_dataset.py -q -k main
constraints:
  - main 必须使用 fake_agent_factory fixture，禁止真实 .learn()
  - 不在 main 中读取环境变量
  - 退出码语义在脚本顶部 docstring 列明
