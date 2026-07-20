# Evaluation Report

- **generated_at**: 2026-07-20T14:36:19Z
- **git_sha**: a68513326c13d765db6748a68e5dfd48816c55a4

## Protocol

| Parameter | Value |
|---|---|
| train_start | 2024-01-01 |
| train_end | 2025-09-30 |
| test_start | 2025-10-01 |
| test_end | 2026-01-15 |
| algos | ppo, sac, td3 |
| baselines | baseline_persistence, baseline_mean, oracle |
| seed | 42 |
| timesteps | 200000 |
| tier | tier4 |
| price_proxy | rt_price->price_da |
| checkpoint_dir | models/rl_full_dataset |
| report_dir | ellectric/reports/rl_full_dataset |

## Training

| algo | status | final_reward | duration_s | error |
| --- | --- | --- | --- | --- |
| ppo | ok | N/A | N/A |  |
| sac | ok | N/A | N/A |  |
| td3 | ok | N/A | N/A |  |

## Rankings

| strategy | total_pnl | sharpe | win_rate | max_drawdown | profit_factor | volatility | oracle_gap | baseline_delta | rank | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | 131482485.968971 | 101.1481709496822 | 1.0 | 0.0 | inf | 11955.970304313047 | 0.0 | 127430662.81605485 | 1.0 | ok |
| rl_ppo | 20342316.938842922 | 31.484145617938594 | 0.6558569182389937 | -422197.0941358153 | 3.464712379565658 | 5942.695239897546 | 0.845284968648649 | 16290493.78592678 | 2.0 | ok |
| rl_td3 | 17237199.465849053 | 9.106067234154011 | 0.5473663522012578 | -465587.2814049944 | 1.3041718788186554 | 17410.48259910121 | 0.868901174640728 | 13185376.31293291 | 3.0 | ok |
| rl_sac | 11477065.237238968 | 6.047100227942516 | 0.5192610062893082 | -880434.8620968722 | 1.1926938287180622 | 17456.558900424778 | 0.9127103115471403 | 7425242.084322825 | 4.0 | ok |
| baseline_persistence | 4051823.1529161427 | 2.5488313102521105 | 0.48771619496855345 | -4321051.341959741 | 1.0846463437844378 | 14621.244619608113 | 0.9691835522955328 | 0.0 | 5.0 | ok |
| baseline_mean | 0.0 | 0.0 | 0.0 | 0.0 | inf | 0.0 | 1.0 | -4051823.1529161427 | 6.0 | ok |

## Failure Diagnosis

_All strategies completed successfully._

## Artifacts

- **Evaluation Report (JSON)**: /home/lmr/projects/Electric/ellectric/reports/rl_full_dataset/evaluation_report.json
- **Evaluation Metrics (CSV)**: /home/lmr/projects/Electric/ellectric/reports/rl_full_dataset/evaluation_metrics.csv
- **Evaluation Report (Markdown)**: /home/lmr/projects/Electric/ellectric/reports/rl_full_dataset/evaluation_report.md
- **Cumulative P&L (HTML)**: ellectric/reports/rl_full_dataset/cumulative_pnl.html
