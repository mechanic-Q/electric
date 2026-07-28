# 全量真实运行汇总报告

*生成时间: 2026-07-01*
*输出目录: `ellectric/reports/full_real_run/20260701T061156Z`*

| 任务 | 状态 | 关键指标 |
|---|---|---|
| validate_weather_tier4 | ✅ | baseline_mae=3412.03, weather_mae=2755.47, mae_delta_pct=-19.24, weather_columns=['temp_jinan', 'ghi_jinan', 'wind_speed_jinan', 'precip_jinan', 'humidity_jinan', 'cloud_jinan', 'temp_qingdao', 'ghi_qingdao', 'wind_speed_qingdao', 'precip_qingdao', 'humidity_qingdao', 'cloud_qingdao'], baseline_features=11 |
| validate_renewable_forecaster | ✅ | wind_mae=2309.34, wind_nrmse=0.13, solar_mae=1030.33, solar_nrmse=0.09 |
| compare_price_models | ✅ | lear={'mae': 92.52617858803323, 'rmse': 126.34001831991371, 'mape': 117.09216532161729}, dnn={'mae': 324.4425845539262, 'rmse': 360.658095101112, 'mape': 100.4668899532332}, persistence={'mae': 131.11918958333334, 'rmse': 188.82688617026452, 'mape': 231.508951214036}, weekly_avg={'mae': 97.13806045145331, 'rmse': 143.7424831256067, 'mape': 103.91549842298757} |
| pytest | ✅ | passed=127 |
| verify_time_resolution | ✅ | passed=15, failed=0 |
| rl_ppo | ✅ | final_reward=-1238253268.78, duration_s=3183.70 |
| rl_sac | ✅ | final_reward=-1009398782.75, duration_s=3658.80 |
| rl_td3 | ✅ | final_reward=-979720748.96, duration_s=3314.20 |

---
## 负荷预测 (Weather Tier4 Ablation)
- Baseline Tier1-3 (11 特征): MAE=3412.03
- +Weather Tier4 (23 特征): MAE=2755.47
- MAE Δ: -19.24%
- 12 Weather 列: ['temp_jinan', 'ghi_jinan', 'wind_speed_jinan', 'precip_jinan', 'humidity_jinan', 'cloud_jinan', 'temp_qingdao', 'ghi_qingdao', 'wind_speed_qingdao', 'precip_qingdao', 'humidity_qingdao', 'cloud_qingdao']

## 可再生能源预测
- 风电: MAE=2309.34, nRMSE=0.1342
- 光伏: MAE=1030.33, nRMSE=0.0939

## 电价预测模型对比
- lear: MAE=92.53, RMSE=126.34, MAPE=117.09%
- dnn: MAE=324.44, RMSE=360.66, MAPE=100.47%
- persistence: MAE=131.12, RMSE=188.83, MAPE=231.51%
- weekly_avg: MAE=97.14, RMSE=143.74, MAPE=103.92%

## RL 训练
- PPO: reward=-1238253268.78, duration=3183.7s
- SAC: reward=-1009398782.75, duration=3658.8s
- TD3: reward=-979720748.96, duration=3314.2s

## 测试
- pytest: 127 passed
- verify_time_resolution: 15/15 passed