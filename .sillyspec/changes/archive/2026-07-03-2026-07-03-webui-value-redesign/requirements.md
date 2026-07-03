---
author: lmr
created_at: 2026-07-03 17:01:37
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 学习者 | 访问 WebUI，想快速理解项目已经跑通哪些电力预测与策略评估能力。 |
| 项目开发者 | 维护 FastAPI、LLM tools、报告目录和前端页面，需要清楚构建与兼容边界。 |
| 演示者 | 向他人展示山东数据、预测、RL 评估、解释性和报告溯源的端到端闭环。 |

## 功能需求

### FR-001: Dashboard-first 首页
覆盖决策：D-001@v1

Given 用户打开 WebUI 根路径
When 页面加载成功
Then 第一屏必须以 Dashboard 为主体，而不是以聊天输入框为主体。

Given 用户没有任何项目背景
When 用户阅读首屏标题、摘要和卡片
Then 用户应能理解这是 AI + 电力交易技术学习平台，不是实盘交易系统。

### FR-002: 山东 15min 数据资产展示
覆盖决策：D-001@v1, D-004@v1

Given `/datasets` 返回山东数据元信息
When Dashboard 渲染数据资产卡
Then 页面展示频率、行数、时间范围、字段或可用性状态。

Given `/datasets` 中山东数据不可用
When Dashboard 渲染数据资产卡
Then 页面展示 unavailable/missing 状态和原因，不阻断其他区域加载。

### FR-003: 端到端价值链展示
覆盖决策：D-001@v1

Given `/capabilities` 和 `/reports` 返回可用内容
When Dashboard 渲染主内容
Then 页面必须展示“公开数据 → 预测 → 回测/RL 策略评估 → 解释 → 报告溯源”的结构化链路。

### FR-004: Forecast Lab 展示预测能力
覆盖决策：D-001@v1, D-004@v1

Given `/capabilities` 包含 `forecast_load`、`forecast_price`、`forecast_wind`、`forecast_solar`
When 用户查看 Forecast Lab
Then 页面展示负荷、电价、风电、光伏预测能力、fallback 能力和对应数据/报告来源。

Given `/reports` 包含 Weather Tier4、价格对比或可再生预测报告
When 页面展示预测指标
Then 指标必须标注报告 ID、生成时间或 source 信息。

### FR-005: Strategy Evaluation 展示策略评估
覆盖决策：D-001@v1, D-003@v1, D-004@v1

Given `/reports` 包含 RL full dataset 或 backtest 相关报告
When 用户查看 Strategy Evaluation
Then 页面展示 baseline、oracle、PPO、SAC、TD3 等策略的评估口径和关键指标来源。

Given 报告缺失或状态为 `missing`、`error`、`degraded`
When 页面渲染 Strategy Evaluation
Then 页面显示对应状态，不展示无来源或伪造的 P&L/Sharpe 数字。

### FR-006: Explainability 与 Reports/Data 溯源
覆盖决策：D-001@v1, D-004@v1

Given `/reports` 和 `/reports/{report_id:path}` 可用
When 用户查看 Explainability 或 Reports/Data 区域
Then 页面展示 SHAP、Weather Tier4、报告摘要、报告路径和可读取状态。

Given 报告详情读取失败
When 用户请求报告详情
Then 页面只在该报告卡显示错误，不影响其他 Dashboard 区域。

### FR-007: 新增框架化前端工程
覆盖决策：D-002@v2

Given 仓库当前没有前端 package
When 实现本变更
Then 新增 `ellectric/web/`，包含 Vite + React + TypeScript 的最小构建配置。

Given 开发者执行前端 build
When 构建成功
Then 产物输出到 `ellectric/api/static/`，包含可由 FastAPI 服务的 `index.html`。

### FR-008: FastAPI 静态页面兼容
覆盖决策：D-002@v2, D-005@v1

Given 前端已构建
When 用户访问 FastAPI `GET /`
Then 返回新 Dashboard 页面。

