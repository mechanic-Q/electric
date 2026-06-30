---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Decisions: LLM 交易建议工具

## Current Decisions

### D-001@v1: 建议粒度采用“双层输出”

**决策**: 工具返回结构化数值动作，LLM 输出自然语言方向性解释。

**理由**: 结构化 JSON 可测试、可回放；自然语言适合学习者理解。两层同时保留可解释性和稳定性。

### D-002@v1: 动作 schema 使用完整 buy/sell/hold + price + quantity

**决策**: 每条建议包含 `action`, `price_limit`, `quantity_mwh`, `reason`, `confidence`。

**理由**: 比“低吸/高抛”更贴近图迹自动交易机器人形态，但仍限定为模拟建议。

### D-003@v1: LLM 只能转述工具证据，不允许自由计算交易建议

**决策**: `/recommend` 是事实源；LangChain agent 只做解释层。

**理由**: 避免 LLM 幻觉和不可测试建议。

### D-004@v1: confidence guard 强制保守输出

**决策**: 低置信度时必须输出 hold 或 reduced-size 建议，并带免责声明。

**理由**: 项目是学习原型，不应制造过度确定的交易口吻。

## Unresolved

无。
