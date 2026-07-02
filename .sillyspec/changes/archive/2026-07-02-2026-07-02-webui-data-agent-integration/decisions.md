---
author: lmr
created_at: 2026-07-02 16:55:06
---

# Decisions: WebUI Data Agent Integration

## D-001@v1: 展示结构采用对话内嵌 + 右侧数据面板

- type: architecture
- status: accepted
- source: user
- priority: P1
- question: 结构化数据在网页中如何呈现？
- answer: AI 消息内嵌摘要卡片/表格，同时右侧面板展示详细数据、报告链接和图表。
- normalized_requirement: tool_result 必须被解析为 UI card payload，并同步加入 data panel。
- impacts: [FR-UI-structured-results, task-frontend-panel, verify-sse-tool-result-render]
- evidence: brainstorm Step 6 用户回答

## D-002@v1: 数据发现采用能力清单 + AI 引导双通道

- type: boundary
- status: accepted
- source: user
- priority: P1
- question: 用户如何知道能问什么、能看什么？
- answer: 页面显式能力清单 + Agent 通过工具主动检索与引导。
- normalized_requirement: 后端提供 capabilities 数据；前端欢迎区/右侧面板展示能力；LLM tool 可查询 capabilities。
- impacts: [FR-capabilities, task-capabilities-api, verify-capabilities-ui]
- evidence: brainstorm Step 6 用户回答

## D-003@v1: 实时模型缺失时 fallback 到离线报告

- type: compatibility
- status: accepted
- source: user
- priority: P1
- question: 模型文件缺失时 UI 如何处理？
- answer: 自动 fallback 到最近离线报告。
- normalized_requirement: Forecast tool 在模型缺失时返回 structured fallback，而非只返回 500 错误；UI 标明数据来源为离线报告。
- impacts: [FR-fallback-reports, task-report-registry, verify-missing-model-fallback]
- evidence: brainstorm Step 6 用户回答

## D-004@v1: 本次范围接通全部已有项目能力

- type: boundary
- status: accepted
- source: user
- priority: P1
- question: 本次接通哪些数据源和能力？
- answer: 负荷/电价预测、风光预测、市场仿真、回测、SHAP、交易建议、离线报告、数据集元信息、能力清单/文档。
- normalized_requirement: WebUI 与 Agent 数据工具覆盖上述能力；不包含登录、多用户、真实交易、完整 React 重构。
- impacts: [FR-scope, task-agent-tools, task-report-api, task-dataset-api]
- evidence: brainstorm Step 6 用户回答

## D-005@v1: 采用方案 B 数据目录与报告层

- type: architecture
- status: accepted
- source: user
- priority: P1
- question: 三种实现方案中选择哪一种？
- answer: 选择方案 B：保留现有 HTML/FastAPI，新增 reports/datasets/capabilities registry + LLM tools + 右侧数据面板。
- normalized_requirement: 不做纯轻量修补，也不做独立前端重构；通过轻量数据目录层解决数据发现、fallback、结构化展示。
- impacts: [design-wave-1, design-wave-2, design-wave-3, design-wave-4, design-wave-5]
- evidence: brainstorm Step 8 用户回答
