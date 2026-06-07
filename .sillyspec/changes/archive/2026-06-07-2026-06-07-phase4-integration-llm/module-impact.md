---
author: lmr
created_at: 2026-06-08 01:10:00
---

# 模块影响分析: Phase 4 — Integration + LLM Interface

## 声明范围 vs 实际变更

| 来源 | 文件数 | 一致性 |
|------|--------|--------|
| design.md 文件变更清单 | 13 (12新增+1修改) | ✅ 完全一致 |
| git diff --cached | 13 (12A+1M) | ✅ 完全一致 |
| pipeline 变化 | 0 | ✅ 零改动 |

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|---------|-------------|-------------|
| — | 新增 | `ellectric/service/` (3 文件) | Pydantic schemas + handler 业务逻辑 | false |
| — | 新增 | `ellectric/api/` (2 文件) | FastAPI REST API 4 endpoints | false |
| — | 新增 | `ellectric/cli/` (2 文件) | typer CLI 5 commands | false |
| — | 新增 | `ellectric/llm/` (4 文件) | LangChain agent + tools + chat | false |
| — | 配置新增 | `ellectric/requirements-phase4.txt` | 7 依赖声明 | false |
| forecaster | 调用关系变更 (只读) | `service/handlers.py` | 引入 XGBoostForecaster 做预测 | false |
| price-forecaster | 调用关系变更 (只读) | `service/handlers.py` | 引入 LEARForecaster 做预测 | false |
| backtester | 调用关系变更 (只读) | `service/handlers.py` | 引入 BacktestRunner 做回测 | false |
| shap-explainer | 调用关系变更 (只读) | `service/handlers.py` | 引入 SHAP 解释函数 | false |
| assume-simulation | 调用关系变更 (只读) | `service/handlers.py` | subprocess 调 run_simulation.py | false |

## 现有模块变动详情

所有 pipeline 模块（forecaster, price-forecaster, backtester, shap-explainer, trading-env, rl-trainer, data-loader, cleaner, feature-engineer）**零改动**。仅被 Phase 4 新代码通过 `import` / `subprocess` 调用。

## 未匹配文件

13 个文件均为**新增模块**，不属于任何现有 _module-map.yaml 中的模块。建议在模块索引中注册：
- service (schemas.py, handlers.py)
- api (server.py)
- cli (main.py)
- llm (tools.py, agent.py, chat.py)

## 调用关系

```
forecaster   ← service/handlers.py (run_forecast)
price-forecaster ← service/handlers.py (run_forecast)
backtester   ← service/handlers.py (run_backtest)
shap-explainer  ← service/handlers.py (run_explain)
assume-simulation ← service/handlers.py (run_simulate, subprocess)
```
