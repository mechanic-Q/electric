---
schema_version: 1
doc_type: module-card
module_id: rl-evaluation
---

# rl-evaluation

## 定位

评估框架模块，提供评估协议、策略评估、指标计算和报告生成纯函数。不依赖 ASSUME 框架，最大化评估透明度。

## 契约摘要

- `EvaluationProtocol` — frozen dataclass，集中保存评估配置窗口/算法/基线/路径
- `StrategyEvaluation` — dataclass，保存单策略评估结果（status/trades/error/artifact_path）
- `evaluate_baselines(runner, baselines, load, price, start, end) -> dict[str, StrategyEvaluation]`
- `evaluate_rl_agents(runner, algos, checkpoint_dir, load, price, start, end) -> dict[str, StrategyEvaluation]`
- `compute_strategy_metrics(evaluations, baseline_name, oracle_name) -> pd.DataFrame`
  - 11 列英文指标: strategy/total_pnl/sharpe/win_rate/max_drawdown/profit_factor/volatility/oracle_gap/baseline_delta/rank/status
- `write_evaluation_report(protocol, training, evaluations, metrics, report_dir, cumulative_pnl_html_path) -> dict[str, str]`
  - 输出: evaluation_report.json / evaluation_metrics.csv / evaluation_report.md，原子写入
- `generate_cumulative_pnl_html(evaluations, report_dir) -> str`

## 关键逻辑

- 复用 `BacktestRunner.replay()` 和 `BacktestRunner.plot_comparison()` 回测与图表
- 复用 `RLAgentFactory.load()` 加载已训练 checkpoint
- 单策略失败隔离：单个 baseline/RL agent 失败仅标记 status/error，不阻断其余策略
- 兼容旧 `BacktestRunner.compare()` 中文列名输出

## 注意事项

- 不调用 sb3 `.learn()`（只评估，不训练）
- 不修改传入的 load_data/price_data DataFrame
- 默认 report_dir = `"ellectric/reports/rl_full_dataset"`
- 不删除或覆盖 training_report.* 旧报告
- `cumulative_pnl_html_path` 参数支持外部传递或自动生成

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
