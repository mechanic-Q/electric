---
author: lmr
created_at: 2026-07-02 17:55:55
plan_level: full
---

# 实现计划

## Spike 前置验证

无需 Spike。本变更使用项目既有技术栈：FastAPI、Pydantic v2、LangChain tools、SSE、单文件 HTML/JS。关键不确定性已在 Design Grill 中消解：`/reports/{report_id:path}`、StaticFiles 路由顺序、SSE payload 语义、Pydantic default_factory。

## Wave 1（基础契约）

- [ ] task-01: 扩展 service schemas（覆盖：FR-01, FR-02, FR-03, D-002@v1, D-005@v1）
- [ ] task-02: 新增 catalog registry 服务（覆盖：FR-01, FR-02, FR-03, D-002@v1, D-003@v1, D-005@v1）

## Wave 2（Service/API 接入，依赖 Wave 1）

- [ ] task-03: 新增 catalog handlers 与 forecast fallback helper（覆盖：FR-01, FR-02, FR-03, FR-05, D-003@v1, D-005@v1）
- [ ] task-04: 新增 capabilities/datasets/reports API 路由（覆盖：FR-01, FR-02, FR-03, FR-09, D-002@v1, D-005@v1）
- [ ] task-05: 新增 catalog service 测试（覆盖：FR-01, FR-02, FR-03, FR-05, D-002@v1, D-003@v1, D-005@v1）
- [ ] task-06: 新增 catalog API smoke 测试（覆盖：FR-01, FR-02, FR-03, FR-09, D-005@v1）

## Wave 3（Agent/SSE 接入，依赖 Wave 2）

- [ ] task-07: 扩展 LLM tools 并实现离线报告 fallback（覆盖：FR-04, FR-05, D-002@v1, D-003@v1, D-004@v1, D-005@v1）
- [ ] task-08: 更新 Agent prompt 和工具注册（覆盖：FR-04, D-002@v1, D-004@v1, D-005@v1）
- [ ] task-09: 修复 SSE 事件字段协议（覆盖：FR-06, D-001@v1, D-005@v1）
- [ ] task-10: 新增 SSE 事件协议测试（覆盖：FR-06, D-001@v1, D-005@v1）

## Wave 4（WebUI/文档，依赖 Wave 2-3）

- [ ] task-11: 改造 WebUI 为聊天 + 数据面板（覆盖：FR-07, FR-08, D-001@v1, D-002@v1, D-004@v1, D-005@v1）
- [ ] task-12: 更新 README Web Chat 使用说明（覆盖：FR-08, D-002@v1, D-004@v1）

## Wave 5（最终验证，依赖 Wave 1-4）

- [ ] task-13: 运行 targeted verification（覆盖：FR-01 至 FR-09, D-001@v1 至 D-005@v1）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | 扩展 service schemas | W1 | P0 | — | FR-01, FR-02, FR-03, D-002@v1, D-005@v1 | 为 catalog/report/dataset 响应提供契约 |
| task-02 | 新增 catalog registry 服务 | W1 | P0 | task-01 | FR-01, FR-02, FR-03, D-002@v1, D-003@v1, D-005@v1 | 建立能力、数据集、报告事实目录 |
| task-03 | 新增 catalog handlers 与 forecast fallback helper | W2 | P0 | task-01, task-02 | FR-01, FR-02, FR-03, FR-05, D-003@v1, D-005@v1 | 连接 schema/catalog 与 service 层 |
| task-04 | 新增 capabilities/datasets/reports API 路由 | W2 | P0 | task-03 | FR-01, FR-02, FR-03, FR-09, D-002@v1, D-005@v1 | 暴露只读目录端点，保持旧路由 |
| task-05 | 新增 catalog service 测试 | W2 | P0 | task-01, task-02, task-03 | FR-01, FR-02, FR-03, FR-05, D-002@v1, D-003@v1, D-005@v1 | 验证 registry、fallback、缺失报告行为 |
| task-06 | 新增 catalog API smoke 测试 | W2 | P0 | task-04 | FR-01, FR-02, FR-03, FR-09, D-005@v1 | 验证新 API 和 StaticFiles 顺序 |
| task-07 | 扩展 LLM tools 并实现离线报告 fallback | W3 | P0 | task-03, task-04 | FR-04, FR-05, D-002@v1, D-003@v1, D-004@v1, D-005@v1 | 让 Agent 可读取目录和报告 |
| task-08 | 更新 Agent prompt 和工具注册 | W3 | P0 | task-07 | FR-04, D-002@v1, D-004@v1, D-005@v1 | 注册新工具并约束数据来源表达 |
| task-09 | 修复 SSE 事件字段协议 | W3 | P0 | task-07 | FR-06, D-001@v1, D-005@v1 | 统一 tool_call/tool_result/error 字段 |
| task-10 | 新增 SSE 事件协议测试 | W3 | P0 | task-09 | FR-06, D-001@v1, D-005@v1 | 锁定事件字段兼容性 |
| task-11 | 改造 WebUI 为聊天 + 数据面板 | W4 | P0 | task-04, task-09 | FR-07, FR-08, D-001@v1, D-002@v1, D-004@v1, D-005@v1 | 展示能力清单和结构化工具结果 |
| task-12 | 更新 README Web Chat 使用说明 | W4 | P1 | task-11 | FR-08, D-002@v1, D-004@v1 | 文档化可问问题与启动方式 |
| task-13 | 运行 targeted verification | W5 | P0 | task-01-task-12 | FR-01 至 FR-09, D-001@v1 至 D-005@v1 | 执行测试/API/前端 smoke 验证 |

