---
author: lmr
created_at: 2026-06-07 23:46:10
---

# Proposal: Phase 4 — Integration + LLM Interface

## 动机

Phases 1-3 已实现数据管道、负荷/电价预测、市场仿真、RL 交易智能体、回测、模型可解释性的完整技术闭环。但所有能力散落在 Jupyter Notebook 和独立脚本中，没有一个统一的对外接口。学习者不能通过终端命令或 API 调用直接使用这些功能。

Phase 4 的目标：用最小增量把已有能力包装为 **REST API、CLI 命令行工具、自然语言交易助手**，让平台从"内部管道"升级为"可对外交互的系统"。

## 关键问题

1. **入口碎片化**：负荷预测在 notebook 04，电价预测在 notebook 07，仿真要手动跑 `run_simulation.py`，回测在 notebook 11。学习者需要在 3 个不同界面之间切换。
2. **不可编程调用**：无法通过 HTTP 请求获取预测结果，无法从脚本或下游工具调用仿真/回测。
3. **没有自然语言入口**：学习者想查"昨天峰值负荷"必须先定位 notebook、找到对应 cell、修改参数、重新运行——学习曲线陡峭。

## 变更范围

- 新增 `ellectric/service/` — 共享业务逻辑层 (Pydantic schemas + handler 函数)
- 新增 `ellectric/api/` — FastAPI REST API (4 endpoints)
- 新增 `ellectric/cli/` — typer 命令行工具 (5 commands)
- 新增 `ellectric/llm/` — LangChain + DeepSeek API 自然语言助手 (3 tools + chat)
- 新增 `ellectric/requirements-phase4.txt` — Phase 4 依赖声明

## 不在范围内（显式清单）

- 不做 Web UI 前端
- 不做用户认证 / 权限管理
- 不做实时数据流推送 (WebSocket)
- 不做生产级部署配置 (systemd/Docker)
- 不做 MLflow 实验追踪集成
- 不修改任何 Phase 1-3 已有代码

## 成功标准（可验证）

1. FastAPI 服务启动后 `POST /predict` 返回有效 JSON 预测结果和 MAE/RMSE/MAPE
2. `el-cli forecast load 24` 终端输出预测值表格
3. `el-cli simulate summer_peak --days 7` 返回出清价格和代理利润
4. `el-cli backtest 2022-08-01 2022-08-31 ppo` 输出累计 P&L 和策略对比
5. `el-cli ask "昨天峰值负荷多少？"` 返回自然语言回答，内容来自实时预测 API
6. pipeline 层 14 个模块文件无任何修改，Phase 1-3 功能完全保留
