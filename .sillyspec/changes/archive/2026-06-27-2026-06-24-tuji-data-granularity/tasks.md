---
author: lmr
created_at: 2026-06-26 21:12:40
---

# Tasks

## 任务列表

- [ ] T-001: 校准 TimeConfig 文档与默认值
  - 文件路径：`ellectric/config.py`
  - 覆盖：FR-002, D-003@v1

- [ ] T-002: 修正清洗频率规范化逻辑
  - 文件路径：`ellectric/pipeline/cleaner.py`
  - 覆盖：FR-003, D-003@v1, D-004@v1

- [ ] T-003: 迁移负荷特征窗口到 TimeConfig
  - 文件路径：`ellectric/pipeline/features.py`
  - 覆盖：FR-004, D-003@v1, D-004@v1

- [ ] T-004: 迁移电价特征窗口与训练 gap
  - 文件路径：`ellectric/pipeline/price_forecaster.py`
  - 覆盖：FR-004, D-003@v1, D-004@v1

- [ ] T-005: 迁移负荷预测训练 gap 与文案
  - 文件路径：`ellectric/pipeline/forecaster.py`
  - 覆盖：FR-004, D-003@v1, D-004@v1

- [ ] T-006: 迁移 TradingEnv 动作与观测维度语义
  - 文件路径：`ellectric/pipeline/trading_env.py`
  - 覆盖：FR-005, D-003@v1, D-004@v1

- [ ] T-007: 补强山东 15min loader metadata 合约
  - 文件路径：`ellectric/pipeline/shandong_loader.py`
  - 覆盖：FR-001, D-002@v1

- [ ] T-008: 更新 service schema 数据源与 horizon 语义
  - 文件路径：`ellectric/service/schemas.py`
  - 覆盖：FR-006, D-005@v1

- [ ] T-009: 更新 service handlers 使用 shandong data_source
  - 文件路径：`ellectric/service/handlers.py`
  - 覆盖：FR-001, FR-006, D-002@v1, D-005@v1

- [ ] T-010: 更新 CLI/API/LLM 用户可见文案
  - 文件路径：`ellectric/cli/main.py`, `ellectric/api/server.py`, `ellectric/llm/tools.py`
  - 覆盖：FR-006, D-005@v1

- [ ] T-011: 更新 README、module docs、notebook 15min 语义
  - 文件路径：`ellectric/README.md`, `docs/Ellectric/modules/*.md`, `ellectric/notebooks/*.ipynb`
  - 覆盖：FR-006, D-001@v1, D-004@v1

- [ ] T-012: 新增 15min 时间分辨率测试
  - 文件路径：`tests/test_time_resolution_15min.py`
  - 覆盖：FR-007, D-003@v1, D-005@v1

## Plan 阶段说明

本文件只列任务名称、路径、覆盖关系。具体任务顺序、依赖、验收命令、分 wave 执行策略在 `sillyspec run plan --change 2026-06-24-tuji-data-granularity` 阶段展开。
