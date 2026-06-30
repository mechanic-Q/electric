---
author: lmr
created_at: 2026-06-30 21:56:51
---

# 验证报告

## 结论

PASS

Revision 1 修复后验证通过。`compare_price_models` full-run 已成功生成报告产物，四模型 MAE/RMSE/MAPE 均为有限值，目标测试 21 passed。

## 任务完成度

| Task | 结果 | 证据 |
|---|---|---|
| T-01 新增 PyTorch DNN 电价预测器 | PASS | `ellectric/pipeline/price_forecaster_dnn.py` 存在，含 `DNNPriceForecaster`, `train_evaluate`, `predict` |
| T-02 新增 comparison 脚本骨架 | PASS | `ellectric/scripts/compare_price_models.py` 存在，支持 `--dataset shandong` / `--output-dir` / `--dry-run` |
| T-03 四模型统一评估 | PASS | LEAR、DNN、persistence、weekly_avg 均输出有限 MAE/RMSE/MAPE |
| T-04 DM/GW 统计检验 | PASS | pairwise DM/GW table 生成；缺 epftoolbox 时使用 MOCK 标注，不阻塞报告 |
| T-05 生成报告 | PASS | `comparison.json`, `comparison.md`, `residuals.html`, `comparison.log` 均生成 |
| T-06 service/CLI model_type | PASS | `schemas.py` / `handlers.py` / `cli/main.py` 支持 `price_dnn` opt-in |
| T-07 新增测试 | PASS | `tests/test_price_forecaster_dnn.py`, `tests/test_compare_price_models.py`; 21 tests passed |
| T-08 更新模块文档 | PASS | `docs/Ellectric/modules/price-forecaster.md` 含 DNN baseline、报告路径、非 TensorFlow、LEAR 默认说明 |

完成率：8/8 PASS。

## 设计一致性

- 文件变更清单：主要文件均存在。
- DNN baseline：符合 PyTorch MLP、非 TensorFlow、固定小模型方向。
- 比较脚本：包含四模型、统一 metrics、DM/GW、报告输出逻辑。
- 兼容性：`price` 默认 LEAR，`price_dnn` 为 opt-in。
- 报告产物：full-run 已生成 JSON/MD/HTML/log。

## 探针结果

- 未实现标记扫描：变更相关源码未发现 `尚未实现|TODO|FIXME|HACK|XXX`。
- 关键词覆盖：`DNNPriceForecaster`、`PyTorch`、`MLP`、`LEAR`、`persistence`、`weekly_avg`、`MAE`、`RMSE`、`MAPE`、`dm_test`、`gw_test`、`comparison.json`、`comparison.md`、`residuals.html`、`comparison.log`、`price_dnn` 均有实现或文档匹配。
- 测试覆盖：目标测试文件存在，21 tests passed。
- 决策追踪覆盖：D-001@v1~D-004@v1 在 tasks/plan/decisions 中可追踪；requirements.md 未直接引用 D-ID，记录为非阻断 warning。
- Contract parity：无 `.sillyspec/.runtime/contract-artifacts/`，无 `backend/` / `frontend/`，不适用。

## 决策追踪矩阵

| 决策 ID | FR | Task | Evidence | 状态 |
|---|---|---|---|---|
| D-001@v1 | FR-01, FR-08 | task-01, task-02, task-08 | DNN 文件、DNN tests、模块文档 | PASS |
| D-002@v1 | FR-02, FR-03, FR-06, FR-07 | task-03, task-06, task-08 | 山东 comparison 脚本、full-run 报告、模块文档 | PASS |
| D-003@v1 | FR-01, FR-04 | task-01, task-04 | 固定小模型、finite metrics 逻辑 | PASS |
| D-004@v1 | 兼容性 | task-07 | `price` 默认 LEAR，`price_dnn` opt-in | PASS |

## 测试结果

- `rtk pytest tests/test_price_forecaster_dnn.py tests/test_compare_price_models.py -v --tb=short` → PASS, 21 passed。
- `python -m ellectric.cli.main forecast price 24 --help` → PASS, help 中显示 `price_dnn=PyTorch DNN 电价预测`。
- `python -m ellectric.scripts.compare_price_models --dataset shandong --output-dir .sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison` → PASS。

Full-run 产物：

```text
OK .sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/comparison.json
OK .sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/comparison.md
OK .sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/residuals.html
OK .sillyspec/changes/2026-06-29-price-model-comparison/verify-price-comparison/comparison.log
```

Full-run metrics：

```text
lear: MAE=92.53, RMSE=126.34, MAPE=117.09
dnn: MAE≈324.99, RMSE≈361.30, MAPE≈100.67
persistence: MAE=131.12, RMSE=188.83, MAPE=231.51
weekly_avg: MAE=97.14, RMSE=143.74, MAPE=103.92
```

## 技术债务

变更相关文件 TODO/FIXME/HACK/XXX 扫描无结果。

## 变更风险等级

change_risk_profile: unit-sufficient

理由：主要为离线模型、脚本、schema/handler opt-in 和测试；不是 daemon/backend 跨进程、session/lease 状态机或部署启动路径。

## Runtime Evidence

不适用（非 integration-critical / deployment-critical）。

## 代码审查

修复项：

1. `if __name__ == "__main__": main()` 移到文件末尾，避免 `_setup_logging` 定义前调用。
2. baseline metrics 过滤 NaN/Inf actual-prediction pairs，避免山东 `price_da` 大量缺失导致 NaN 指标。
3. weekly_avg 避免空窗口 `nanmean` warning。
4. DM/GW pairwise errors 过滤 NaN/Inf pairs，报告中不再出现 `SKIP — contains NaN/Inf`。
5. `comparison.md` 增加 author/created_at frontmatter，满足 SillySpec 文档元数据检查。

总体评价：PASS，可归档。
