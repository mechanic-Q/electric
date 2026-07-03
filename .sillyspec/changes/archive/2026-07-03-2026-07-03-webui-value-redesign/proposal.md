---
author: lmr
created_at: 2026-07-03 17:01:37
---

# Proposal

## 动机

当前 WebUI 已接入 FastAPI 静态页面、SSE Chat、能力目录、数据集目录和报告目录，但主体验仍是 Chat-first。它能回答问题，却不能在第一屏讲清楚本项目最有价值的闭环：山东 15min 真实数据接入、负荷/电价/风光预测、回测与 RL 策略评估、SHAP/Weather 解释、离线报告溯源。

本变更把 WebUI 重构为 Dashboard-first，优先展示可验证事实和端到端能力，Chat 退为右侧 Copilot。用户明确选择方案 C：新增 Vite + React + TypeScript 前端工程，以换取长期可维护的 Dashboard 页面结构。

## 关键问题

1. 现有 Chat-first 页面把项目能力藏在对话后面。访问者必须先知道该问什么，才可能看到山东数据、预测、RL 评估和报告证据。
2. 单文件静态 HTML 已承载能力面板、聊天、结果卡和样式，继续叠加 Dashboard 会让状态管理、SSE 事件和响应式布局难维护。
3. 交易相关措辞需要更明确的边界治理。项目是学习原型，WebUI 必须展示“策略评估/回测/假设分析”，而不是暗示真实交易或收益承诺。

## 变更范围

- 新增 `ellectric/web/` 前端工程，使用 Vite + React + TypeScript。
- 前端构建产物输出到 `ellectric/api/static/`，FastAPI 继续服务 `GET /`。
- 首页改为 Dashboard-first：山东数据资产、端到端价值链、Forecast Lab、Strategy Evaluation、Explainability、Reports/Data。
- Chat 改为右侧 Copilot，复用现有 `/chat/stream` SSE 协议。
- 前端直接复用现有 `/capabilities`、`/datasets`、`/reports`、`/reports/{report_id:path}` 只读端点。
- 保持现有 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend`、`/chat/stream` 语义兼容。
- 更新 README 中 WebUI 开发、构建、启动说明。

## 不在范围内（显式清单）

- 不做真实交易、真实下单、实盘接口或收益承诺。
- 不做准实时 T+15min 调度，不新增 cron、daemon 或 queue。
- 不做模型重训，不重新生成已有离线报告。
- 不做登录、权限、多用户或聊天记录持久化。
- 不新增数据库或后端状态表。
- 不新增 `/dashboard-summary` 聚合端点，除非实现阶段证明现有端点无法满足页面加载。
- 不引入 UI 组件库、全局状态管理库或复杂前端路由。
- 不改变既有 REST/SSE API 响应语义。

## 成功标准（可验证）

- `ellectric/web/` 能执行前端构建，并生成 `ellectric/api/static/index.html`。
- FastAPI `GET /` 能返回新 Dashboard 页面。
- 旧端点仍注册：`/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend`、`/chat/stream`、`/capabilities`、`/datasets`、`/reports`、`/reports/{report_id:path}`。
- Dashboard 第一屏能看出“山东 15min 数据 → 预测 → 策略评估 → 解释 → 报告溯源”闭环。
- Copilot 能继续处理 `/chat/stream` 的 `token`、`tool_call`、`tool_result`、`error`、`done` 事件。
- 报告和指标卡展示来源字段，至少包含 API/report 来源、`report_id` 或 `generated_at` 中的可用信息。
- 页面文案不出现真实交易、实盘下单或收益保证暗示。
- 缺少报告、模型或 `DEEPSEEK_API_KEY` 时，Dashboard 仍可展示可用数据，局部卡片降级。
