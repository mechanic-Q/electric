---
schema_version: 1
doc_type: module-card
module_id: price-forecaster
---
# price-forecaster
## 定位
LEAR 电价预测器 — Lasso + 滞后特征 + 日历特征 + 滚动统计
## 契约摘要
- `LEARForecaster(alpha=0.01, max_iter=10000, random_state=42)`
- `train_evaluate(df, tier) -> dict{predictions, actuals, metrics, model, feature_importance}`
- `predict(X) -> np.ndarray`, `save_model/load_model(path)`
- `plot_price_forecast(df, preds) -> go.Figure`, `plot_coefficients() -> go.Figure`
## 关键逻辑
- Tier 1-3 渐进式特征 (6/11/14 列)
- TimeSeriesSplit(n_splits=5, gap=TimeConfig.points_per_day), StandardScaler fit-on-train-only
- L1 正则化自动特征选择
- 与 XGBoostForecaster 同构接口
## 注意事项
- 目标变量为 price_da（日前价格），不是 load_mw
- 不处理 price_rt（实时价格预测不在范围内）
## DNNPriceForecaster
**定位:** PyTorch MLP 电价预测 baseline（轻量深度学习对比模型）

### 契约摘要
- `DNNPriceForecaster(input_dim=30, lr=1e-3, epochs=50)`
- `train_evaluate(X, y, n_splits=5) -> dict{predictions, actuals, metrics}`
- `predict(X) -> np.ndarray`

### 架构
- 3 层 MLP: `Linear(128) → ReLU → Dropout(0.2) → Linear(64) → ReLU → Linear(1)`
- 优化器: AdamW, 损失: MSELoss

### 关键说明
- **PyTorch 实现**, 不是 TensorFlow / epftoolbox DNN
- feature 对齐 LEAR 的滞后 + 日历特征（同一套特征工程）
- 不做超参数搜索, 仅作为 DNN baseline 用于对比
- **可选 opt-in 模型**, 不替代 LEAR 作为默认预测器
- 默认模型仍然为 `LEARForecaster`

## 模型对比报告
执行 `python -m ellectric.scripts.compare_price_models` 生成对比报告, 支持 4 个模型: LEAR, DNN, persistence, weekly_avg。

### 报告产物
| 文件 | 路径（相对项目根目录） | 说明 |
|------|------------------------|------|
| JSON | `ellectric/reports/price_comparison/comparison.json` | 完整结果（指标 + 统计检验 + 预测值） |
| Markdown | `ellectric/reports/price_comparison/comparison.md` | 可读报告 |
| HTML | `ellectric/reports/price_comparison/residuals.html` | 交互式残差图（plotly） |
| Log | `ellectric/reports/price_comparison/comparison.log` | 训练日志 |

### 统计检验
- DM (Diebold-Mariano) / GW (Giacomini-White) 成对检验
- 优先使用 epftoolbox 实现, fallback 到 mock 值（epftoolbox 不可用时）
## 变更索引
- ql-20260607-001-3f2a | predict() 支持 scaler 转换: 新增 self._scaler, save/load 包含 scaler
