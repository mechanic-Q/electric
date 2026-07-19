# RL Full Dataset 训练报告

## Metadata

| 字段 | 值 |
|---|---|
| generated_at | 2026-07-19T13:23:27Z |
| git_sha | a05d580ff84257597860789b92849bf80ee79408 |
| time_config | {'freq': '15min', 'points_per_day': 96} |
| seed | 42 |
| algos | ['ppo'] |
| timesteps_per_algo | 20000 |
| train_range | ['2024-01-01', '2025-09-30'] |
| test_range | ['2025-10-01', '2026-01-14'] |
| tier | tier4 |
| price_proxy | rt_price->price_da |
| reward_fn | profit_only |
| weather_source | cache |
| train_max_capacity_mw | 111100.836 |
| test_max_capacity_mw | 99673.38 |

## Training

| 算法 | 状态 | final_reward | duration_s | checkpoint_path |
|---|---|---|---|---|
| ppo | ok | 1773.1253255064432 | 392.3 | models/rl_quick_validation/ppo.zip |

## Backtest

| 策略 | 总收益 | 夏普比率 | 胜率 | 最大回撤 | 交易次数 |
| --- | --- | --- | --- | --- | --- |
| baseline_persistence | 6041414.369733619 | 3.866900534914212 | 0.49236111111111114 | -4321051.341959741 | 10080 |
| baseline_mean | 0.0 | 0.0 | 0.0 | 0.0 | 10080 |
| oracle | 129492894.75215352 | 100.67493507323734 | 1.0 | 0.0 | 10080 |
| rl_ppo | 3685051.3915063078 | 30.50022525189541 | 0.6800595238095238 | -95490.86646445817 | 10080 |

累计 P&L 图: [ellectric/reports/rl_quick_validation/cumulative_pnl.html](ellectric/reports/rl_quick_validation/cumulative_pnl.html)

## Interpretation

- **hard_threshold_applied**: False
- **summary**: 成功 1/1 算法训练完成。最佳策略: oracle。
