---
author: lmr
created_at: 2026-06-07 23:46:10
---

# Requirements: Phase 4 — Integration + LLM Interface

## 角色

| 角色 | 说明 |
|------|------|
| 学习者 | 通过 Jupyter/CLI/API/自然语言使用平台功能 |
| 开发者 | 维护者，需要 CLI 快速验证和执行操作 |

## 功能需求

### FR-01: 负荷/电价预测 API

Given 系统已安装依赖且模型文件存在于 `ellectric/models/`
When 发送 `POST /predict` 请求，body 为 `{"model_type": "load", "horizon": 24, "data_source": "owid"}`
Then 返回 200 状态码，JSON 包含 `timestamps`, `predictions`, `metrics{mae, rmse, mape}`

Given 请求 model_type 为不支持的值 (如 "abc")
When 发送 `POST /predict` 请求
Then 返回 422 状态码，错误信息指明无效值

### FR-02: 市场仿真 API

Given 系统已安装 ASSUME 依赖且配置文件存在于 `ellectric/assume/configs/`
When 发送 `POST /simulate` 请求，body 为 `{"config": "summer_peak", "days": 7}`
Then 返回 200 状态码，JSON 包含 `clearing_prices`, `dispatch`, `agent_profits`

Given 请求的 config 名称不存在
When 发送 `POST /simulate` 请求
Then 返回 400 状态码，错误信息列出可用配置名称

### FR-03: 回测 API

Given 系统有历史数据和已训练的 RL 模型文件
When 发送 `POST /backtest` 请求，body 为 `{"start_date": "2022-08-01", "end_date": "2022-08-31", "strategy": "ppo", "model_path": "...", "data_source": "owid"}`
Then 返回 200 状态码，JSON 包含 `cumulative_pnl`, `sharpe_ratio`, `comparison`

Given 请求的 strategy 为 "baseline_persistence" (不需要 model_path)
When 发送 `POST /backtest` 请求且未提供 model_path
Then 正常运行，使用内置基准策略，不报错

Given 请求的 strategy 为 "ppo" 但未提供 model_path
When 发送 `POST /backtest` 请求
Then 返回 400 状态码，提示需要 model_path

### FR-04: 模型可解释性 API

Given 系统有已训练的 XGBoost 模型
When 发送 `POST /explain` 请求，body 为 `{"model_type": "xgboost", "sample_index": 0, "max_display": 10}`
Then 返回 200 状态码，JSON 包含 `feature_importance` (Top 10 ranking) 和 `waterfall_json`

### FR-05: CLI 预测命令

Given 系统已安装依赖
When 在终端执行 `el-cli forecast load 24`
Then 终端输出 24 小时预测值表格，包含 timestamp 和 prediction_mw 列

Given 使用无效 model_type
When 执行 `el-cli forecast bad 24`
Then 终端输出错误提示，列出有效选项 (load|price)

### FR-06: CLI 仿真命令

Given ASSUME 依赖就绪
When 执行 `el-cli simulate summer_peak --days 7`
Then 终端输出出清价格摘要 (avg/min/max) 和代理利润表

### FR-07: CLI 回测命令

Given 系统有历史数据和 RL 模型
When 执行 `el-cli backtest 2022-08-01 2022-08-31 ppo`
Then 终端输出累计 P&L、Sharpe ratio、策略对比表

### FR-08: CLI LLM 查询命令

Given DeepSeek API key 已配置为环境变量 `DEEPSEEK_API_KEY`
When 执行 `el-cli ask "昨天峰值负荷多少？"`
Then 终端输出自然语言回复，内容基于实际 API 调用结果

Given 未配置 `DEEPSEEK_API_KEY`
When 执行 `el-cli ask`
Then 终端输出友好提示，指引用户设置环境变量

### FR-09: LLM 交互对话

Given DeepSeek API key 已配置
When 执行 `python -m ellectric.llm.chat`
Then 进入交互式对话，支持多轮问答，`/exit` 退出

Given 用户输入与预测/仿真/回测无关的问题
When LLM 无法通过工具回答
Then 回复说明能力范围，不调用工具

### FR-10: 兼容性

Given Phase 1-3 已存在的 notebook 和脚本
When Phase 4 新增文件部署后
Then 所有已有功能的导入路径和行为不变

Given Phase 4 新增文件被删除
When 执行 Phase 1-3 notebook
Then 所有功能恢复到部署前状态（完全可回退）

## 非功能需求

- **兼容性**: pipeline 层零改动，所有已有导入路径不变
- **可回退**: 删除 `service/` `api/` `cli/` `llm/` 四个目录即可完全回退
- **可测试**: 每个端点/命令有明确输入输出契约
- **渐进式**: Wave 1 可独立验证，Wave 2 不依赖 Wave 3
- **LLM 可选**: 未配置 API key 时 API 和 CLI 命令 (forecast/simulate/backtest/explain) 不受影响
- **环境**: Python 3.11+，所有新增依赖通过 requirements-phase4.txt 声明
