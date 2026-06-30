---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Proposal: LLM 交易建议工具

## 动机

Ellectric 已经跑通数据接入、负荷/电价预测、RL 回测、SHAP 解释和 LangChain 工具调用。当前 LLM 助手能查询 forecast/backtest/explain，但还不能把这些结果合成为人类可读的“交易指导”。

本变更新增一个结构化交易建议能力：后端先产出可测试 JSON，LLM 只负责转述和解释，避免模型自由编造交易结论。

## 变更范围

- 新增 `/recommend` REST API、CLI `recommend` 子命令、LangChain `recommend_trade` 工具。
- 新增 service handler：串联负荷预测、电价预测、历史回测摘要、SHAP top features。
- 输出双层建议：结构化数值动作 + 自然语言解释。
- 动作 schema 使用完整 `buy/sell/hold + price + quantity + reason + confidence`。
- 强制学习用途免责声明，不生成真实交易指令。

## 不在范围内

- 不接入真实交易下单。
- 不承诺盈利，不提供投资建议。
- 不新增外部市场数据源。
- 不训练新模型；只组合已有 forecast/backtest/explain 能力。
- 不做实时调度或守护进程。

## 成功标准

- `POST /recommend` 返回固定 schema 的 JSON。
- `python -m ellectric.cli.main recommend 2026-01-15 --horizon 24` 可运行。
- LLM `recommend_trade` 工具能调用 `/recommend` 并返回中文说明。
- 低置信度时输出保守建议和免责声明。
- 单元测试覆盖 schema、confidence、低置信 guard、LLM tool HTTP 调用。
