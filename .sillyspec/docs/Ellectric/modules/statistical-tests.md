---
schema_version: 1
doc_type: module-card
module_id: statistical-tests
---
# statistical-tests
## 定位
DM/GW 统计检验封装 — 中国 LEAR vs 5 个基准数据集
## 契约摘要
- `run_statistical_tests(errors_chinese, errors_benchmarks, h=24, crit='MAE') -> dict`
- 输出: `{dm_results, gw_results, summary}` 含 dataset, stat, p-value, significant
## 关键逻辑
- 调用 epftoolbox.evaluation.dm_test/gw_test
- 当 epftoolbox 不可用时优雅回退为 mock 结果
- 边界处理：空/Nan/Inf 序列、长度不匹配
## 注意事项
- 在 epftoolbox venv 中运行才能获得真实结果
- 不含 Bonferroni 等多重比较校正
