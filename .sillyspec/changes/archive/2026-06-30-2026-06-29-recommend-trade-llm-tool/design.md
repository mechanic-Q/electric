---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Design: LLM 交易建议工具

## 背景

当前 Ellectric 已经具备预测、回测、解释和 LLM 工具调用，但用户仍需要自己把分散结果翻译为交易含义。本变更把这些能力组合成一个“交易建议”接口，输出可验证的结构化建议，再由 LLM 转成中文解释。

## 设计目标

- 提供统一 `/recommend` 能力，面向 API / CLI / LLM 三通道。
- 输出双层信息：结构化动作 + 人类可读总结。
- 建议必须可追溯到 forecast/backtest/SHAP evidence。
- 低置信度时保守输出，始终包含学习用途免责声明。

## 非目标

- 不做真实交易下单。
- 不做实时行情轮询。
- 不新增模型训练。
- 不替代已有 forecast/backtest/explain 接口。

## 决策/方案选择

- **方案选择**: 采用双层输出：service 返回结构化交易动作，LLM 只做中文解释。
- **动作 schema**: `buy/sell/hold + price_limit + quantity_mwh + reason + confidence`。
- **不选方案**: 不让 LLM 直接自由生成交易建议，不只输出模糊方向性建议。
- **取舍理由**: 结构化 JSON 可测试、可回放；自然语言适合学习者理解；低置信度必须保守输出。
- **执行策略**: 先新增 `/recommend` + CLI + LangChain tool，复用现有 forecast/backtest/explain 证据。

## 总体方案

### 数据流

1. `RecommendRequest` 进入 service 层。
2. `run_recommend_trade()` 调用现有预测与回测 handler。
3. handler 生成 peak window、price signal、historical P&L context、top features。
4. service 输出 `RecommendResponse`。
5. API / CLI / LLM tool 只转发或格式化该响应。

### Schema

`RecommendRequest`:
- `date: str`
- `horizon_hours: int = 24`
- `market: str = "shandong"`
- `risk_preference: str = "balanced"`
- `max_actions: int = 5`

`RecommendResponse`:
- `summary: str`
- `actions: list[TradeAction]`
- `confidence: "high" | "medium" | "low"`
- `evidence: dict`
- `disclaimer: str`

`TradeAction`:
- `timestamp: str`
- `action: "buy" | "sell" | "hold"`
- `price_limit: float | None`
- `quantity_mwh: float | None`
- `reason: str`
- `confidence: "high" | "medium" | "low"`

### Confidence 规则

- high: forecast/backtest/explain 三类 evidence 均可用且历史指标有效。
- medium: forecast + 至少一个辅助 evidence 可用。
- low: 预测或回测缺失、异常、指标不可用。

low 时默认输出 hold 或 reduced-size 动作。

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 修改 | `ellectric/service/schemas.py` |
| 修改 | `ellectric/service/handlers.py` |
| 修改 | `ellectric/api/server.py` |
| 修改 | `ellectric/cli/main.py` |
| 修改 | `ellectric/llm/tools.py` |
| 修改 | `ellectric/llm/agent.py` |
| 新增 | `tests/test_recommend_handler.py` |
| 新增 | `docs/Ellectric/modules/recommend.md` |
| 新增 | `ellectric/reports/recommend/sample_output.md` |

## 兼容策略

- 只新增 endpoint/tool/CLI，不改现有 forecast/backtest/explain 行为。
- LLM tool 注册为新增工具，不移除旧工具。
- confidence guard 是输出层约束，不改变模型结果。

## 风险

| 风险 | 缓解 |
|---|---|
| LLM 幻觉 | 工具返回结构化 JSON，LLM 只转述 |
| 建议过度确定 | confidence guard + disclaimer |
| 运行慢 | horizon 限制默认 24，最大 72 |
| 下游 handler 不稳定 | 缺 evidence 时降级 low confidence |

## 验收

- `/recommend` schema 稳定。
- CLI 可输出中文建议。
- LangChain tool 可用。
- 单元测试覆盖降级路径和低置信保护。
