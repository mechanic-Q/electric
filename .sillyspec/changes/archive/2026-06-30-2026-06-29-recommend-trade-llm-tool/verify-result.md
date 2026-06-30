---
author: lmr
created_at: 2026-06-30 23:48:00
---

# 验证报告

## 结论

PASS WITH NOTES

本变更完成了 `/recommend` API、CLI、LangChain tool、service schema/handler、单元测试与文档产物。核心接口可导入、CLI 可运行、FastAPI contract 与 LLM tool HTTP contract 均通过。

保留 3 个需要后续修正/复核的非阻断风险：

1. **Backtest evidence 实际不可用风险**：`run_recommend_trade()` 使用 `start_date=end_date=req.date` 构造 `BacktestRequest`，但 `run_backtest()` 要求 `start_date < end_date`，因此真实 backtest evidence 会降级为 unavailable。
2. **Price signal 语义风险**：proposal/design 提到负荷/电价预测与 price signal，但 handler 当前只调用 `ForecastRequest(model_type="load")`，并将 load forecast prediction 用作 `price_limit`。
3. **market 参数未下传风险**：`RecommendRequest.market` 被 schema/CLI 接收，但 handler 未传给 `ForecastRequest.data_source` / `BacktestRequest.data_source`。

这些风险不影响当前低置信降级路径、免责声明、API schema、CLI smoke 与 contract 测试，但建议在后续 quick/fix 中修正。

## 任务完成度

| Task | 验收结果 | Evidence | 状态 |
|---|---|---|---|
| task-01 schema | `TradeAction`, `RecommendRequest`, `RecommendResponse` 存在；字段与 Literal/Noneable 约束符合 | `ellectric/service/schemas.py:282` | PASS |
| task-02 service handler | `run_recommend_trade()` 存在；缺 evidence 降级；low confidence hold；disclaimer 存在 | `ellectric/service/handlers.py:501` | PASS WITH NOTES |
| task-03 tests | recommend schema/handler 测试存在 | `tests/test_recommend_handler.py` | PASS |
| task-04 FastAPI | `POST /recommend` 存在，response model 为 `RecommendResponse` | `ellectric/api/server.py:185` | PASS |
| task-05 CLI | `recommend` Typer command 存在，CLI smoke 可运行 | `ellectric/cli/main.py:310` | PASS |
| task-06 LLM tool | `recommend_trade` tool 存在并注册到 agent tool list | `ellectric/llm/tools.py:146`, `ellectric/llm/agent.py:68` | PASS |
| task-07 docs/sample | module card + sample output 存在；含 disclaimer 与 MANUAL_NOTES | `docs/Ellectric/modules/recommend.md`, `ellectric/reports/recommend/sample_output.md` | PASS |

完成率：7/7。

## 设计一致性

| 设计项 | 结果 | 说明 |
|---|---|---|
| `/recommend` API | PASS | `POST /recommend` 已注册 |
| CLI `recommend` | PASS | `python -m ellectric.cli.main recommend ...` 可运行 |
| LangChain `recommend_trade` | PASS | tool 调用 `/recommend`，agent 已注册 |
| 双层输出：结构化动作 + 中文总结 | PASS | `RecommendResponse.summary/actions` |
| LLM 只转述，不计算核心数值 | PASS | tool docstring 明确限制 |
| low confidence 保守输出 | PASS | low 时返回 hold |
| 学习用途免责声明 | PASS | response/CLI/sample 均含 disclaimer |
| forecast/backtest/explain evidence 聚合 | PASS WITH NOTES | backtest 真实路径因日期范围问题会 unavailable；price signal 语义需修正 |
| `market` 参数 | PASS WITH NOTES | schema/CLI 有，handler 未下传 |

## 探针结果

