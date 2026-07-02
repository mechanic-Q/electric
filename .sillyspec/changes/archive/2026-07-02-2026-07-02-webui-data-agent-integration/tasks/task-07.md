---
id: task-07
title: "扩展 LLM tools 并实现离线报告 fallback（覆盖：FR-04, FR-05, D-002@v1, D-003@v1, D-004@v1, D-005@v1）"
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-03, task-04]
blocks: [task-08, task-09, task-13]
requirement_ids: [FR-04, FR-05]
decision_ids: [D-002@v1, D-003@v1, D-004@v1, D-005@v1]
allowed_paths: [ellectric/llm/tools.py]
---

# task-07: 扩展 LLM tools 并实现离线报告 fallback

## goal

在 `ellectric/llm/tools.py` 新增 catalog/report 查询工具，并让现有 `query_forecast` 在模型缺失时 fallback 到最近离线报告，明确标注数据来源。

## implementation

1. 新增 `@tool query_capabilities()`：调用 `/capabilities`，返回结构化 JSON 文本。
2. 新增 `@tool query_datasets()`：调用 `/datasets`。
3. 新增 `@tool query_reports(report_type: str | None = None)`：调用 `/reports?report_type=...`。
4. 新增 `@tool read_report(report_id: str)`：调用 `/reports/{report_id:path}`。
5. 修改 `query_forecast`：当 HTTP 500/404 且 message 提示模型/文件缺失时，转调 `handlers.build_forecast_fallback` 或 `read_report`，返回带 `status=fallback`、`source=offline_report`、`fallback_reason` 的 JSON 文本；无匹配报告时返回 `status=error` 与建议 `/capabilities` 的提示。
6. 保留其他工具（`run_simulation`、`run_backtest`、`recommend_trade`）行为不变。

## acceptance

- [ ] 四个新 tools 在 `create_agent_executor` 注册后可被 agent 调用。
- [ ] 实时 API 正常时 `query_forecast` 返回原实时响应。
- [ ] 实时 API 返回 500 且信息含 `model` 缺失关键字时，`query_forecast` 返回 fallback JSON，含 `status`, `source`, `fallback_reason`, `summary`。
- [ ] 报告不可用时 `query_forecast` 返回 `status=error` 与建议 `/capabilities`。
- [ ] 无网络时（HTTP 客户端超时/连接错误）不修改已有错误提示格式。

## verify

```bash
python -m pytest tests/test_service_catalog.py tests/test_api_catalog.py -q
```

## constraints

- 工具签名保持向后兼容，不改现有工具名。
- 所有 fallback 输出必须明确标注 `source=offline_report`，不得伪装成实时数据。
- 不引入新的 pydantic 依赖或 LLM SDK；沿用 `httpx.Client`。
- 不注册需要 DEEPSEEK_API_KEY 才能测试的分支。
