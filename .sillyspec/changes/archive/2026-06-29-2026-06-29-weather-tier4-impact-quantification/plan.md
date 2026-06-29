---
author: lmr
created_at: 2026-06-29 20:43:10
plan_level: light
---

# 轻量计划：Weather Tier4 特征精度影响量化

## 来源

来自 brainstorm 结论：在全量山东 15min 数据上量化 Weather Tier4 对负荷预测精度的影响；修正 ablation 为 Tier3 vs Tier3+weather-only，禁止 raw columns 泄漏；扩展 metadata/report/log；更新测试和模块文档。

## 范围

- `ellectric/scripts/validate_weather_tier4.py` — 修正 ablation 特征隔离、扩展 metadata、增强 Markdown 解释。
- `tests/test_weather_tier4_validation.py` — 覆盖 raw columns 不泄漏、weather columns 记录、metadata schema。
- `docs/Ellectric/modules/feature-engineer.md` — 更新 Weather Tier4 验证语义。
- `ellectric/reports/weather_tier4/weather_tier4_validation.json` — full-run JSON 报告产物。
- `ellectric/reports/weather_tier4/weather_tier4_validation.md` — full-run Markdown 报告产物。
- `ellectric/reports/weather_tier4/weather_tier4_impact.log` — full-run 日志证据。

## Wave 1

- [x] task-01: 修正 Weather Tier4 ablation 特征隔离（覆盖：FR-01, FR-02, D-002@v1）
- [x] task-02: 扩展 validation metadata 与 JSON 报告结构（覆盖：FR-03, FR-06, D-001@v1, D-003@v1, D-004@v1）
- [x] task-03: 增强 Markdown Impact Conclusion（覆盖：FR-04, D-001@v1）

## Wave 2

- [x] task-04: 更新 Weather Tier4 validation 单元测试（覆盖：FR-01, FR-02, FR-03, FR-04, FR-06, D-001@v1, D-002@v1, D-003@v1）
- [x] task-05: 更新 feature-engineer 模块文档（覆盖：FR-04, FR-05, D-001@v1, D-002@v1）

## Wave 3

- [x] task-06: 运行 targeted tests 与 full-run 生成报告证据（覆盖：FR-05, D-003@v1, D-004@v1）

## 验收

- `run_ablation_experiment()` 的 weather 模型特征列等于 Tier3 columns + weather columns，不含 raw Shandong columns。
- JSON 报告包含 `metadata.data_source="shandong"`、`metadata.weather_source`、`metadata.input_rows`、`metadata.report_scope`、`metadata.log_path`。
- JSON 报告包含 `experiments.weather_tier4.weather_columns`。
- `experiments.weather_tier4.feature_count == baseline_tier3.feature_count + len(weather_columns)`。
- Markdown 报告包含 Impact Conclusion，并说明 MAE delta 正负与 report-only 语义。
- `rtk pytest tests/test_weather_tier4_validation.py` 通过。
- full-run 命令生成 `ellectric/reports/weather_tier4/weather_tier4_validation.json`、`weather_tier4_validation.md`、`weather_tier4_impact.log`。
- FeatureEngineer、prepare_features、XGBoostForecaster、ShandongDataLoader 的公开签名不变。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-02, task-03, task-04, task-05 | `hard_threshold_applied=false` 保持；Markdown Impact Conclusion；schema tests |
| D-002@v1 | task-01, task-04, task-05 | raw columns 不进入 weather X；weather columns 记录；module doc 说明隔离实验 |
| D-003@v1 | task-02, task-06 | `metadata.log_path`；reports 目录下 full-run log |
| D-004@v1 | task-02, task-06 | `--no-fetch` full-run；cache/degraded 路径测试 |

## Wave 可行性校验

- Wave 1：task-01 → task-02 → task-03（同一脚本内顺序修改，避免测试基于半成品 schema）。
- Wave 2：task-04、task-05（测试与模块文档可在 Wave 1 后并行）。
- Wave 3：task-06（依赖代码、测试、文档完成后生成 full-run 证据）。
- 关键依赖：task-06 依赖 task-01~05；无循环依赖；allowed_paths 与 task 目标一致。

## 自检

- [x] 输出明确标注 plan_level: light
- [x] 有来源、范围、任务列表、验收标准四个部分
- [x] 来源直接引用已有文档，未重新扩写
- [x] 任务列表清晰且无实现细节
- [x] 任务使用 checkbox 格式
- [x] 验收标准具体可验证
- [x] 所有当前版本 D-xxx@vN 在 plan.md 中可追踪
- [x] 不存在 P0/P1 unresolved blocker
- [x] 没有 Mermaid 图、估时、风险分析
- [x] 没有函数签名、代码示例等实现细节
- [x] plan.md 与 design.md 的文件变更清单一致