- 未实现标记扫描：PASS，变更源码文件中 `TODO|FIXME|HACK|XXX` 匹配 0。
- 关键词覆盖：PASS，`recommend`, `/recommend`, `run_recommend_trade`, `recommend_trade`, `confidence`, `disclaimer`, `buy/sell/hold`, `forecast/backtest/explain` 均有源码命中。
- 测试覆盖：PASS，`tests/test_recommend_handler.py` 存在。
- 决策追踪覆盖：PASS WITH NOTES，D-001~D-004 均在 plan/tasks 覆盖；requirements 未直接列 D 编号但 FR 映射存在。
- API Contract Parity：PASS，endpoint artifact 为 `POST /recommend`；无 frontend 目录；FastAPI TestClient contract probe 通过；LLM tool HTTP payload probe 通过。

## 决策追踪矩阵

| 决策 ID | FR | Task | Evidence | 状态 |
|---|---|---|---|---|
| D-001@v1 | FR-01, FR-02, FR-05 | task-01, task-02, task-04, task-05, task-07 | schemas + API/CLI/docs | PASS |
| D-002@v1 | FR-03 | task-01, task-03 | `TradeAction` schema + validation tests | PASS |
| D-003@v1 | FR-04, FR-05 | task-02, task-06 | service handler + LLM tool docstring/registration | PASS |
| D-004@v1 | FR-06, FR-07 | task-02, task-03, task-07 | low confidence hold + disclaimer tests/docs | PASS |

## 测试结果

- Targeted unit tests: `rtk pytest tests/test_recommend_handler.py -v --no-header` → **22 passed**.
- CLI smoke: `python -m ellectric.cli.main recommend 2026-01-15 --horizon 24 --json` → **success**, returns low-confidence hold + disclaimer when local model files are missing.
- Import smoke: schemas/handler/API/tool imports → **success**.
- Contract probe 1: FastAPI `TestClient(app).post('/recommend', ...)` with patched handler → **HTTP 200**, schema keys `actions/confidence/disclaimer/evidence/summary` present.
- Contract probe 2: `recommend_trade.invoke(...)` with fake HTTP client → **POST http://localhost:8000/recommend**, payload includes `date`, `horizon_hours`, `risk_preference`, `max_actions`; result contains `confidence` + `disclaimer`.
- Lint: not run; `.sillyspec/local.yaml` has no lint command.

## 技术债务

变更源码文件 TODO/FIXME/HACK/XXX：0。

## 变更风险等级

change_risk_profile: **contract-required**

原因：本变更涉及 API endpoint、Pydantic DTO/schema、CLI client-like surface、LangChain tool HTTP contract。已补充 contract probes。

## Runtime Evidence

本变更不是 daemon/backend 跨进程或 deployment-critical，Runtime Evidence 非必填。

Contract evidence:

- FastAPI contract: `POST /recommend` via TestClient → 200.
- LLM tool contract: `recommend_trade` posts to `http://localhost:8000/recommend` with expected JSON payload.
- CLI runtime smoke: `python -m ellectric.cli.main recommend 2026-01-15 --horizon 24 --json` returns valid JSON response and disclaimer.

## 代码审查

### Findings

| Severity | Finding | Evidence | Suggested fix |
|---|---|---|---|
| Medium | Real backtest evidence will always be unavailable because `start_date=end_date=req.date` conflicts with `run_backtest()` date validation. | `ellectric/service/handlers.py:523-528`, `run_backtest()` requires start < end | Use a short historical window, e.g. `req.date - 1 day` to `req.date`, or make recommend use a separate summary path. |
| Medium | `price_limit` is derived from load forecast values, not price forecast. | `ForecastRequest(model_type="load")` at `ellectric/service/handlers.py:510`; action `price_limit=predictions[...]` | Call `run_forecast(ForecastRequest(model_type="price"))` for price signal or rename field semantics in design. |
| Low | `market` request parameter is accepted but not passed into downstream requests. | `RecommendRequest.market` schema/CLI, no handler use | Pass `data_source=req.market` into forecast/backtest/explain requests where supported. |
| Low | Tests mock handler dependencies and do not assert `recommend_trade` HTTP path directly. | `tests/test_recommend_handler.py` | Add a small unit test for `recommend_trade` with fake `_CLIENT`. Contract probe passed manually in verify. |

### Overall

Implementation meets core MVP acceptance and contract checks. Remaining issues are semantic/integration quality risks, not schema/API breakages. Recommend follow-up fix before archive if strict design fidelity is required.
