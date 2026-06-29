---
id: task-08
title: 实现 `run_backtest` 6 条线对比 + Plotly 累计 P&L html
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-02, task-06]
blocks: [task-09]
requirement_ids: [FR-04]
decision_ids: [D-005@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  在回测窗口跑 persistence/mean/oracle 三基线 + 训练成功的 PPO/SAC/TD3 三 RL agent，输出统一 metrics 表 + Plotly 累计 P&L html。
implementation:
  - 函数签名 `run_backtest(train_results, test_load, test_price, *, test_start, test_end, checkpoint_dir, report_dir) -> dict`
  - 内部构造 BacktestRunner(env_factory=lambda: make_env(test_load, test_price))
  - for s in SUPPORTED_STRATEGIES: results[s] = runner.replay(s, test_load, test_price, test_start, test_end, strategy_name=s)
  - for algo, info in train_results.items(): if info["status"]=="ok": agent = RLAgentFactory.load(algo, info["checkpoint_path"]); results[f"rl_{algo}"] = runner.replay(agent, test_load, test_price, test_start, test_end, strategy_name=f"rl_{algo}")
  - metrics_df = runner.compare(results)；fig = BacktestRunner.plot_comparison(results)；fig.write_html(report_dir/"cumulative_pnl.html")
  - 返回 {metrics: metrics_df.to_dict(orient="records"), cumulative_pnl_html_path: str}
acceptance:
  - test_run_backtest_baselines_only：train_results 全部 status=="error" 时仍输出 3 条基线
  - test_run_backtest_includes_rl：单 RL 算法 status=="ok" 时输出包含 rl_<algo> 条目
  - test_run_backtest_html_generated：cumulative_pnl.html 文件存在 size>0
verify:
  - pytest tests/test_train_rl_full_dataset.py -q -k run_backtest
constraints:
  - status=="error" 的算法不调 RLAgentFactory.load
  - report_dir 不存在时自动 mkdir
  - 不修改 BacktestRunner 内部
