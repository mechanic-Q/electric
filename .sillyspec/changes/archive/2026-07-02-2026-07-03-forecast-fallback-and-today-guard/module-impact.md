---
author: lmr
created_at: 2026-07-03 01:26:26
---

# Module Impact

## 模块映射

_module-map.yaml 不存在，无法自动匹配模块。所有文件归入 unmapped。

## 变更文件

| 文件 | 类型 | 摘要 |
|---|---|---|
| `ellectric/service/schemas.py` | 数据结构变更 | `ReportSummary` 新增 `metrics_meta` 可选字段 |
| `ellectric/service/catalog.py` | 逻辑变更 | `_weather_tier4_summary` 语义键名 + status 透传 + `metrics_meta` 输出；`get_report` 透传 `metrics_meta` |
| `ellectric/service/handlers.py` | 逻辑变更 | `build_forecast_fallback` 接受 ok/degraded 状态，新增 `report_status`/`metrics_meta` |
| `ellectric/llm/agent.py` | 调用关系变更 | `_SYSTEM_PROMPT` 增加 today guard 时间口径规则 |
| `ellectric/api/static/index.html` | 接口变更 | `renderMetrics` 支持 `metricsMeta`，`renderResultCard` 显示 degraded 提示 |
| `tests/test_service_catalog.py` | 新增 | 语义键名断言、degraded 测试、fallback `report_status`/`metrics_meta` 断言 |
| `tests/test_chat_streaming_events.py` | 接口变更 | SSE payload 增加 `metrics_meta`/`report_status` 字段 |
| `tests/test_agent_prompt.py` | 新增 | 静态断言 today guard prompt 关键词 |

## 影响分析

- 不改变 `/predict`/`/simulate`/`/backtest`/`/recommend` 路由 schema
- 不改变数据库或外部依赖
- 内部 catalog 与 handler 接口兼容（新增字段可选）
- API `/reports` 和 `/reports/{id}` 输出新增 `metrics_meta` 可选字段
- SSE tool_result payload 新增 `metrics_meta`/`report_status` 可选字段