Given catalog 和 legacy API 路由存在
When FastAPI 注册静态挂载
Then `/capabilities`、`/datasets`、`/reports` 等 API 路由不能被 `StaticFiles` 捕获。

### FR-009: 旧 REST/SSE API 语义兼容
覆盖决策：D-005@v1

Given 前端重构完成
When 测试读取 FastAPI route table
Then `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend`、`/chat/stream`、`/capabilities`、`/datasets`、`/reports`、`/reports/{report_id:path}` 仍注册。

Given 旧 API 请求体和响应 schema 不变
When 旧客户端调用这些端点
Then 后端不因本次前端重构改变语义。

### FR-010: Copilot 迁移 SSE 行为
覆盖决策：D-001@v1, D-002@v2, D-005@v1

Given 用户在 Copilot 输入问题
When 前端调用 `/chat/stream`
Then 前端能处理 `token`、`tool_call`、`tool_result`、`error`、`done` 事件。

Given `tool_result` 内容为 JSON 字符串
When 前端解析事件
Then 以结构化结果卡展示 `source`、`fallback_reason`、`report_status`、`metrics`、`metrics_meta` 等可用字段。

### FR-011: 非交易边界文案
覆盖决策：D-003@v1

Given 用户浏览 Dashboard 或 Copilot
When 页面展示策略、回测或建议相关内容
Then 文案必须使用“策略评估 / 回测 / 假设分析 / 学习原型 / 非交易建议”口径。

Given 页面或示例问题涉及交易动作
When 用户阅读内容
Then 页面不得暗示真实下单、实盘交易或收益保证。

### FR-012: 不新增实盘交易能力
覆盖决策：D-003@v1

Given 本变更完成
When 检查新增前端和后端代码
Then 不存在真实下单、资金账户、交易所连接、准实时调度或收益承诺功能。

### FR-013: 指标来源和降级状态
覆盖决策：D-004@v1

Given Dashboard 展示任何数字指标
When 指标来自 API、离线报告或 fallback
Then UI 必须展示来源状态，支持 `api`、`offline_report`、`fallback`、`missing`、`error`、`degraded` 等口径。

Given API 请求失败
When Dashboard 渲染失败区域
Then 只显示局部错误卡，不阻断全页。

### FR-014: README 说明更新
覆盖决策：D-002@v2, D-005@v1

Given 开发者阅读 README
When 查看 WebUI 启动说明
Then README 说明前端 dev/build 命令、FastAPI 启动方式、构建产物位置和后端 API 兼容边界。

## 非功能需求

- 兼容性：不得改变现有 FastAPI REST/SSE API 语义。
- 可回退：缺报告、缺模型、缺 `DEEPSEEK_API_KEY` 时页面局部降级，不整页崩溃。
- 可测试：至少保留 API route smoke、catalog route order、SSE event parsing、前端构建或静态页面 smoke。
- 可维护：前端源码维护在 `ellectric/web/`，不继续手写大型单文件 `index.html`。
- 依赖克制：只新增 Vite + React + TypeScript 所需最小依赖，不引入 UI 组件库或状态管理库。
- 可访问性：Dashboard 卡片、按钮、输入框需要基本语义标签和移动端可读布局。
- 溯源性：指标、报告、fallback 必须显示 source/report/status 线索。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-010 | Dashboard-first 是页面主定位。 |
| D-002@v2 | FR-007, FR-008, FR-010, FR-014 | 用户选择方案 C，允许新增 Vite + React + TypeScript。 |
| D-003@v1 | FR-005, FR-011, FR-012 | 交易能力只展示为学习用策略评估。 |
| D-004@v1 | FR-002, FR-004, FR-005, FR-006, FR-013 | 指标、报告和 fallback 必须可溯源。 |
| D-005@v1 | FR-008, FR-009, FR-010, FR-014 | 后端业务 API 保持兼容。 |
