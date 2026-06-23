---
plan_level: light
author: lmr
created_at: 2026-06-23T19:20:00+08:00
---

# 轻量计划：时间分辨率参数化

## 来源

- proposal.md: 上变更 shanxi-spot-data-access 已接 15min 数据，pipeline 还吃不下
- design.md: 方案=全局 TimeConfig + 5 文件逐个替换，6 条决策 D-001~D-003@v1
- requirements.md: 7 FR + 4 NFR
- tasks.md: 7 任务

## 范围

- 新增 `ellectric/config.py`（TimeConfig 类）
- 修改 5 个 pipeline 文件: `trading_env.py`, `features.py`, `forecaster.py`, `price_forecaster.py`, `cleaner.py`
- 新增 `ellectric/scripts/verify_time_resolution.py` 验证脚本

不动文件：`data_loader.py` / `shanxi_loader.py` / `cli/main.py` / `api/server.py` / 所有 notebook / `requirements.txt`

## Tasks

### Wave 1 (无依赖)
- [x] task-01: 新建 `ellectric/config.py` 定义 TimeConfig 类（覆盖：FR-001, D-001@v1, NFR-002）

### Wave 2 (依赖 task-01，可并行)
- [x] task-02: `trading_env.py` 约 30 处硬编码替换（覆盖：FR-002, D-002@v1）
- [x] task-03: `features.py` 2 处 shift 替换（覆盖：FR-003, D-002@v1）
- [x] task-04: `forecaster.py` 1 处 shift 替换（覆盖：FR-004, D-002@v1）
- [x] task-05: `price_forecaster.py` 5 处 shift 替换（覆盖：FR-005, D-002@v1）
- [x] task-06: `cleaner.py` freq 比较和重采样目标替换（覆盖：FR-006, D-002@v1）

### Wave 3 (依赖全部)
- [x] task-07: 新建 `ellectric/scripts/verify_time_resolution.py` 验证脚本（覆盖：FR-007, D-003@v1, NFR-001~NFR-004）

## 验收

- [x] `python ellectric/scripts/verify_time_resolution.py` 退出码 0
- [x] 默认 24 下，`python ellectric/scripts/verify_shanxi_loader.py` 仍 24/24 通过
- [x] 改 `TimeConfig.points_per_day=96` 后，`ElectricityMarketEnv().action_space.shape == (96,)`
- [x] `features.py` 的 `shift(...)` 调用所有出现处都引用 TimeConfig
- [x] `cleaner.py` 没有硬编码 `"h"` 文字比较
- [x] `requirements.txt` 不变
- [x] `ellectric/pipeline/data_loader.py`、`shanxi_loader.py` 零修改
- [x] 全部新建/修改文件含类型标注（NFR-002）

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1（全局配置单例） | task-01 | `ellectric/config.py` 存在 + 3 属性 |
| D-002@v1（逐文件替换） | task-02~06 | 5 文件硬编码均替换 |
| D-003@v1（默认值不变） | task-01, task-07 | TimeConfig 默认 24/168/"h"，verify_shanxi_loader 24/24 通过 |
| FR-001 | task-01 | TimeConfig 类 |
| FR-002~FR-006 | task-02~06 | 5 文件全部替换 |
| FR-007 | task-07 | 默认行为不变验证 |
| NFR-001~NFR-004 | task-01, task-07 | 性能/风格/兼容/原子切换 |