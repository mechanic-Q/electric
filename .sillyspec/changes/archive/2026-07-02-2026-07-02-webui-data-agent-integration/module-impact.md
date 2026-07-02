---
author: lmr
created_at: 2026-07-02 21:04:00
---

# Module Impact — WebUI Data Agent Integration

> `.sillyspec/docs/Electric/modules/_module-map.yaml` 不存在，无法按模块映射表自动归类。建议后续运行 `sillyspec scan` 生成模块映射。本文件按路径前缀临时分组，所有条目均归入未映射/人工模块名。

## 输入来源

- 声明范围：proposal.md / design.md / tasks.md / plan.md
- 任务范围：task-01 ~ task-13 allowed_paths
- 真实变更：`git diff --name-only HEAD` + untracked status

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| API service | 接口变更 | `ellectric/api/server.py` | 新增 `/capabilities`、`/datasets`、`/reports`、`/reports/{report_id:path}` 只读端点；保留 legacy routes | false |
| Service schemas | 数据结构变更 | `ellectric/service/schemas.py` | 新增能力、数据集、报告 summary/detail 的 Pydantic schema | false |
| Service handlers/catalog | 逻辑变更 / 新增 | `ellectric/service/catalog.py`, `ellectric/service/handlers.py` | 新增 catalog registry、report reader、forecast offline fallback helper | false |
| LLM agent/tools | 调用关系变更 / 逻辑变更 | `ellectric/llm/tools.py`, `ellectric/llm/agent.py` | 新增 catalog/report LangChain tools；Agent 注册新工具；prompt 增加来源标注和 fallback 约束 | false |
| Chat SSE | 接口变更 | `ellectric/chat/streaming.py` | `tool_result` 增加 `payload` 字段，兼容结构化前端渲染 | false |
| Web Chat UI | 逻辑变更 / UI 变更 | `ellectric/api/static/index.html` | 单页 HTML 改为 chat + data panel；fetch catalog endpoints；渲染结构化 result cards | false |
| Tests | 新增 / 回归 | `tests/test_service_catalog.py`, `tests/test_api_catalog.py`, `tests/test_chat_streaming_events.py` | 覆盖 catalog service/API 与 SSE payload protocol | false |
| Documentation | 文档更新 | `README.md` | 增加 Web Chat 数据面板、catalog endpoints、offline_report fallback 说明 | false |

## 未匹配文件

| 文件 | 原因 | 处理 |
|------|------|------|
| `.sillyspec/changes/2026-07-02-webui-data-agent-integration/**` | 变更规范/验证/任务文档，无模块映射 | 随变更归档 |
| `.sillyspec/.runtime/execute-runs/**/review.json` | execute review gate 产物，无模块映射 | 保留运行时证据 |
| `.sillyspec/changes/archive/2026-07-01-2026-07-01-shandong-rl-evaluation/**` | 旧变更归档残留在当前 dirty diff 中，非本变更新增功能 | 不作为本变更影响模块 |
| `ellectric/pipeline/rl_evaluation.py` | 旧变更残留在当前 dirty diff 中，非本次 WebUI/catalog 任务路径 | needs_review=true（非本变更） |
| `ellectric/reports/weather_tier4/**` | 旧 Weather Tier4 报告残留在 dirty diff 中，非本次任务路径 | needs_review=true（非本变更） |
| `.serena/project.yml` | 工具配置变更，非产品模块 | needs_review=true（工具状态） |
| `.cocoindex_code/**` | 索引数据库变更，非源码；应保持未纳入归档提交 | needs_review=true（工具缓存） |
| `ellectric/data/external/**`, `ellectric/reports/full_real_run/**`, `ellectric/reports/renewable_forecaster/**` | 当前工作区未跟踪数据/报告，非本变更代码路径 | needs_review=true（数据资产） |

## 更新结果

| 目标 | 状态 | 说明 |
|------|------|------|
| `.sillyspec/docs/Electric/modules/_module-map.yaml` | skipped | 文件不存在，无法同步结构化模块索引 |
| `.sillyspec/docs/Electric/modules/<module>.md` | skipped | 模块卡片目录不存在，无法按模块卡片同步 |

## 风险与后续

- 模块映射缺失：建议下一轮运行 scan 生成 `.sillyspec/docs/Electric/modules/_module-map.yaml`。
- 工作区已有多项历史 dirty/untracked 文件，归档或提交前需人工筛选 staged files，避免把工具缓存或非本变更数据资产混入。
- 本变更核心路径已由 targeted pytest 21 passed、回归 35/56 passed、compileall passed 验证。
