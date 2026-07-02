---
author: lmr
created_at: 2026-07-03 01:16:03
---

# Design: Forecast Fallback Metrics + Today Guard

## 背景

Web Chat 已接入 forecast offline fallback。用户询问“今天的负荷预测”时，实时负荷模型缺失会回退到 Weather Tier4 离线报告。当前回退链路能避免 500，但报告指标和时间口径仍可能误导用户。

## 问题描述

- Weather Tier4 回退 payload 中的指标命名缺少实验上下文和单位，前端裸渲染后容易把降级/占位指标误读成真实负荷预测值。
- `build_forecast_fallback` 对报告状态的处理过窄或语义不清，`degraded` 报告需要可回退但必须显式标注质量限制。
- Agent 对“今天/当前/实时”问题缺少防护，可能把历史数据集最新可用日说成真实今天。

## 目标

- 让 Weather Tier4 fallback 返回语义化、带单位/label 的指标。
- 让 degraded 离线报告可以作为 fallback 来源，但在 payload、note 和 UI 中明确标注。
- 让 Agent 对“今天/实时”查询保持诚实：不能给真实今天预测时必须说明原因并要求用户指定历史日期或确认使用数据集最新可用日。

## 非目标

- 不训练或生成 `xgboost_model.joblib`。
- 不新增实时数据源、定时任务或准实时预测链路。
- 不改变 `/predict` 请求/响应 schema。
- 不重做 WebUI 布局或视觉风格。
- 不把所有报告统一迁移到新指标体系；只做 Weather Tier4 fallback 所需最小改动。

## 约束/风险/Trade-off

- 山东 15min 数据是历史数据，不能被表述为真实今天预测。
- `ReportSummary.metrics` 当前只允许 scalar 值；若新增 `metrics_meta`，必须保持旧 API 客户端兼容。
- Weather Tier4 报告可能真实处于 `degraded`，fallback 可用但必须显式提示质量限制。
- 前端应支持没有 `metrics_meta` 的旧报告，避免破坏 renewable/price/RL 报告卡片。
- 不训练模型意味着用户仍可能拿不到实时预测数值；本变更只提升 fallback 事实准确性和交互诚实性。

## 文件变更清单

| 文件 | 改动 |
|---|---|
| `ellectric/service/schemas.py` | 可选新增 `metrics_meta` 到报告 schema。 |
| `ellectric/service/catalog.py` | 修 Weather Tier4 summary 指标映射、status、meta。 |
| `ellectric/service/handlers.py` | 修 forecast fallback 对 `degraded` 的处理与 note。 |
| `ellectric/llm/agent.py` | 增加 today guard prompt。 |
| `ellectric/api/static/index.html` | 支持 metrics label/unit 渲染与 degraded note。 |
| `tests/test_service_catalog.py` | 覆盖 metrics mapping 与 degraded fallback。 |
| `tests/test_api_catalog.py` | 覆盖 report detail 输出 `metrics_meta`。 |
| `tests/test_chat_streaming_events.py` | 更新 fallback payload contract。 |
| `tests/test_agent_prompt.py` | 可新增，静态断言 today guard prompt。 |

## 设计决策

### D-001@v1: Weather Tier4 指标采用语义化键名

Weather Tier4 summary 不再只输出 `baseline_mae` / `weather_mae` 这种容易误读的 raw key。改为：

- `mae_baseline_tier3`
- `mae_weather_tier4`
- `mae_delta_pct`

同时新增 `metrics_meta` 或等价结构，提供 label/unit：

- `mae_baseline_tier3`: label=`Baseline Tier3 MAE`, unit=`MW`
- `mae_weather_tier4`: label=`Weather Tier4 MAE`, unit=`MW`
- `mae_delta_pct`: label=`MAE Delta`, unit=`%`

若为最小改动，可不扩展 schema，而是在 `metrics` 中使用可展示字符串 key：`Baseline Tier3 MAE (MW)`。优先方案仍为 schema 增加 `metrics_meta`。

### D-002@v1: fallback 接受 degraded 但必须显式标注

`build_forecast_fallback` 当前只接受 `detail.status == "ok"`。本变更允许：

- `ok`: 正常 fallback。
- `degraded`: 仍可 fallback，但 `note` 必须包含“离线报告标记为 degraded，指标可能不完整”。

其他状态继续不 fallback，避免把 `missing/error` 当事实来源。

### D-003@v1: Agent 拒绝真实今天预测

`_SYSTEM_PROMPT` 新增时间口径约束：

- 山东 15min 数据是历史数据，不代表真实今天。
- 用户说“今天/当前/实时”时，必须说明无法提供真实今天负荷预测。
- 可建议改问“数据集最新可用日”或指定历史日期。

### D-004@v1: WebUI 只做指标展示契约最小改动

前端 `renderMetrics` 读取 `metrics_meta` 时展示 label + unit；没有 meta 时保留原渲染。fallback 卡片增加 degraded/source note，不重做布局。

## 影响文件（摘要）

| 文件 | 影响 |
|---|---|
| `ellectric/service/schemas.py` | 可选新增 `metrics_meta` 字段到 `ReportSummary` / `ReportDetail`。 |
| `ellectric/service/catalog.py` | 修 `_weather_tier4_summary` 指标映射、status 传递、meta 输出。 |
| `ellectric/service/handlers.py` | 修 `build_forecast_fallback` 接受 degraded 并增强 note。 |
| `ellectric/llm/agent.py` | 增加 today guard prompt。 |
| `ellectric/api/static/index.html` | `renderMetrics` 使用 label/unit；fallback card 标记 degraded。 |
| `tests/test_service_catalog.py` | 覆盖指标映射和 degraded fallback。 |
| `tests/test_chat_streaming_events.py` | 如 payload 示例需更新，则同步断言。 |
| `tests/test_api_catalog.py` | 必要时覆盖 `metrics_meta` API 输出。 |

## 边界

- 不触碰模型训练流程。
- 不改变 `/predict` 请求/响应 schema。
- 不改变报告文件格式，只在 catalog summary 层做事实提取与展示映射。

## 验证策略

- Unit: `tests/test_service_catalog.py`
- API smoke: `tests/test_api_catalog.py`
- SSE/UI payload contract: `tests/test_chat_streaming_events.py`
- Static prompt check: 断言 `_SYSTEM_PROMPT` 包含“今天/数据集最新可用日/不编造实时预测”等关键词。
