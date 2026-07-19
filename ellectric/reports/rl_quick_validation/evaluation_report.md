# Evaluation Report

- **generated_at**: 2026-07-19T13:23:27Z
- **git_sha**: a05d580ff84257597860789b92849bf80ee79408

## Protocol

| Parameter | Value |
|---|---|
| train_start | 2024-01-01 |
| train_end | 2025-09-30 |
| test_start | 2025-10-01 |
| test_end | 2026-01-14 |
| algos | ppo |
| baselines | baseline_persistence, baseline_mean, oracle |
| seed | 42 |
| timesteps | 20000 |
| tier | tier4 |
| price_proxy | rt_price->price_da |
| checkpoint_dir | models/rl_quick_validation |
| report_dir | ellectric/reports/rl_quick_validation |

## Training

| algo | status | final_reward | duration_s | error |
| --- | --- | --- | --- | --- |
| ppo | ok | 1773.1253255064432 | 392.3 |  |

## Rankings

| strategy | total_pnl | sharpe | win_rate | max_drawdown | profit_factor | volatility | oracle_gap | baseline_delta | rank | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | 129492894.75215352 | 100.67493507323734 | 1.0 | 0.0 | inf | 11943.073421830208 | 0.0 | 123451480.3824199 | 1.0 | ok |
| baseline_persistence | 6041414.369733619 | 3.866900534914212 | 0.49236111111111114 | -4321051.341959741 | 1.131684121971253 | 14506.650366522164 | 0.9533455918079772 | 0.0 | 2.0 | ok |
| baseline_mean | 0.0 | 0.0 | 0.0 | 0.0 | inf | 0.0 | 1.0 | -6041414.369733619 | 3.0 | ok |
| rl_ppo |  |  |  |  |  |  |  |  |  | error |

## Failure Diagnosis

| strategy | status | error |
|---|---|---|
| rl_ppo | error | 模型未训练，请先调用 train() |

## Artifacts

- **Evaluation Report (JSON)**: /home/lmr/projects/Electric-rl-reward/ellectric/reports/rl_quick_validation/evaluation_report.json
- **Evaluation Metrics (CSV)**: /home/lmr/projects/Electric-rl-reward/ellectric/reports/rl_quick_validation/evaluation_metrics.csv
- **Evaluation Report (Markdown)**: /home/lmr/projects/Electric-rl-reward/ellectric/reports/rl_quick_validation/evaluation_report.md
- **Cumulative P&L (HTML)**: ellectric/reports/rl_quick_validation/cumulative_pnl.html
