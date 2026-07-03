---
author: lmr
created_at: 2026-07-03 17:01:37
---

# Decisions — WebUI Value Redesign

## D-001@v1: Dashboard-first 是页面主定位
- type: architecture
- status: accepted
- source: user
- question: WebUI 应该继续以 Chat 为中心，还是改成项目价值驾驶舱？
- answer: 采用 Dashboard-first 实施方案。首页展示山东 15min 数据、预测、策略评估、解释性和报告溯源，Chat 作为右侧 Copilot。
- normalized_requirement: 首屏必须让用户看到“山东真实数据 → 预测 → 回测/RL 策略评估 → 解释 → 报告溯源”的端到端技术闭环。
- impacts: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006]
- evidence: 用户回答“Dashboard-first 实施方案”；前序专家判断结论。
- priority: P0

## D-002@v2: 允许框架化前端重构
- type: architecture
- status: accepted
- source: user
- supersedes: D-002@v1
- question: 是否继续保留单文件静态 HTML，还是引入前端框架？
- answer: 用户选择方案 C：前端框架化重构。新增 `ellectric/web/`，采用 Vite + React + TypeScript，构建产物输出到 `ellectric/api/static/`。
- normalized_requirement: 本变更可以新增 Node/Vite/React/TypeScript 前端构建链路，但 FastAPI 既有 REST/SSE API 语义必须保持兼容。
- impacts: [FR-007, FR-008, FR-009, FR-010]
- evidence: 用户回答“方案c”；仓库当前无 `package.json`、`vite.config.*`、`tsconfig*.json`。
- priority: P0

## D-003@v1: 交易能力只展示为学习用策略评估
- type: boundary
- status: accepted
- source: user+docs
- question: WebUI 是否展示自动交易、真实下单、准实时调度或收益承诺？
- answer: 不展示。页面使用“策略评估 / 回测 / 假设分析 / 非交易建议”口径，不使用真实交易、下单、实盘、收益保证等措辞。
- normalized_requirement: 所有交易相关 UI 文案必须保持学习原型边界，不得暗示真实资金交易能力。
- impacts: [FR-011, FR-012]
- evidence: 项目 ROADMAP 明确排除真实交易和准实时 T+15min 调度；用户确认 Dashboard-first 展示技术闭环。
- priority: P0

## D-004@v1: 指标和回答必须可溯源
- type: compatibility
- status: accepted
- source: docs
- question: Dashboard 和 Copilot 展示的数字如何避免 LLM 编造或用户误读？
- answer: 每个指标卡、报告卡和 Copilot 工具结果必须标注来源：实时 API 或离线报告，并尽量展示 `report_id`、`generated_at`、`fallback_reason`。
- normalized_requirement: UI 不展示无来源指标；缺实时模型时优先展示离线报告 fallback，并明确来源。
- impacts: [FR-004, FR-005, FR-006, FR-013]
- evidence: 归档变更 `2026-07-02-webui-data-agent-integration` 的 catalog/report/fallback 设计与验收。
- priority: P1

## D-005@v1: 后端业务 API 保持兼容
- type: compatibility
- status: accepted
- source: code+user
- question: 前端重构是否允许改变现有 FastAPI 业务端点？
- answer: 不允许改变现有端点语义。`/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend`、`/chat/stream`、`/capabilities`、`/datasets`、`/reports` 继续可用。
- normalized_requirement: 前端重构最多调整静态资源挂载和文档，不破坏既有 API 注册和响应语义。
- impacts: [FR-008, FR-009, FR-014]
- evidence: 用户确认设计方案；现有 `ellectric/api/server.py` 和 tests 中已有 legacy route smoke。
- priority: P0
