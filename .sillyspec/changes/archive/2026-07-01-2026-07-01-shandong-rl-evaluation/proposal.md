---
author: lmr
created_at: 2026-07-01 23:37:15
---

# Proposal

## 动机

山东 15min RL full dataset 训练已经具备基础闭环：`train_rl_full_dataset.py` 可以构建数据、训练 PPO/SAC/TD3、运行基线回测并输出训练报告。但当前结果解释仍然困难：评估配置散落在脚本参数和内联函数里，基线与 RL 策略的失败诊断不统一，指标列名和报告结构缺少面向“策略公平对比”的稳定契约。

用户明确本次优化主目标为 **增强对比评估**。因此本变更不再扩大数据源、不重定义交易环境、不做 reward/action 重构，而是把现有 RL 策略与 baseline 策略放进一套统一、可复现、可解释的评估框架中。

## 关键问题

1. **评估协议隐式化**：train/test 窗口、seed、策略集合、checkpoint/report 路径散落在脚本默认值和内联函数中，后续难以复现实验。
2. **指标口径不稳定**：现有 `BacktestRunner.compare()` 输出中文列名，训练报告又兼容部分英文列名，新增对比指标没有稳定 schema。
3. **失败诊断不足**：某个 RL 模型缺 checkpoint 或加载失败时，报告缺少统一 status/error 结构，不利于判断“策略失败”还是“评估管道失败”。

## 变更范围

1. 新增统一评估协议，固定 train/test 窗口、seed、算法列表、基线列表、checkpoint/report 路径等配置。
2. 让 PPO/SAC/TD3 与 `baseline_persistence`、`baseline_mean`、`oracle` 走同一 `BacktestRunner.replay()` 路径。
3. 新增英文指标表，补齐 `profit_factor`、`volatility`、`oracle_gap`、`baseline_delta`、`rank`、`status`。
4. 新增 report builder，输出 markdown/json/csv/html，并记录失败诊断和 artifact 路径。
5. 增加 smoke 测试，不触发长训练，验证指标、报告、失败隔离和脚本集成。

## 不在范围内（显式清单）

- 不下载或接入 Datawhale/DataFountain 新数据。
- 不分析 da_price 空值分布。
- 不新增净负荷、负价、尖峰 regime 等特征。
- 不修改 `ElectricityMarketEnv` reward 公式。
- 不把 96 维 action 改成 1 维 scalar。
- 不做 PPO/SAC/TD3 超参搜索或收益刷榜。

## 成功标准（可验证）

- 旧 `BacktestRunner.compare()` 行为和 `train_rl_full_dataset.py --dry-run` 默认行为不变。
- 能以统一协议评估 baseline + RL 策略集合。
- 任一策略失败不会阻断整体报告，失败原因进入报告。
- 报告目录 `ellectric/reports/rl_full_dataset/` 生成 evaluation markdown/json/csv/html。
- 指标表至少包含 total_pnl、sharpe、win_rate、max_drawdown、profit_factor、volatility、oracle_gap、baseline_delta、rank、status。
- 新增 smoke tests 通过，且不调用真实 stable-baselines3 `.learn()`。
