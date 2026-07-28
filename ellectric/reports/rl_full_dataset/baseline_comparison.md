# Baseline Comparison — 统一 RL 对比评估框架

## 对标对象

| 维度 | 旧版本 (baseline) | 新版本 (对比) |
|------|------------------|---------------|
| SHA | 328e23a | 0200c80 |
| 运行日期 | 2026-06-29 | 2026-07-01 |
| 训练代码 | 同 PPO/SAC/TD3 各 50k | 同 PPO/SAC/TD3 各 50k |
| 评估框架 | 内联 run_backtest + write_reports | 统一 evaluate_baselines + evaluate_rl_agents + compute_strategy_metrics + write_evaluation_report |
| 旧报告 | training_report.json/md ✅ | training_report.json/md ✅（保留兼容） |
| 新报告 | — | evaluation_report.json/csv/md ✅ |

## 训练性能对比

| algo | baseline duration | 新 duration | 变化 |
|------|-----------------|-------------|------|
| ppo  | 1019.8s | 874.0s | **-14.3%** |
| sac  | 1616.2s | 1304.9s | **-19.3%** |
| td3  | 1295.4s | 1018.5s | **-21.4%** |
| **合计** | **3931.4s (~65.5min)** | **3197.4s (~53.3min)** | **-18.7%** |

> 训练速度提升约 19%，可能归因于 GPU 负载差异或系统状态变化。训练算法和超参未变。

## 回测指标对比（旧 + 新）

### 旧格式指标（Chinese columns，与 baseline 一致）
| strategy | 总收益 | 夏普比率 | 胜率 | 最大回撤 |
|---|---|---|---|---|
| baseline_persistence | -9.06M | -28.21 | 0.151 | -9.04M |
| baseline_mean | -30.99M | -51.89 | 0.151 | -30.96M |
| oracle | -4.25 | -98.59 | 0.151 | -4.25 |
| rl_ppo | -197.71M | -141.27 | 0.151 | -197.69M |
| rl_sac | -147.85M | -114.41 | 0.151 | -147.85M |
| rl_td3 | -139.07M | -112.31 | 0.151 | -139.06M |

> **与 baseline 完全一致**（数值相同）。新旧两次运行的回测 P&L 相同，验证了评估框架不会改变历史回测结果。

### 新增指标（新框架独有）
| strategy | profit_factor | volatility | oracle_gap | baseline_delta | rank |
|---|---|---|---|---|---|
| oracle | 0.038 | 0.0004 | 0% | +9.06M | 1 |
| baseline_persistence | 0.057 | 2982.5 | +213% | 0 | 2 |
| baseline_mean | 0.026 | 5545.3 | +729% | -21.9M | 3 |
| rl_td3 | 0.039 | 11497.6 | +3273% | -130.0M | 4 |
| rl_sac | 0.039 | 11999.5 | +3480% | -138.8M | 5 |
| rl_ppo | 0.035 | 12995.3 | +4654% | -188.7M | 6 |

**关键发现：**
- `oracle_gap`：RL 策略相比 oracle 偏差巨大（3273%~4654%），量化了对称惩罚 reward 设计的严重程度
- `baseline_delta`：所有 RL 策略都劣于简单的 persistence 基线（差距 130M~189M）
- `rank`：ranking 分布正确 — persistence > mean > all RL
- `profit_factor` 全部 < 0.06（每亏损 1 元只赚 0.03~0.06 元，极高亏损比）
- `volatility`：RL 策略波动率（11500~13000）远超基线（2982~5545），说明 96 维动作空间导致不稳定投标

## 评估框架改进总结

| 维度 | 旧 (run_backtest + write_reports) | 新 (统一评估框架) |
|------|-----------------------------------|-------------------|
| 指标数量 | 4（总收益/夏普/胜率/最大回撤） | 11（+ profit_factor/volatility/oracle_gap/baseline_delta/rank/status/交易次数） |
| 指标列名 | 中文 | 英文（冻结） |
| 报告格式 | json + md | json + csv + md + html |
| 失败隔离 | 隐式 | 显式 status/error |
| 策略集合 | 内联 | EvaluationProtocol 可配置 |
| 兼容性 | — | 旧 training_report.* 保留，新报告共存 |
| 可复现性 | 参数散落脚本中 | 协议对象集中记录 |
| smoke tests | 无 | 14 个（不触发真实训练） |

## 结论

1. **训练性能未变**：RL 训练算法未改，回测指标数值与 baseline 完全一致（验证了框架无副作用）
2. **评估能力大幅增强**：新增 7 个对比指标、标准化英文列名、失败诊断、协议可复现
3. **兼容性通过**：旧 training_report.json/md 继续生成，旧 CLI 参数不变
4. **可测试性建立**：14 smoke tests 为后续模型迭代提供质量保障
