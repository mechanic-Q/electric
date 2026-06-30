
---
schema_version: 1
doc_type: module-card
module_id: recommend
author: lmr
created_at: 2026-06-30T15:10:48Z
---

# recommend

## 定位

聚合负荷预测、历史回测和模型可解释性证据，生成结构化交易建议。
作为 LLM Agent 的 `recommend_trade` 工具后端，提供可解释、可追溯的 buy/sell/hold 动作序列。

## 契约摘要

- `TradeAction(BaseModel)` — 结构化交易动作
  - `timestamp: str` — ISO 时间戳
  - `action: Literal["buy", "sell", "hold"]` — 交易动作
  - `price_limit: float | None` — 限价（元/MWh）
  - `quantity_mwh: float | None` — 建议电量（MWh）
  - `reason: str` — 中文原因说明
  - `confidence: Literal["high", "medium", "low"]` — 单条建议置信度
- `RecommendRequest(BaseModel)` — 请求参数
  - `date: str` — 交易日期 YYYY-MM-DD
  - `horizon_hours: int` — 预测时长（小时），默认 24，范围 1-72
  - `market: str` — 数据源标识，默认 "shandong"
  - `risk_preference: str` — 风险偏好: conservative/balanced/aggressive
  - `max_actions: int` — 最多返回动作数，默认 5，范围 1-10
- `RecommendResponse(BaseModel)` — 响应
  - `summary: str` — 中文交易建议总结
  - `actions: list[TradeAction]` — 交易动作列表
  - `confidence: Literal["high", "medium", "low"]` — 总体置信度
  - `evidence: dict` — 证据摘要（forecast/backtest/explain 可用性）
  - `disclaimer: str` — 学习用途免责声明

## 关键逻辑

### 数据流

```
RecommendRequest
  │
  ├─▸ run_forecast()        ──► forecast_data (timestamps, predictions)
  ├─▸ run_backtest()        ──► backtest_data (cumulative_pnl, sharpe_ratio, comparison)
  └─▸ run_explain()         ──► explain_data (top_features)

  ──► _determine_confidence()  ──► "high" | "medium" | "low"
  ──► _generate_actions()      ──► list[TradeAction]
  ──► _build_summary()         ──► str
  ──► RecommendResponse
```

### 置信度规则（`_determine_confidence`）

| 条件 | 置信度 |
|------|--------|
| forecast + backtest + explain 全部可用 | `high` |
| forecast + (backtest or explain) 可用 | `medium` |
| 其他情况（含全部不可用） | `low` |

### 动作生成（`_generate_actions`）

- **低置信度**：仅返回 hold 动作，原因明确指出"证据不足"
- **有预测数据**：根据预测趋势（up/down/flat）生成 sell/buy/hold
- **有回测数据**：追加 oracle 策略上下文 hold 动作（含夏普比率）
- **有可解释性数据**：追加关键特征上下文 hold 动作
- 最终截断至 `max_actions` 条

## API 端点

```http
POST /recommend
Content-Type: application/json

{
  "date": "2026-01-15",
  "horizon_hours": 24,
  "market": "shandong",
  "risk_preference": "balanced",
  "max_actions": 5
}
```

响应：

```json
{
  "summary": "目标日期: 2026-01-15\n预测: available | 回测: available | ...",
  "actions": [
    {
      "action": "sell",
      "timestamp": "2026-01-15T12:00:00",
      "price_limit": 410.20,
      "quantity_mwh": 30.0,
      "reason": "预测价格呈上升趋势，在 2026-01-15T12:00:00 附近达峰值 410.20 元/MWh，建议卖出",
      "confidence": "high"
    }
  ],
  "confidence": "high",
  "evidence": {
    "forecast": "available",
    "backtest": "available",
    "explain": "available"
  },
  "disclaimer": "⚠️ 此为学习平台生成的模拟交易建议，不构成任何真实交易建议。请勿据此进行实际电力交易。"
}
```

## CLI 用法

```bash
# 默认配置
ellectric recommend 2026-01-15

# 指定风险偏好 + 动作数
ellectric recommend 2026-01-15 --risk-preference conservative --max-actions 3

# JSON 输出
ellectric recommend 2026-01-15 --json
```

## LLM Tool 注册

```python
# ellectric/llm/tools.py
@tool
def recommend_trade(date: str, horizon: int = 24,
                    risk_preference: str = "balanced",
                    max_actions: int = 5) -> str:
    """生成并解释结构化电力交易建议。"""
```

LangChain Agent 工具列表：`tools=[query_forecast, run_simulation, run_backtest, recommend_trade]`

## 注意事项

- 三个上游服务（forecast/backtest/explain）任一个失败不阻塞整体流程，仅降低置信度
- service 层生成结构化动作，LLM 仅负责转述，不修改数值
- 所有数据基于模拟/历史数据，无实时市场接入
- `horizon_hours` 超范围 → Pydantic ValidationError
- `max_actions` 超范围 → Pydantic ValidationError

## 非目标

| 功能 | 原因 |
|------|------|
| 真实交易下单 | 学习项目，不涉及真实资金 |
| 实时市场接入 | 数据源结构性不支持 |
| 自动执行交易 | LLM 只建议，不下单 |

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
