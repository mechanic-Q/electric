---
id: task-03
title: 新增 catalog handlers 与 forecast fallback helper
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-01, task-02]
blocks: [task-04, task-05, task-07]
requirement_ids: [FR-01, FR-02, FR-03, FR-05]
decision_ids: [D-003@v1, D-005@v1]
allowed_paths:
  - ellectric/service/handlers.py
---

## goal

在 `handlers.py` 中新增 5 个函数，桥接 catalog registry（task-02）与 API/LLM 层：

- `list_capabilities()` / `list_datasets()` — 轻量委托至 `catalog` 模块。
- `list_reports(report_type=None)` / `get_report(report_id)` — 同上，加错误包装。
- `build_forecast_fallback(model_type, error)` — 当模型缺失时构造结构化 fallback dict，供 LLM tool（task-07）使用。

## implementation

1. 在文件尾部追加新函数。顶部导入 `from ellectric.service.catalog import ...`。
2. `list_capabilities/list_datasets/list_reports/get_report`：直接委托给同名的 `catalog.*` 函数；允许 `get_report` 在 catalog 抛出异常时返回 `status="error"` 的 `ReportDetail`，不往上抛。
3. `build_forecast_fallback(model_type, error)`：检查 `error` 类型。若是 `FileNotFoundError`（模型文件缺失），返回 `{"status": "fallback", "source": "offline_report", "fallback_reason": "model_missing", ...}`，并调用 `list_reports` 查找匹配的离线报告摘要；返回 `None` 表示无法 fallback。
4. 不修改 `run_forecast` / `run_simulate` / `run_backtest` / `run_explain` / `run_recommend_trade` 等已有函数。

## acceptance

- `list_capabilities()` 返回 catalog 注册的全部 CapabilityItem。
- `list_datasets()` 与 `list_reports()` 正确代理 catalog 返回值。
- `get_report("known_id")` 返回正常 ReportDetail；`get_report("nonexistent")` 返回 `status="error"` 的 detail。
- `build_forecast_fallback("load", FileNotFoundError("xgboost_model.joblib"))` 返回带离线指标的 dict。
- `build_forecast_fallback("load", ValueError("bad arg"))` 返回 `None`（非模型错误不隐藏）。

## verify

python -m pytest tests/test_service_catalog.py -q

## constraints

- 保持旧 `/predict` 语义 — `run_forecast` 完全不动。
- fallback helper 只对 `FileNotFoundError`（模型缺）或加载时异常触发 fallback；对 `ValueError`、数据错误等非模型异常返回 `None`，由上层决定如何处理。
- handler 函数不引入新的 pydantic schema 或网络调用。
