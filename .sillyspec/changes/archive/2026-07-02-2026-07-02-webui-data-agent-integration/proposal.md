---
author: lmr
created_at: 2026-07-02 16:55:06
---

# Proposal

## 动机

现有 Web Chat UI 已经能通过 DeepSeek V4 和 LangChain 进行基础对话，但它还不能准确连接项目内已经生成的预测、评估、报告和数据集信息。用户希望通过一个对话式网页直接询问负荷、电价、风光出力、策略评估、交易建议、模型解释等问题，并在网页中看到清晰的数据来源、结构化指标和可问问题说明。

本变更的核心动机是把现有聊天页升级为 Ellectric 学习平台的数据入口：既能自然语言问答，也能展示项目已有事实数据。

## 关键问题

1. **项目事实分散，AI 没有统一目录**
   报告散落在 `ellectric/reports/**`，实时能力散落在 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend`，前端和 Agent 都没有一个稳定的 capabilities/datasets/reports 目录。

2. **工具结果没有进入 UI**
   `streaming.py` 已发送 `tool_result`，但现有 `index.html` 只把工具状态标记为完成，不展示 `tool_result.content`。同时现有前端读取 `event.tool/event.tool_id`，而后端发送的是 `name` 字段，导致工具状态匹配不准。

3. **实时模型缺失时体验断裂**
   如果 `xgboost_model.joblib`、`lear_model.joblib`、`dnn_model.joblib` 等文件缺失，实时预测会失败。但项目已有离线报告可以回答许多问题，当前没有自动 fallback 到离线报告的路径。

## 变更范围

- 新增 reports/datasets/capabilities registry 与只读 API。
- 新增 LLM tools 查询能力清单、数据集元信息和离线报告。
- 为 forecast tool 增加实时失败时的离线报告 fallback。
- 修复 SSE `tool_call`、`tool_result`、`error` 字段协议。
- 改造现有 HTML 单页为左侧对话 + 右侧数据面板。
- 在 AI 气泡内展示结构化工具结果摘要。
- 增加可问问题清单和示例问题。
- 增加 catalog/API/SSE 相关测试。
- 更新 README 中 Web Chat 使用说明。

## 不在范围内（显式清单）

- 不做 React/Vite/Streamlit/Gradio 前端重构。
- 不做登录、权限、多用户。
- 不做聊天记录持久化。
- 不做真实交易下单。
- 不重新训练模型。
- 不重新生成已有报告。
- 不迁移完整 Grafana/Plotly 仪表盘。
- 不把 SSE 改成 WebSocket。
- 不改变现有核心 API 的请求/响应语义。

## 成功标准（可验证）

- `GET /capabilities` 返回可问问题类别、示例问题和相关 endpoint/tool。
- `GET /datasets` 返回山东/OWID/Chinese 等数据源元信息。
- `GET /reports` 返回已有报告清单，缺失报告不导致 500。
- `GET /reports/{report_id:path}` 可读取指定报告详情。
- `query_capabilities`、`query_datasets`、`query_reports`、`read_report` 可被 Agent 注册并调用。
- 实时 forecast 失败且有离线报告时，tool 返回 `status=fallback`、`source=offline_report`、`fallback_reason`。
- `/chat/stream` 的 `tool_call`/`tool_result`/`error` 字段与前端解析一致。
- 前端能显示工具状态、结构化结果卡片和右侧数据面板。
- 页面欢迎区或侧栏明确列出能问的问题。
- 旧 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend` 路由继续可用。
