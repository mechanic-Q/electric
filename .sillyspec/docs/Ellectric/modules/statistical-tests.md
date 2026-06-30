---
schema_version: 1
doc_type: module-card
module_id: statistical-tests
author: lmr
created_at: 2026-06-30 22:16:05
---

# statistical-tests

## 定位

DM/GW 统计检验封装，用于比较预测误差序列是否存在显著差异。主要支持 LEAR 与基准模型对比，也被 price comparison 脚本复用做四模型 pairwise 检验。

## 契约摘要

- `run_statistical_tests(errors_chinese, errors_benchmarks, h=24, crit='MAE') -> dict`
- 输出: `{dm_results, gw_results, summary}` 含 dataset, stat, p-value, significant
- `compare_price_models.run_dm_gw_pairwise(model_results, h=96, crit='MAE') -> dict`

## 关键逻辑

- 调用 `epftoolbox.evaluation.dm_test/gw_test`
- 当 epftoolbox 不可用时优雅回退为 mock 结果，并在报告中明确标注 MOCK
- 边界处理：空/Nan/Inf 序列、长度不匹配
- Price comparison 调用前会过滤 NaN/Inf actual-prediction pairs，避免山东日前价格缺失导致 pairwise 全部跳过
- 不同长度误差序列按尾部对齐后比较

## 注意事项

- 在 epftoolbox venv 中运行才能获得真实 DM/GW 结果
- 主环境未安装 epftoolbox 时，统计检验只作为报告结构验证，不代表真实显著性
- 不含 Bonferroni 等多重比较校正
- 15min 数据的 day-ahead horizon 通常为 `h=96`

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
