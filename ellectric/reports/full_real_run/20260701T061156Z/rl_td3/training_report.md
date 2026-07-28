# RL Full Dataset 训练报告

## Metadata

| 字段 | 值 |
|---|---|
| generated_at | 2026-07-01T07:20:25Z |
| git_sha | bbe0efa8c606b450322ed6a768fea6222ecd2421 |
| time_config | {'freq': '15min', 'points_per_day': 96} |
| seed | 42 |
| algos | ['td3'] |
| timesteps_per_algo | 50000 |
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
| td3 | ok | -979720748.9631712 | 3314.2 | ellectric/reports/full_real_run/20260701T061156Z/rl_td3/checkpoints/td3.zip |

## Backtest

| 策略 | 总收益 | 夏普比率 | 胜率 | 最大回撤 | 交易次数 |
| --- | --- | --- | --- | --- | --- |
| baseline_persistence | -9062664.855351645 | -28.21429439378405 | 0.15109126984126983 | -9039547.178321693 | 10080 |
| baseline_mean | -30987986.980334345 | -51.88693438674839 | 0.15109126984126983 | -30964869.303304464 | 10080 |
| oracle | -4.248357432112609 | -98.58720360494073 | 0.15109126984126983 | -4.247606358532706 | 10080 |
| rl_td3 | -136009118.54514742 | -112.5954663150341 | 0.15109126984126983 | -136005399.6266272 | 10080 |

累计 P&L 图: [ellectric/reports/full_real_run/20260701T061156Z/rl_td3/cumulative_pnl.html](ellectric/reports/full_real_run/20260701T061156Z/rl_td3/cumulative_pnl.html)

## Interpretation

- **hard_threshold_applied**: False
- **summary**: 成功 1/1 算法训练完成。最佳策略: oracle。