## 关键路径

task-01 → task-02 → task-03 → task-04 → task-07 → task-09 → task-11 → task-13

## 调用点搜索记录

搜索命令：

`/usr/bin/rg -n "run_forecast|ForecastRequest|ForecastResponse|run_simulate|run_backtest|run_explain|run_recommend_trade|create_agent_executor|query_forecast|run_simulation|recommend_trade|tool_call|tool_result|event\.tool|event\.tool_id|app\.mount\(\"/\"" ellectric tests .sillyspec/changes/2026-07-02-webui-data-agent-integration -g '*.py' -g '*.html' -g '*.md'`

关键命中：

- `ellectric/api/server.py`：现有 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend` 和 `app.mount("/")`。
- `ellectric/service/schemas.py`：现有 `ForecastRequest`/`ForecastResponse`。
- `ellectric/service/handlers.py`：现有 forecast/simulate/backtest/explain/recommend handlers。
- `ellectric/llm/tools.py`：现有 query_forecast/run_simulation/run_backtest/recommend_trade tools。
- `ellectric/llm/agent.py`：现有工具注册点。
- `ellectric/chat/streaming.py`：现有 `tool_call`/`tool_result` SSE 输出点。
- `ellectric/api/static/index.html`：现有前端仍读取 `event.tool`/`event.tool_id`。
- `ellectric/cli/main.py`：复用 service handlers，不能破坏旧 request/response。
- `tests/test_recommend_handler.py`、`tests/test_time_resolution_15min.py`：现有 service schema/handler 调用点。

## 全局验收标准

- [ ] `GET /capabilities`、`GET /datasets`、`GET /reports`、`GET /reports/{report_id:path}` 返回预期结构。
- [ ] 缺失报告或数据源读取失败不会导致服务启动失败。
- [ ] 模型缺失时 forecast tool 可返回离线报告 fallback 或友好错误。
- [ ] `/chat/stream` 的 `tool_call`、`tool_result`、`error` 事件字段与前端解析一致。
- [ ] WebUI 首页显示能力清单/示例问题，工具结果在气泡和右侧数据面板可见。
- [ ] 旧 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend` 核心语义不变。
- [ ] 路由注册顺序保证 catalog API 不被 `app.mount("/")` 捕获。
- [ ] 报告路径只暴露项目内相对路径，不允许任意文件读取。
- [ ] targeted pytest 通过：`tests/test_service_catalog.py`、`tests/test_api_catalog.py`、`tests/test_chat_streaming_events.py`，并回归 `tests/test_recommend_handler.py`、`tests/test_time_resolution_15min.py`。
- [ ] 如可用，手动或脚本 smoke 验证 WebUI 能发起一次 `/chat/stream` 请求并渲染工具结果。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-09, task-10, task-11 | SSE 事件测试 + WebUI 工具结果展示 |
| D-002@v1 | task-01, task-02, task-04, task-07, task-08, task-11, task-12 | capabilities API/tool/UI/README |
| D-003@v1 | task-02, task-03, task-05, task-07 | fallback 单测 + tool 输出 source/offline_report |
| D-004@v1 | task-07, task-08, task-11, task-12 | Agent 工具覆盖全部能力 + UI 示例问题 |
| D-005@v1 | task-01 至 task-13 | 数据目录与报告层完整链路 |
| FR-01 | task-01, task-02, task-03, task-04, task-05, task-06 | /capabilities + schema/service tests |
| FR-02 | task-01, task-02, task-03, task-04, task-05, task-06 | /datasets + schema/service tests |
| FR-03 | task-01, task-02, task-03, task-04, task-05, task-06 | /reports + /reports/{id:path} tests |
| FR-04 | task-07, task-08 | Agent tools registered and callable |
| FR-05 | task-03, task-05, task-07 | model-missing fallback test |
| FR-06 | task-09, task-10 | SSE event contract test |
| FR-07 | task-11 | front-end render smoke/manual check |
| FR-08 | task-11, task-12 | UI capability list + README |
| FR-09 | task-04, task-06, task-13 | old routes remain + route-order smoke |

## 自检结果

- [x] 每个 task 有编号（task-01 至 task-13）。
- [x] 每个 task 在 Wave 下有 checkbox。
- [x] 已标注 Wave 分组和依赖关系。
- [x] 有任务总表，含优先级和依赖列，无估时列。
- [x] 有关键路径标注。
- [x] 有全局验收标准。
- [x] 当前版本 D-001@v1 至 D-005@v1 全部覆盖。
- [x] 不存在 P0/P1 unresolved blocker。
- [x] brownfield 兼容性条款已纳入全局验收。
- [x] 不包含接口定义或代码示例等实现细节。
- [x] plan.md 与 design.md 文件变更清单一致。
- [x] 已搜索相关调用点并记录。
- [x] 未生成 Mermaid 图。
- [x] 无泛泛风险分析。
