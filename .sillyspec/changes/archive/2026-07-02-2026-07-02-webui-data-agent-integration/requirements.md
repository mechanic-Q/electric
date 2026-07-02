---
author: lmr
created_at: 2026-07-02 16:55:06
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 学习者/开发者 | 使用 Ellectric WebUI 查询预测、报告、评估结果，理解 AI+电力交易技术闭环 |
| AI 电力交易助手 | 基于 DeepSeek V4 和工具调用回答问题，必须标注数据来源，不编造数字 |
| 系统维护者 | 维护报告目录、API schema、前端数据面板和测试 |

## 功能需求

### FR-01: 能力清单 API

覆盖决策：D-002@v1, D-004@v1, D-005@v1

Given FastAPI 服务启动
When 用户或 Agent 请求 `GET /capabilities`
Then 系统返回可用能力列表，包括预测、仿真、回测、解释、交易建议、报告、数据集，并包含标题、说明、示例问题、endpoint/tool、是否支持离线 fallback。

Given 某些能力依赖的模型或报告缺失
When 用户请求 `GET /capabilities`
Then 系统仍返回能力项，并通过 `available` 或说明字段表达可用性，不导致 500。

### FR-02: 数据集元信息 API

覆盖决策：D-002@v1, D-004@v1, D-005@v1

Given 项目存在山东、OWID 或 Chinese 数据加载能力
When 用户或 Agent 请求 `GET /datasets`
Then 系统返回数据源 ID、标题、说明、来源、频率、行数、时间范围、字段列表和可用状态。

Given 某个数据源读取失败
When 用户请求 `GET /datasets`
Then 系统返回该数据源 `available=false` 或错误摘要，不阻断其他数据源。

### FR-03: 离线报告目录 API

覆盖决策：D-002@v1, D-003@v1, D-004@v1, D-005@v1

Given 项目存在 `ellectric/reports/**` 报告产物
When 用户请求 `GET /reports`
Then 系统返回报告清单，包括 full_real_run、price comparison、Weather Tier4、renewable forecaster、RL full dataset 等可用报告摘要。

Given 用户请求 `GET /reports/{report_id:path}`
When `report_id` 对应报告存在
Then 系统返回报告详情，包括标题、类型、生成时间、摘要、关键指标、项目内相对路径和内容。

Given `report_id` 不存在
When 用户请求 `GET /reports/{report_id:path}`
Then 系统返回明确的 not found 错误，不暴露任意文件路径。

### FR-04: Agent 可查询能力、数据集和报告

覆盖决策：D-002@v1, D-004@v1, D-005@v1

Given DeepSeek Agent 已创建
When 用户询问“能问什么”“有哪些报告”“山东数据包含什么字段”
Then Agent 调用 `query_capabilities`、`query_datasets`、`query_reports` 或 `read_report`，基于工具结果回答。

Given 工具返回结构化 JSON
When Agent 生成回答
Then 回答必须使用工具中的数字，并标注来源为实时 API 或离线报告。

### FR-05: 实时模型缺失 fallback 到离线报告

覆盖决策：D-003@v1, D-005@v1

Given 用户询问负荷、电价或其他预测结果
And 对应实时模型文件缺失或加载失败
When forecast tool 捕获该错误
Then tool 返回结构化 fallback，包含 `status=fallback`、`source=offline_report`、`fallback_reason`、`report_id`、`summary`、`metrics`。

Given 实时模型和离线报告都不可用
When 用户请求预测
Then 系统返回友好错误，并建议查看 `/capabilities` 或可用报告，不编造预测数字。

### FR-06: SSE 工具事件协议一致

覆盖决策：D-001@v1, D-005@v1

Given Agent 调用工具
When `/chat/stream` 输出 SSE
Then `tool_call` 帧包含 `type`、`name`、`args`。

Given 工具调用结束
When `/chat/stream` 输出 SSE
Then `tool_result` 帧包含 `type`、`name`、`content`，如可解析 JSON 则提供或允许前端生成 `payload`。

Given 发生错误
When `/chat/stream` 输出 SSE
Then `error` 帧包含 `message`，前端兼容读取 `message` 或旧 `content`。

### FR-07: 前端结构化结果展示

覆盖决策：D-001@v1, D-002@v1, D-005@v1

Given 前端收到 `tool_result` 事件
When `content` 是 JSON 或可摘要的结构化文本
Then 前端在 AI 气泡内展示摘要卡片、指标表或报告卡片。

Given 前端收到工具结果
When 右侧数据面板存在
Then 前端同步更新数据面板，展示详细指标、报告链接或数据集信息。

Given 前端无法解析 `tool_result.content`
When 工具结果仍有文本
Then 前端显示文本摘要，不丢弃结果。

### FR-08: WebUI 能力清单和示例问题

覆盖决策：D-002@v1, D-004@v1

Given 用户首次打开首页
When 欢迎区和右侧数据面板加载
Then 页面展示可问问题分组：预测、评估、交易、解释、数据。

Given 用户点击示例问题
When 问题发送到 `/chat/stream`
Then 聊天流程与手动输入一致。

### FR-09: 保持既有 API 兼容

覆盖决策：D-005@v1

Given 旧客户端仍调用 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend`
When 本变更完成后
Then 这些路由仍存在，并保持原核心请求/响应语义。

Given 静态页面由 `app.mount("/")` 提供
When 新增 catalog API 路由
Then 新路由必须注册在静态文件挂载之前，避免被 StaticFiles 捕获。

## 非功能需求

- 兼容性：新增端点只读，不改变现有核心 API 行为。
- 可回退：模型缺失、报告缺失、数据源读取失败都必须返回结构化说明或友好错误。
- 可测试：catalog service、API 端点、SSE 字段、前端结果解析均应有测试或 smoke 验证。
- 安全性：报告路径只返回项目内相对路径，不允许任意文件读取。
- 性能：前端只显示摘要，大型 JSON 在右侧面板折叠或截断。
- 可维护性：能力/报告/数据集定义集中在 catalog 层，避免散落在前端硬编码。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-06, FR-07 | SSE 事件和 UI 同时支持气泡内嵌与右侧面板 |
| D-002@v1 | FR-01, FR-02, FR-03, FR-04, FR-08 | 能力清单 + AI 引导双通道 |
| D-003@v1 | FR-03, FR-05 | 模型缺失时 fallback 到离线报告 |
| D-004@v1 | FR-01, FR-02, FR-03, FR-04, FR-08 | 覆盖全部已有项目能力 |
| D-005@v1 | FR-01 至 FR-09 | 采用数据目录与报告层方案 |
