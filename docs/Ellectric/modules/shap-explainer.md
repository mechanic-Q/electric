
---
schema_version: 1
doc_type: module-card
module_id: shap-explainer
---

# shap-explainer

## 定位

SHAP 模型可解释性模块。使用 TreeExplainer (XGBoost) 和
LinearExplainer (LEAR/Lasso) 解释单个预测，并跨模型对比特征重要性。

## 契约摘要

- `explain_xgboost_sample(model, X, sample_idx, max_display) -> go.Figure` — XGBoost SHAP waterfall
- `explain_lear_sample(model, X, sample_idx, max_display) -> go.Figure` — LEAR Lasso SHAP waterfall
- `feature_importance_ranking(models, feature_names) -> pd.DataFrame` — 跨模型特征排名

## 关键逻辑

- XGBoost: `shap.TreeExplainer(model._model)`
- LEAR: `shap.LinearExplainer(model._model, X)`
- 输出 plotly Figure（瀑布图）或 DataFrame（排名表）
- 不修改传入的 model 或 X

## 注意事项

- 依赖 shap 包，未安装时 raise RuntimeError
- sample_idx 越界 → IndexError
- max_display < 1 → 默认 10

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
