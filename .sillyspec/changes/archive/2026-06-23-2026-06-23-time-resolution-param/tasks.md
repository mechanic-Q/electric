---
author: lmr
created_at: 2026-06-23T19:10:00+08:00
---

# Tasks — 时间分辨率参数化

> 任务清单按依赖顺序，task-01 必须先做。

## task-01 — 新建 TimeConfig 全局配置

- **目标**：创建 `ellectric/config.py`，定义 `TimeConfig` 类，3 个类属性 + 中英双语 docstring
- **文件**：`ellectric/config.py`（新增）
- **覆盖**：FR-001, D-001@v1, NFR-002

## task-02 — trading_env.py 参数化

- **目标**：替换约 30 处 24/168/`"h"` 硬编码为 `TimeConfig` 引用
- **文件**：`ellectric/pipeline/trading_env.py`（修改）
- **覆盖**：FR-002, D-002@v1
- **依赖**：task-01

## task-03 — features.py 参数化

- **目标**：替换 2 处 `shift(24)` / `shift(168)`，扩展到 rolling 调用
- **文件**：`ellectric/pipeline/features.py`（修改）
- **覆盖**：FR-003, D-002@v1
- **依赖**：task-01

## task-04 — forecaster.py 参数化

- **目标**：替换 1 处 `shift(24)`
- **文件**：`ellectric/pipeline/forecaster.py`（修改）
- **覆盖**：FR-004, D-002@v1
- **依赖**：task-01

## task-05 — price_forecaster.py 参数化

- **目标**：替换 5 处 `shift(24)` / `shift(168)`
- **文件**：`ellectric/pipeline/price_forecaster.py`（修改）
- **覆盖**：FR-005, D-002@v1
- **依赖**：task-01

## task-06 — cleaner.py 参数化

- **目标**：替换 freq 比较和重采样目标
- **文件**：`ellectric/pipeline/cleaner.py`（修改）
- **覆盖**：FR-006, D-002@v1
- **依赖**：task-01

## task-07 — 验证脚本

- **目标**：新建 `verify_time_resolution.py`，覆盖：
  - 默认 24 下 verify_shanxi_loader 仍通过（D-003@v1 兼容性）
  - 改 `TimeConfig.points_per_day=96` 后 trading_env shape 变 (96,)
  - cleaner 不再硬编码 "h"
- **文件**：`ellectric/scripts/verify_time_resolution.py`（新增）
- **覆盖**：FR-007, D-003@v1, NFR-001~NFR-004
- **依赖**：task-02~06 全部
