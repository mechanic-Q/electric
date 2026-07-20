# RL Full Dataset 训练报告

## Metadata

| 字段 | 值 |
|---|---|
| generated_at | 2026-07-20T14:36:19Z |
| git_sha | a68513326c13d765db6748a68e5dfd48816c55a4 |
| time_config | {'freq': '15min', 'points_per_day': 96} |
| seed | 42 |
| algos | ['ppo', 'sac', 'td3'] |
| timesteps_per_algo | 200000 |
| train_range | ['2024-01-01', '2025-09-30'] |
| test_range | ['2025-10-01', '2026-01-15'] |
| tier | tier4 |
| price_proxy | rt_price->price_da |
| reward_fn | profit_only |
| weather_source | cache |

## Training

| 算法 | 状态 | final_reward | duration_s | checkpoint_path |
|---|---|---|---|---|
| ppo | ok | N/A | N/A | N/A |
| sac | ok | N/A | N/A | N/A |
| td3 | ok | N/A | N/A | N/A |

## Backtest

| 策略 | 总收益 | 夏普比率 | 胜率 | 最大回撤 | 交易次数 |
| --- | --- | --- | --- | --- | --- |
| baseline_persistence | 4051823.1529161427 | 2.5488313102521105 | 0.48771619496855345 | -4321051.341959741 | 10176 |
| baseline_mean | 0.0 | 0.0 | 0.0 | 0.0 | 10176 |
| oracle | 131482485.968971 | 101.1481709496822 | 1.0 | 0.0 | 10176 |
| rl_ppo | 20342316.938842922 | 31.484145617938594 | 0.6558569182389937 | -422197.0941358153 | 10176 |
| rl_sac | 11477065.237238968 | 6.047100227942516 | 0.5192610062893082 | -880434.8620968722 | 10176 |
| rl_td3 | 17237199.465849053 | 9.106067234154011 | 0.5473663522012578 | -465587.2814049944 | 10176 |

累计 P&L 图: [ellectric/reports/rl_full_dataset/cumulative_pnl.html](ellectric/reports/rl_full_dataset/cumulative_pnl.html)

## Interpretation

- **hard_threshold_applied**: False
- **summary**: 成功 3/3 算法训练完成。最佳策略: oracle。
