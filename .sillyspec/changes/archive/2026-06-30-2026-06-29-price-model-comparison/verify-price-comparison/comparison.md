---
author: lmr
created_at: 2026-06-30 21:56:30
---

# Price Model Comparison Report

- **Dataset**: shandong
- **Feature tier**: tier3
- **Date range**: 2024-01-01 01:00:00+00:00 ~ 2025-12-31 00:00:00+00:00
- **Splits**: 5-fold TimeSeriesSplit
- **Samples (clean)**: 17520
- **Features**: 14

## Metrics Summary

| Model | MAE | RMSE | MAPE (%) |
|---|---|---|---|
| dnn | 324.99 | 361.30 | 100.67 |
| lear | 92.53 | 126.34 | 117.09 |
| persistence | 131.12 | 188.83 | 231.51 |
| weekly_avg | 97.14 | 143.74 | 103.92 |

## Statistical Tests

### DM/GW Pairwise Test Results

| Model 1 | Model 2 | DM stat | DM p-value | GW stat | GW p-value | Notes |
|---|---|---|---|---|---|---|
| lear | dnn | 0.497 (No) | 0.732 | -0.138 (No) | 0.599 | MOCK — epftoolbox not installed |
| lear | persistence | 0.497 (No) | 0.732 | -0.138 (No) | 0.599 | MOCK — epftoolbox not installed |
| lear | weekly_avg | 0.497 (No) | 0.732 | -0.138 (No) | 0.599 | MOCK — epftoolbox not installed |
| dnn | persistence | 0.497 (No) | 0.732 | -0.138 (No) | 0.599 | MOCK — epftoolbox not installed |
| dnn | weekly_avg | 0.497 (No) | 0.732 | -0.138 (No) | 0.599 | MOCK — epftoolbox not installed |
| persistence | weekly_avg | 0.497 (No) | 0.732 | -0.138 (No) | 0.599 | MOCK — epftoolbox not installed |

## Residual Interpretation

- Lower MAE/RMSE indicates better point forecast accuracy.
- MAPE should be interpreted with caution near zero prices.
- Statistically significant DM p-value (< 0.05) indicates the 
  forecast errors differ meaningfully between the two models.
- GW test extends DM to nested model comparisons.

## Caveats

- DNN is a PyTorch MLP baseline, NOT the epftoolbox DNN implementation.
- DNN is PyTorch MLP baseline, not epftoolbox DNN
