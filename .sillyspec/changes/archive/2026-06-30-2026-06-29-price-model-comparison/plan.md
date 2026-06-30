---
plan_level: full
author: lmr
created_at: 2026-06-30 04:09:00
---

# 实现计划：电价模型对比报告

## 来源

来自 `design.md`：使用山东数据统一对比 LEAR、PyTorch DNN、persistence、weekly_avg，输出 metrics、DM/GW 统计检验和 residual visualization；不引入 TensorFlow，不跑海外 5 市场。

## Spike 前置验证

| Spike | 验证内容 | 不通过后果 |
|---|---|---|
| spike-01 | 确认当前 price feature 构造可被 LEAR 和 DNN 共用 | 若不可共用，先抽取 comparison 专用特征构造 |
| spike-02 | 确认 PyTorch 依赖在主环境可 import | 若不可用，降级为 sklearn MLP 或阻断 DNN task |

## Wave 1（model core）

- [x] task-01: 新增 PyTorch DNN 电价预测器（覆盖：FR-01, D-001@v1, D-003@v1）
- [x] task-02: 新增 DNN forecaster 单元测试（覆盖：FR-08）

## Wave 2（comparison script）

- [x] task-03: 新增 `compare_price_models.py` 脚本骨架与统一数据切分（覆盖：FR-02, FR-03, D-002@v1）
- [x] task-04: 实现 LEAR/DNN/persistence/weekly_avg 统一评估（覆盖：FR-02, FR-03, FR-04）
- [x] task-05: 接入 DM/GW 统计检验（覆盖：FR-05）

## Wave 3（reports/integration）

- [x] task-06: 生成 JSON/MD/HTML/log 报告（覆盖：FR-06, FR-07）
- [x] task-07: 可选扩展 service/CLI 支持 price DNN model_type（覆盖：D-004@v1）
- [x] task-08: 更新模块文档（覆盖：D-001@v1, D-002@v1）

## 验收

- `rtk pytest tests/test_price_forecaster_dnn.py tests/test_compare_price_models.py` 通过。
- `python -m ellectric.scripts.compare_price_models --dataset shandong` 生成 comparison.json/comparison.md/residuals.html/comparison.log。
- 报告包含四模型 MAE/RMSE/MAPE 和 DM/GW pairwise table。
- 不引入 TensorFlow。
- LEAR 仍是默认 price forecast。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-02, task-08 | PyTorch DNN tests + doc |
| D-002@v1 | task-03, task-06, task-08 | 山东 comparison report |
| D-003@v1 | task-01, task-04 | fixed DNN config |
| D-004@v1 | task-07 | LEAR default unchanged test |

## Wave 可行性校验

- Wave 1 先实现 DNN core，供 Wave 2 比较脚本调用。
- Wave 2 统一评估和统计检验，不依赖 service/CLI。
- Wave 3 生成报告和低风险集成。
- 无循环依赖。

## 自检

✓ 输出明确标注 plan_level: full
✓ 有 spike、wave、验收、覆盖矩阵
✓ 所有 D-xxx@vN 在计划中可追踪
✓ task 使用 checkbox 格式
✓ 未引入 TensorFlow 或海外数据 scope
