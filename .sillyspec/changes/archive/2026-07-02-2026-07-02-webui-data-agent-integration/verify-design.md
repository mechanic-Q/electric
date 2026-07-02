---
author: lmr
created_at: 2026-07-02 20:47:00
---

# Verify — Step 4 对照设计检查（revision 2）

## 自动探针

### 探针 1：未实现标记扫描

`rg "尚未实现|TODO|FIXME|HACK|XXX" ellectric tests`：无命中。

### 探针 2：设计关键词覆盖

| 关键词/契约 | 证据 | 结果 |
|---|---|---|
| capabilities API | `api/server.py` L204，`tools.py` `query_capabilities`，`index.html` fetch `/capabilities` | ✅ |
| datasets API | `api/server.py` L210，`tools.py` `query_datasets`，`index.html` fetch `/datasets` | ✅ |
| reports API | `api/server.py` L216/L222，`tools.py` `query_reports/read_report`，`index.html` fetch `/reports` | ✅ |
| offline fallback | `handlers.py` `build_forecast_fallback`，`tools.py` `_local_forecast_fallback`，README `source=offline_report` | ✅ |
| SSE payload | `streaming.py` `payload = json.loads(content)` + `payload: payload`，测试覆盖 | ✅ |
| WebUI 数据面板 | `index.html` `.shell` / `.chat` / `.data` + `renderResultCard` + `loadDataPanel` | ✅ |
| 来源标注 | `agent.py` prompt 要求来源；`index.html` source-note；README 说明 | ✅ |

### 探针 3：测试覆盖

| Task | 测试 |
|---|---|
| catalog service/API | `tests/test_service_catalog.py`、`tests/test_api_catalog.py` |
| SSE 字段协议 | `tests/test_chat_streaming_events.py` |
| WebUI catalog contract | `tests/test_api_catalog.py` + 静态 grep 检查前端调用路径 |
| README | 静态文档检查 |

### 探针 4：决策追踪覆盖

requirements.md 覆盖 D-001@v1 至 D-005@v1；plan/tasks 映射 FR/D；实现证据能回指。

## 设计一致性检查

| Decision | 设计要求 | 实现证据 | 结果 |
|---|---|---|---|
| D-001@v1 | 对话内嵌摘要卡片 + 右侧数据面板；tool_result 可解析 UI payload | `streaming.py` payload；`index.html` `renderResultCard` + `.data` 面板 | ✅ |
| D-002@v1 | 能力清单 + AI 引导双通道 | `/capabilities` API；`query_capabilities` tool；前端 welcome chips 来自 capabilities | ✅ |
| D-003@v1 | 模型缺失 fallback 到离线报告 | `build_forecast_fallback` + `query_forecast` HTTP 500 fallback + prompt/source-note | ✅ |
| D-004@v1 | 接通全部已有项目能力 | capabilities 覆盖负荷/电价/风光/仿真/回测/SHAP/交易/报告/数据集；agent 注册 catalog/report tools | ✅ |
| D-005@v1 | 方案 B：保留 HTML/FastAPI，新增 registry + LLM tools + 右侧面板 | 未引入新前端框架；新增 registry/API/tool/UI 面板 | ✅ |

## Contract 对账

- 后端端点：`GET /capabilities`、`GET /datasets`、`GET /reports`、`GET /reports/{report_id:path}` 均存在。
- 前端调用：`index.html` 启动时 fetch `/capabilities`、`/datasets`、`/reports`。
- Agent 调用：`query_capabilities`、`query_datasets`、`query_reports`、`read_report` 均注册。

**对账结果：PASS，无 missing backend endpoint。**

## 结论

设计一致性检查通过。进入 Step 5 任务蓝图验收。
