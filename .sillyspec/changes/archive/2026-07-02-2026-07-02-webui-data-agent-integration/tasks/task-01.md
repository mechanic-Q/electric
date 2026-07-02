---
id: task-01
title: "扩展 service schemas（覆盖：FR-01, FR-02, FR-03, D-002@v1, D-005@v1）"
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: []
blocks: [task-02, task-03, task-04, task-05, task-06]
requirement_ids: [FR-01, FR-02, FR-03]
decision_ids: [D-002@v1, D-005@v1]
allowed_paths: [ellectric/service/schemas.py]
---

# task-01: 扩展 service schemas

## goal

在 `ellectric/service/schemas.py` 新增 4 个 Pydantic v2 schema，为 catalog/dataset/report 响应提供统一契约：`CapabilityItem`、`DatasetInfo`、`ReportSummary`、`ReportDetail`。现有 Forecast/Simulate/Backtest/Explain/Recommend schema 不动。

## implementation

追加到文件末尾（RecommendResponse 之后），新增 catalog 分区：

1. **CapabilityItem(BaseModel)**：id, title, category (Literal 7 值), description, example_questions (list[str]), endpoint (str|None), tool_name (str|None), supports_offline_fallback (bool), available (bool)
2. **DatasetInfo(BaseModel)**：id, title, description, source, frequency, rows, start, end, columns, available
3. **ReportSummary(BaseModel)**：id, title, report_type, status (Literal["ok","missing","error"]), generated_at, summary, metrics (dict), paths (dict)
4. **ReportDetail(ReportSummary)**：继承 ReportSummary，新增 content (dict|str|None)

## acceptance

- [ ] `CapabilityItem` 含 9 个字段，category 为 7 值 Literal
- [ ] `DatasetInfo` 含 10 个字段，columns 默认空列表
- [ ] `ReportSummary` 含 8 个字段，status 为 3 值 Literal
- [ ] `ReportDetail` 继承 `ReportSummary` 并新增 content 字段
- [ ] 所有 list/dict 默认值使用 `Field(default_factory=...)` 而非裸 `=[]` / `={}`
- [ ] 现有 schema 无任何修改

## verify

```bash
python -m pytest tests/test_service_catalog.py tests/test_api_catalog.py -q
```

## constraints

- Pydantic v2 语法：使用 `Field(default_factory=list)` / `Field(default_factory=dict)` 作为 list/dict 默认值，禁止裸 `= []` / `= {}` 赋值
- 不引入 pydantic v1 兼容 API（无 `@validator`、无 `class Config`）
- 类型标注使用 Python 3.10+ 原生语法（`list[str]`、`dict[str, float]`、`str | None`）
