---
author: lmr
created_at: 2026-06-30 22:03:54
---

# 模块影响分析：电价模型对比报告

## 输入来源

- 变更：`2026-06-29-price-model-comparison`
- 声明范围：`proposal.md` / `design.md`
- 任务范围：`tasks.md` / `plan.md`
- 真实变更：当前工作区目标文件清单
- 模块映射：`.sillyspec/docs/Ellectric/modules/_module-map.yaml`

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| price-forecaster | 新增 / 逻辑变更 / 文档变更 | `ellectric/pipeline/price_forecaster_dnn.py`, `ellectric/scripts/compare_price_models.py`, `docs/Ellectric/modules/price-forecaster.md`, `tests/test_price_forecaster_dnn.py`, `tests/test_compare_price_models.py` | 新增 PyTorch MLP DNN 电价预测器；新增山东 LEAR/DNN/persistence/weekly_avg 统一对比脚本；生成 metrics、DM/GW pairwise table、JSON/MD/HTML/log 报告；更新模块文档。 | false |
| statistical-tests | 调用关系变更 | `ellectric/scripts/compare_price_models.py` | 复用 DM/GW 检验能力；epftoolbox 不存在时使用明确 MOCK 标注；pairwise error series 过滤 NaN/Inf。 | false |
| service-api | 接口变更 / 调用关系变更 | `ellectric/service/schemas.py`, `ellectric/service/handlers.py`, `ellectric/cli/main.py` | `ForecastRequest.model_type` 增加 `price_dnn` opt-in；handler 分派 DNN price forecaster；CLI help 展示 `price_dnn`。 | true |

## 未匹配文件

| 文件 | 原因 | 处理 |
|---|---|---|
| `.sillyspec/changes/2026-06-29-price-model-comparison/plan.md` | 变更过程文档，不属于代码模块 | 随变更归档 |
| `.sillyspec/changes/2026-06-29-price-model-comparison/verify-result.md` | 验证报告，不属于代码模块 | 随变更归档 |
| `.sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/comparison.json` | 验证证据产物，不属于代码模块 | 随变更归档 |
| `.sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/comparison.md` | 验证证据产物，不属于代码模块 | 随变更归档 |
| `.sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/residuals.html` | 验证证据产物，不属于代码模块 | 随变更归档 |
| `.sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/comparison.log` | 验证证据产物，不属于代码模块 | 随变更归档 |

## 三重交叉验证

### 声明范围

- PyTorch DNN 电价预测器。
- LEAR / DNN / persistence / weekly_avg 比较脚本。
- DM/GW 显著性检验。
- JSON、Markdown、Plotly HTML、运行日志。
- service/CLI `model_type="price_dnn"` 可选扩展。

### 任务范围

- `ellectric/pipeline/price_forecaster_dnn.py`
- `ellectric/scripts/compare_price_models.py`
- `ellectric/service/schemas.py`
- `ellectric/service/handlers.py`
- `ellectric/cli/main.py`
- `tests/test_price_forecaster_dnn.py`
- `tests/test_compare_price_models.py`
- `docs/Ellectric/modules/price-forecaster.md`

### 真实变更范围

- 目标代码与测试文件均在任务范围内。
- 变更目录下验证产物属于归档证据。
- 当前工作区还存在 unrelated renewable forecaster staged files 与 cocoindex 本地文件；本分析只覆盖 `2026-06-29-price-model-comparison` 目标文件。

## 影响说明

### price-forecaster

`price-forecaster` 模块从单一 LEAR price forecaster 扩展为 price-model comparison 能力：

- DNN baseline 使用 PyTorch MLP，不引入 TensorFlow。
- Comparison script 统一山东数据切分与四模型指标输出。
- Baseline 评估过滤 NaN/Inf actual-prediction pairs，避免山东日前价格缺失导致 NaN 指标。
- Full-run 已验证生成四类报告产物。

### statistical-tests

统计检验模块没有直接修改，但 comparison script 新增调用关系：

- Pairwise DM/GW 覆盖四模型组合。
- `epftoolbox` 缺失时仍生成 MOCK 标注，metrics 不被阻断。
- Error series 长度不同时尾部对齐。

### service-api

服务和 CLI 增加 `price_dnn` 可选路径：

- 默认 `price` 仍走 LEAR。
- `price_dnn` 需要用户显式选择。
- 由于 `_module-map.yaml` 当前无 service/CLI 模块条目，标记 `needs_review=true`，建议后续 scan 时补充模块索引。

## 更新结果

| 目标 | 状态 | 内容 |
|---|---|---|
| `_module-map.yaml: price-forecaster` | 已更新 | 增加 DNN/comparison paths、tags、aliases、entrypoints、main_symbols；depends_on 增加 statistical-tests；used_by 增加 service-api |
| `_module-map.yaml: statistical-tests` | 已更新 | used_by 增加 price-forecaster |
| `_module-map.yaml: service-api` | 已新增 | 增加 service/CLI 模块条目，标记 needs_review=true |
| `modules/price-forecaster.md` | 已更新 | 补充 DNN baseline、四模型 comparison report、NaN/Inf baseline 处理、报告产物说明 |
| `modules/statistical-tests.md` | 已更新 | 补充 compare script 复用、MOCK fallback、NaN/Inf 过滤与 15min horizon |
| `modules/service-api.md` | 已新增 | 记录 forecast schema、handler、CLI、price_dnn opt-in 路径 |

## 建议

- 后续可运行 SillySpec scan 重建模块索引，进一步校验 service/CLI 模块边界。
- 本次归档前无需阻断；`verify-result.md` 已给出 PASS 证据。
