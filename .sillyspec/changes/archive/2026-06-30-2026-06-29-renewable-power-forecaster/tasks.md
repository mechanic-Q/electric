---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Tasks: 风/光功率独立预测模块

- [ ] T-01: 新增 `renewable_forecaster.py` 基础结构
  - 文件: `ellectric/pipeline/renewable_forecaster.py`
  - 覆盖: FR-01, FR-02, FR-03, D-001@v1, D-003@v1

- [ ] T-02: 实现 Tier1-4 特征构建与缺 weather 降级
  - 文件: `ellectric/pipeline/renewable_forecaster.py`
  - 覆盖: FR-04, D-004@v1

- [ ] T-03: 扩展 service/API/CLI forecast model_type
  - 文件: `ellectric/service/schemas.py`, `ellectric/service/handlers.py`, `ellectric/api/server.py`, `ellectric/cli/main.py`
  - 覆盖: FR-06

- [ ] T-04: 扩展 LLM forecast tool 文档
  - 文件: `ellectric/llm/tools.py`
  - 覆盖: FR-06

- [ ] T-05: 新增验证脚本与报告产物
  - 文件: `ellectric/scripts/validate_renewable_forecaster.py`, `ellectric/reports/renewable_forecaster/`
  - 覆盖: FR-05, FR-07

- [ ] T-06: 新增测试
  - 文件: `tests/test_renewable_forecaster.py`
  - 覆盖: FR-01~FR-08

- [ ] T-07: 新增模块文档
  - 文件: `docs/Ellectric/modules/renewable-forecaster.md`
  - 覆盖: FR-01, FR-02, D-002@v1
