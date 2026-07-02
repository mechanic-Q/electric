---
id: task-02
title: "新增 catalog registry 服务（覆盖：FR-01, FR-02, FR-03, D-002@v1, D-003@v1, D-005@v1）"
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-01]
blocks: [task-03, task-05]
requirement_ids: [FR-01, FR-02, FR-03]
decision_ids: [D-002@v1, D-003@v1, D-005@v1]
allowed_paths: [ellectric/service/catalog.py]
---

# task-02: 新增 catalog registry 服务

## goal

在 `ellectric/service/catalog.py` 新建一个只读事实目录：capabilities（能问什么/能运行什么）、datasets（数据源元信息）、reports（离线报告摘要与详情），供 API 与 LLM tools 复用。

## implementation

1. 定义 `list_capabilities()` 静态聚合已知能力：负荷/电价/风光预测、市场仿真、回测、SHAP、交易建议、报告、数据集，附示例问题、endpoint、tool_name、`supports_offline_fallback`。
2. 定义 `list_datasets()`：轻量描述山东、OWID、Chinese 三个数据源；读取失败或缺少 loader metadata 时返回 `available=False`，不抛异常。
3. 定义 `list_reports(report_type=None)`：扫描 `ellectric/reports/full_real_run/**/SUMMARY.json`、`rl_full_dataset/evaluation_report.json`、`weather_tier4/weather_tier4_validation.json`、`renewable_forecaster/renewable_forecast_validation.json` 及价格模型对比 JSON；提取标量指标进入 `metrics`。
4. 定义 `get_report(report_id)`：按稳定 ID 返回 `ReportDetail`；未知 ID 返回 `status="missing"`。
5. 内部工具：`_scan_full_real_run()`、`_resolve_project_relative_path()`；只返回项目内相对路径。

## acceptance

- [ ] `list_capabilities()` 至少包含 predict/price/wind/solar/simulate/backtest/explain/recommend/reports/datasets 类别。
- [ ] `list_datasets()` 在数据源缺失时仍返回条目并 `available=False`。
- [ ] `list_reports()` 在报告缺失时跳过或返回 `status="missing"`，不抛异常。
- [ ] `get_report("weather_tier4/validation")` 返回带 `metrics` 的 `ReportDetail`。
- [ ] 所有路径为项目内相对路径，不出现绝对路径或路径穿越。

## verify

```bash
python -m pytest tests/test_service_catalog.py -q
```

## constraints

- 只读：不训练模型、不重新生成报告、不写任何文件。
- 报告解析容错：JSON 缺字段用默认值，异常降级为 `status="error"`。
- 不依赖 DEEPSEEK_API_KEY 或任何网络调用。
- 数据集元信息优先来自 loader `get_metadata()`；失败时降级为静态描述并标 `available=False`。
