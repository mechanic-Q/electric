---
author: lmr
created_at: 2026-07-03 01:16:03
---

# Requirements: Forecast Fallback Metrics + Today Guard

## FR-01: Weather Tier4 fallback 指标语义化

覆盖决策：D-001@v1

系统必须从 Weather Tier4 报告真实字段提取指标，并输出语义化 metric keys 与单位/label 元信息，避免 `baseline_mae=10` 这类无上下文数字误导用户。

验收：catalog summary / report detail / fallback payload 中能看到 `mae_baseline_tier3`、`mae_weather_tier4`、`mae_delta_pct`，且每个指标有可展示 label/unit。

## FR-02: degraded 报告可 fallback 但必须标注

覆盖决策：D-002@v1

Weather Tier4 报告状态为 `degraded` 时，系统仍可作为 fallback 来源，但必须在 payload/note/UI 中标注报告降级与指标限制。

验收：`build_forecast_fallback("load", FileNotFoundError(...))` 对 degraded 报告返回 fallback dict，包含 `report_status="degraded"` 与降级说明。

## FR-03: Agent today guard

覆盖决策：D-003@v1

Agent 不得把历史山东 15min 数据集说成真实“今天”。用户问“今天/当前/实时”时，必须说明项目没有真实今日数据源，并询问是否使用数据集最新可用日或指定历史日期。

验收：`_SYSTEM_PROMPT` 包含 today guard 规则；相关 prompt static test 通过。

## FR-04: WebUI 指标 label/unit 渲染

覆盖决策：D-004@v1

WebUI result card 应优先使用 `metrics_meta` 渲染指标 label/unit；没有 meta 的旧报告保持原始渲染兼容。

验收：SSE payload 示例包含 `metrics_meta` 时，前端 `renderMetrics` 输出带单位的可读指标。

## FR-05: 不改变实时预测训练范围

覆盖决策：D-002@v1, D-003@v1

本变更不得训练模型、不得新增实时数据源、不得把 fallback 修复伪装成实时预测能力。

验收：不新增模型训练入口；`/predict` schema 不变；文档/Prompt 明确 fallback 与真实预测区别。
