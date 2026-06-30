---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Design: 电价模型对比报告

## 背景

当前 `price_forecaster.py` 已实现 LEAR(Lasso) 电价预测，`statistical_tests.py` 提供 DM/GW 检验。但项目缺少统一的电价模型对比报告，不能回答“LEAR 是否优于 DNN 和 naive baseline”。

## 设计目标

- 在山东数据上统一比较 LEAR、PyTorch DNN、persistence、weekly_avg。
- 输出 metrics + DM/GW significance + residual visualization。
- 保持轻量依赖，不引入 TensorFlow。
- 不改变现有 LEAR 默认行为。

## 非目标

- 不使用 epftoolbox DNN 原始 TensorFlow 实现。
- 不跑海外 5 市场基准。
- 不做自动调参。
- 不做模型注册或服务部署。

## 决策/方案选择

- **方案选择**: 使用 PyTorch MLP 实现 DNN baseline，只在山东数据上对比 LEAR/DNN/persistence/weekly_avg。
- **不选方案**: 不引入 TensorFlow，不跑 epftoolbox 海外 5 市场，不做调参刷榜。
- **取舍理由**: PyTorch 已是项目依赖，避免 TensorFlow 环境冲突；山东数据优先保证业务语境一致。
- **执行策略**: 先离线比较脚本 + 报告产物；service/CLI DNN 选项作为低风险扩展。

## 总体方案

### DNN 模型

新增 `ellectric/pipeline/price_forecaster_dnn.py`：

- `DNNPriceForecaster`
  - PyTorch MLP: input → hidden(128) → dropout → hidden(64) → output。
  - AdamW optimizer。
  - Early stopping 可选，默认小 epoch。
  - 接口：`train_evaluate(X, y)` / `predict(X)`。

### 比较脚本

新增 `ellectric/scripts/compare_price_models.py`：

1. 加载山东 price dataset。
2. 构建与 LEAR 对齐的滞后 + 日历特征。
3. 统一 time split。
4. 训练/预测四个模型：LEAR、DNN、persistence、weekly_avg。
5. 计算 MAE/RMSE/MAPE。
6. 调 DM/GW 生成 pairwise table。
7. 写 JSON/MD/HTML/log 报告。

### Baselines

- persistence: 上一时间点价格。
- weekly_avg: 同一星期位置历史均值。

### 报告结构

`comparison.json`:
- `metadata`
- `models`
- `metrics`
- `statistical_tests`
- `artifacts`
- `notes`

`comparison.md`:
- Summary
- Metrics table
- DM/GW table
- Residual interpretation
- Caveats

`residuals.html`:
- residual time series
- residual distribution
- by-hour error heatmap

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 新增 | `ellectric/pipeline/price_forecaster_dnn.py` |
| 新增 | `ellectric/scripts/compare_price_models.py` |
| 可选修改 | `ellectric/service/schemas.py` |
| 可选修改 | `ellectric/service/handlers.py` |
| 可选修改 | `ellectric/cli/main.py` |
| 新增 | `tests/test_price_forecaster_dnn.py` |
| 新增 | `tests/test_compare_price_models.py` |
| 更新 | `docs/Ellectric/modules/price-forecaster.md` |
| 生成 | `ellectric/reports/price_comparison/comparison.json` |
| 生成 | `ellectric/reports/price_comparison/comparison.md` |
| 生成 | `ellectric/reports/price_comparison/residuals.html` |
| 生成 | `ellectric/reports/price_comparison/comparison.log` |

## 兼容策略

- LEAR 仍是默认 price forecast。
- DNN 和 comparison 是 opt-in。
- 统计检验失败时报告 degraded，不阻断 metrics 输出。

## 风险

| 风险 | 缓解 |
|---|---|
| PyTorch 训练慢 | 默认小 epoch + CPU 小模型 |
| DNN 表现不如 LEAR | 如实报告，不调参刷榜 |
| MAPE 零值问题 | 沿用 compute_metrics 中 zero mask 策略 |
| 统计检验依赖缺失 | fallback/degraded note |

## 验收

- 单元测试通过。
- 山东 full-run comparison report 生成。
- JSON/MD/HTML/log 产物存在。
- 报告明确说明 DNN 是 PyTorch MLP baseline，不是 epftoolbox 原始 DNN。
