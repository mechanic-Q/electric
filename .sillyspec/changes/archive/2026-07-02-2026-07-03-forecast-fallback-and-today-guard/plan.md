---
author: lmr
created_at: 2026-07-03 01:16:03
plan_level: full
---

# Plan: Forecast Fallback Metrics + Today Guard

## 来源

用户确认：先做 A（fallback 层修 bug），接受 C（Agent today guard），不做 B（训练实时模型）。指标命名采用推荐方案：语义化 key + unit/label 元信息。

## 范围

| 文件 | 范围 |
|---|---|
| `ellectric/service/schemas.py` | 新增可选 `metrics_meta` 字段。 |
| `ellectric/service/catalog.py` | 修 Weather Tier4 summary 指标/status/meta。 |
| `ellectric/service/handlers.py` | 修 fallback 对 degraded 的处理。 |
| `ellectric/llm/agent.py` | 增加 today guard prompt。 |
| `ellectric/api/static/index.html` | metrics label/unit + degraded note。 |
| `tests/test_service_catalog.py` | service/fallback 测试。 |
| `tests/test_api_catalog.py` | API schema 输出测试。 |
| `tests/test_chat_streaming_events.py` | SSE payload 测试更新。 |
| `tests/test_agent_prompt.py` | 可新增 prompt 静态测试。 |

## Wave 1: Contract + Catalog Facts

- [x] task-01: 扩展报告指标元信息 schema
  - 修改 `ReportSummary` / `ReportDetail`，新增可选 `metrics_meta: dict[str, dict[str, str]] = {}`。
  - 保持 `metrics` 类型为 scalar dict，不把单位塞进 value。

- [x] task-02: 修正 Weather Tier4 summary 指标映射
  - 从 `experiments.baseline_tier3.metrics.mae` 输出 `mae_baseline_tier3`。
  - 从 `experiments.weather_tier4.metrics.mae` 输出 `mae_weather_tier4`。
  - 从 `experiments.delta.mae_delta_pct` 输出 `mae_delta_pct`。
  - 输出 `metrics_meta` label/unit。
  - 保留报告原始 status；若原始 status 是 `degraded`，summary 中说明降级原因。

## Wave 2: Fallback + Prompt Guard

- [x] task-03: 修正 forecast fallback degraded 处理
  - `build_forecast_fallback` 允许 `detail.status in {"ok", "degraded"}`。
  - payload 增加 `report_status`。
  - degraded 时 note 明确"离线报告降级，指标可能不完整"。

- [x] task-04: 增加 Agent today guard prompt
  - `_SYSTEM_PROMPT` 增加历史数据范围和"今天/实时"拒绝编造规则。
  - 当用户未给日期时，要求澄清或使用"数据集最新可用日"措辞。

## Wave 3: UI Rendering

- [x] task-05: 更新 WebUI metrics label/unit 渲染
  - `renderMetrics(metrics, metricsMeta)` 支持 meta label/unit。
  - `renderResultCard` 传入 `data.metrics_meta`。
  - fallback status/source note 显示 `report_status`，degraded 用 amber 文案。

## Wave 4: Tests + Verification

- [x] task-06: 更新服务层与 API 测试
  - `test_get_report_reads_content_when_available` 断言 semantic metrics keys。
  - `test_build_forecast_fallback_returns_dict_for_model_missing` 断言 `report_status` 与 `metrics_meta`。
  - API report detail 测试允许并检查 `metrics_meta` 字段存在。

- [x] task-07: 更新 SSE payload 与 prompt 契约测试
  - 更新 fake payload 包含 `metrics_meta` / `report_status`。
  - 新增 prompt static test，断言 today guard 关键词。

- [x] task-08: targeted verification
  - 运行 targeted pytest。
  - 运行 compileall。

## 风险

- 当前 Weather Tier4 报告可能真实状态为 degraded；fallback 可用但必须提示质量限制。
- 若后续训练实时模型，本变更仍保留 prompt guard，因为数据源仍不是实时今天。

## 不做

- 不训练模型。
- 不新增实时数据源。
- 不改 `/predict` schema。

## 验收

- `list_reports(report_type="weather_tier4")` 返回语义化 metrics keys 与 `metrics_meta`。
- `get_report("weather_tier4/validation")` 保留报告 status，并包含同样的 metrics/meta。
- `build_forecast_fallback("load", FileNotFoundError(...))` 对 degraded report 返回 fallback，payload 包含 `report_status`。
- Agent prompt 包含 today guard，不允许把历史数据说成真实今天。
- WebUI `renderMetrics` 支持 meta label/unit；没有 meta 时兼容旧 payload。
- targeted pytest 与 compileall 通过。

## 覆盖矩阵

### Requirement Coverage

| Requirement | 覆盖任务 | 验收证据 |
|---|---|---|
| FR-01 | task-01, task-02, task-06, task-08 | semantic metrics + metrics_meta tests |
| FR-02 | task-02, task-03, task-06, task-08 | degraded fallback tests |
| FR-03 | task-04, task-07, task-08 | today guard prompt static test |
| FR-04 | task-01, task-05, task-06, task-07, task-08 | WebUI/SSE metrics_meta contract |
| FR-05 | task-03, task-04, task-08 | no model training/schema change and fallback wording checks |

### Decision Coverage

| Decision | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-02, task-06 | service/API tests assert semantic keys + meta |
| D-002@v1 | task-02, task-03, task-06 | fallback tests assert ok/degraded handling |
| D-003@v1 | task-04, task-07 | prompt static test asserts today guard |
| D-004@v1 | task-05, task-07 | SSE/UI contract tests assert metrics_meta payload |
