---
author: lmr
created_at: 2026-06-28 00:57:11
---

# Weather Tier4 Validation 决策台账

## D-001@v1: 报告式验证优先于硬阈值验收

- type: boundary
- status: accepted
- source: user
- priority: P1
- question: 首轮 Weather Tier4 validation 是否需要设置 MAE/RMSE/MAPE 提升硬阈值？
- answer: 使用现有项目默认数据，只生成可复现实验报告，不设硬性精度提升阈值。
- normalized_requirement: 验证流程必须输出 baseline vs Tier4 指标和 delta，但不得因 Tier4 未提升精度而判定流程失败。
- impacts: [FR-001, FR-002, FR-003, verify-report]
- evidence: Step 6 用户选择 B；Step 9 用户确认设计。

## D-002@v1: Tier4 是可选增强，不保证精度提升

- type: compatibility
- status: accepted
- source: docs
- priority: P1
- question: Weather Tier4 缺失或未提升精度时应如何处理？
- answer: Tier4 为可选增强层，天气数据为小时级 ffill 到 15min 粒度，不保证预测精度提升；天气源失败时降级为无 weather 列。
- normalized_requirement: 验证脚本必须兼容 weather 缺失/降级，并在报告中记录 weather_features_available 与降级原因。
- impacts: [FR-001, FR-004, verify-degraded]
- evidence: docs/Ellectric/modules/feature-engineer.md:23; docs/Ellectric/scan/ARCHITECTURE.md:217; ellectric/pipeline/features.py:215.

## D-003@v1: 采用可复现脚本 + 报告产物

- type: architecture
- status: accepted
- source: user
- priority: P1
- question: Weather Tier4 validation 应采用 notebook-only、脚本化报告，还是测试-only？
- answer: 选择方案B：可复现脚本 + JSON/Markdown 报告产物。
- normalized_requirement: 新增脚本入口运行默认数据验证，生成机器可读 JSON 与人类可读 Markdown 报告，并补测试覆盖报告 schema 与降级行为。
- impacts: [FR-001, FR-002, FR-003, FR-004, task-script, task-tests]
- evidence: Step 8 用户选择 B；Step 9 用户确认设计。
