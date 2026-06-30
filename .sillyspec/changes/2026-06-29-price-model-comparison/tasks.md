---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Tasks: 电价模型对比报告

- [ ] T-01: 新增 PyTorch DNN 电价预测器
  - 文件: `ellectric/pipeline/price_forecaster_dnn.py`
  - 覆盖: FR-01, D-001@v1, D-003@v1

- [ ] T-02: 新增 price comparison 脚本骨架
  - 文件: `ellectric/scripts/compare_price_models.py`
  - 覆盖: FR-02, FR-03, D-002@v1

- [ ] T-03: 实现 LEAR/DNN/persistence/weekly_avg 统一评估
  - 文件: `ellectric/scripts/compare_price_models.py`
  - 覆盖: FR-02, FR-03, FR-04

- [ ] T-04: 接入 DM/GW 统计检验
  - 文件: `ellectric/scripts/compare_price_models.py`, `ellectric/pipeline/statistical_tests.py`
  - 覆盖: FR-05

- [ ] T-05: 生成 JSON/MD/HTML/log 报告
  - 文件: `ellectric/reports/price_comparison/`
  - 覆盖: FR-06, FR-07

- [ ] T-06: 可选扩展 service/CLI model_type
  - 文件: `ellectric/service/schemas.py`, `ellectric/service/handlers.py`, `ellectric/cli/main.py`
  - 覆盖: D-004@v1

- [ ] T-07: 新增测试
  - 文件: `tests/test_price_forecaster_dnn.py`, `tests/test_compare_price_models.py`
  - 覆盖: FR-01~FR-08

- [ ] T-08: 更新模块文档
  - 文件: `docs/Ellectric/modules/price-forecaster.md`
  - 覆盖: D-001@v1, D-002@v1
