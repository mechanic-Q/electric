---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Requirements: LLM 交易建议工具

## 功能需求

- [ ] **FR-01**: 新增 `RecommendRequest`，字段包含 `date`, `horizon_hours`, `market`, `risk_preference`, `max_actions`。
- [ ] **FR-02**: 新增 `RecommendResponse`，字段包含 `summary`, `actions`, `confidence`, `evidence`, `disclaimer`。
- [ ] **FR-03**: `actions` 必须是结构化列表，每项包含 `timestamp`, `action`, `price_limit`, `quantity_mwh`, `reason`, `confidence`。
- [ ] **FR-04**: service handler 串联现有 forecast/backtest/explain 能力；缺某项时降级但不崩溃。
- [ ] **FR-05**: FastAPI 新增 `/recommend`，CLI 新增 `recommend`，LLM tools 新增 `recommend_trade`。
- [ ] **FR-06**: confidence=low 时必须输出保守建议，并明确“不建议依赖该输出做真实交易”。
- [ ] **FR-07**: 所有输出必须包含学习用途免责声明。
- [ ] **FR-08**: 新增单元测试，覆盖 schema、降级路径、confidence guard、LLM tool 调用。

## 非功能需求

- 不触网调用交易平台；只调用本地 API。
- 单次 `/recommend` 默认 horizon 不超过 72 小时。
- LLM 不负责计算核心数值，只转述 service 返回的结构化结果。

## 验收命令

- `rtk pytest tests/test_recommend_handler.py`
- `python -m ellectric.cli.main recommend 2026-01-15 --horizon 24`
