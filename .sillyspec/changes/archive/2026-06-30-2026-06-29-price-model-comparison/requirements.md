---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Requirements: 电价模型对比报告

## 功能需求

- [ ] **FR-01**: 新增 `DNNPriceForecaster`，基于 PyTorch MLP。
- [ ] **FR-02**: 比较脚本同时评估 LEAR、DNN、persistence、weekly_avg。
- [ ] **FR-03**: 四模型使用同一山东数据、同一时间切分、同一 metrics。
- [ ] **FR-04**: 输出 MAE/RMSE/MAPE。
- [ ] **FR-05**: 调用 DM/GW 检验，输出 pairwise significance table。
- [ ] **FR-06**: 输出 Plotly residuals.html，对比残差分布与时间序列。
- [ ] **FR-07**: 报告文件写入 `ellectric/reports/price_comparison/`。
- [ ] **FR-08**: 新增测试覆盖 DNN forecaster、compare script、report schema。

## 非功能需求

- 使用 PyTorch，不新增 TensorFlow。
- DNN 训练默认小模型，CPU 可运行。
- 不改变现有 price forecast 默认行为。

## 验收命令

- `rtk pytest tests/test_price_forecaster_dnn.py tests/test_compare_price_models.py`
- `python -m ellectric.scripts.compare_price_models --dataset shandong`
