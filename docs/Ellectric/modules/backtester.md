
---
schema_version: 1
doc_type: module-card
module_id: backtester
---

# backtester

## 定位

回测引擎，在历史负荷和电价数据上回放交易策略，支持基线策略和 RL 智能体，
提供多策略对比分析和累计 P&L 可视化。

## 契约摘要

- `BacktestRunner` — 回测运行器
  - `replay(model, load_data, price_data, start, end, strategy_name) -> pd.DataFrame` — 回放
  - `compare(results) -> pd.DataFrame` — 多策略对比
  - `plot_comparison(comparison_df, title) -> go.Figure` — 累计 P&L 叠加图
- `baseline_persistence(env, t) -> np.ndarray` — t-24h 持续法投标
- `baseline_mean(env, t) -> np.ndarray` — 168h 滚动均值投标
- `oracle_strategy(env, t) -> np.ndarray` — 已知真实负荷的完美投标

## 关键逻辑

- 输出列: timestamp, bid_mw, cleared_mw, clearing_price, actual_load, pnl_hourly, pnl_cumulative, strategy
- compare() 计算: 总收益、夏普比率、胜率、最大回撤
- oracle 策略 P&L ≥ 所有策略（逻辑正确性断言）
- 复用电价/latex: `forecaster.calculate_pnl()`

## 注意事项

- start/end 格式: YYYY-MM-DD → ValueError
- 不修改传入 DataFrame
- 缺失值: ffill + bfill

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
