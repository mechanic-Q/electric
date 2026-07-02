---
author: lmr
created_at: 2026-07-03 01:16:03
---

# Proposal: Forecast Fallback Metrics + Today Guard

## 背景

用户在 Web Chat 中询问“今天的负荷预测”时，实时负荷预测因 `xgboost_model.joblib` 缺失触发 offline fallback。当前回退回答暴露两个问题：

- Weather Tier4 回退报告展示 `baseline_mae=10`，与真实山东 15min Weather Tier4 验证结果不一致，且缺少单位/实验上下文。
- Agent 直接响应“今天”，但项目数据集是历史山东 15min 数据，不支持真实今天预测。

## 目标

- 修正 Weather Tier4 fallback 指标映射、状态语义和 UI 展示，避免误导用户。
- 增加 Agent “today guard”：用户说“今天/当前/实时”时，不编造实时日期，必须说明数据覆盖范围并询问是否使用数据集最新可用日。
- 保持本次范围只修 fallback 与 prompt 严谨性，不训练模型、不补实时预测链路。

## 非目标

- 不训练或生成 `xgboost_model.joblib`。
- 不新增定时任务、实时数据源、准实时预测。
- 不重构 WebUI 样式系统。
- 不扩大到所有报告的全面指标体系；只处理 Weather Tier4 fallback 必需字段，必要时做最小前端兼容。

## 成功标准

- Weather Tier4 summary 使用真实字段：`baseline_tier3.metrics.mae`、`weather_tier4.metrics.mae`、`delta.mae_delta_pct`。
- fallback payload 中指标语义明确：推荐键名 `mae_baseline_tier3`、`mae_weather_tier4`、`mae_delta_pct`，并带单位/label 元信息。
- `build_forecast_fallback` 可对 `ok` 与 `degraded` 的 Weather Tier4 报告返回 fallback；`degraded` 时 note 明确提示报告降级。
- WebUI result card 渲染带单位/label 的指标，不再把 raw key 直接裸露成易误读数字。
- Agent prompt 明确：没有实时数据时不能回答“今天具体预测值”；应说明数据集最新可用日期或询问用户日期。
- Tests 覆盖 Weather Tier4 metrics 映射、degraded fallback、today guard prompt 文案、前端 metrics label 渲染契约。

## 用户确认

- 用户选择：先做 A（fallback 层修 bug）。
- 用户接受：C（Agent today guard）。
- 用户暂未最终确认：指标命名方案。计划默认采用语义化键名 + unit/label 元信息。
