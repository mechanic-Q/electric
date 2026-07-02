---
id: task-05
title: 新增 catalog service 测试（覆盖：FR-01, FR-02, FR-03, FR-05, D-002@v1, D-003@v1, D-005@v1）
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-01, task-02, task-03]
blocks: [task-13]
requirement_ids: [FR-01, FR-02, FR-03, FR-05]
decision_ids: [D-002@v1, D-003@v1, D-005@v1]
allowed_paths: [tests/test_service_catalog.py]
---

## goal

验证 catalog registry 三项事实（capabilities/datasets/reports）的正常读取、缺失报告路径处理、模型缺失 forecast fallback 行为。确保 registry/fallback 逻辑不依赖 LLM/API/网络。

## implementation

tests/test_service_catalog.py:

1. **TestCapabilityRegistry** — `list_capabilities()` returns `list[CapabilityItem]`; each item has id/title/category/description/example_questions; category is valid `Literal`.

2. **TestDatasetRegistry** — `list_datasets()` returns `list[DatasetInfo]`; entries populated when loader metadata available; `available=false` when source missing; no exception thrown.

3. **TestReportRegistry** — `list_reports()` returns `list[ReportSummary]`; supports `report_type` filter; empty dir returns []; missing dir returns []; status field handles ok/missing/error.

4. **TestReportDetail** — `get_report()` returns `ReportDetail` for existing report; returns `status="missing"` (no exception) for unknown `report_id`; content field present in detail.

5. **TestForecastFallback** — `build_forecast_fallback()` returns structured dict with `source="offline_report"` and `fallback_reason` for model_missing/load_error; returns None for unknown model type.

## acceptance

- list_capabilities() 返回非空列表，每项符合 CapabilityItem schema
- list_datasets() 在 loader 可用时填充 available=true，不可用时 available=false 不抛异常
- list_reports() 过滤正确，缺失目录返回 []
- get_report() 读取存在的报告返回 ReportDetail，不存在的返回 status="missing"
- build_forecast_fallback() 返回含 "offline_report" 来源标识的 dict

## verify

```bash
python -m pytest tests/test_service_catalog.py -q
```

## constraints

- 仅修改 `tests/test_service_catalog.py`，不修改 service/schema/catalog/handler 源码
- 使用 `tmp_path` / `monkeypatch` / `unittest.mock.patch` 隔离文件系统和模块依赖
- 不启动 FastAPI 服务器，不访问外部网络
- 不依赖真实报告文件在磁盘上存在
