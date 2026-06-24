---
author: lmr
created_at: 2026-06-24T00:10:00+08:00
---

# Tasks — 数据 schema 扩展

## task-01 — ShanxiMonthDealLoader

- **目标**：追加 `ShanxiMonthDealLoader` 到 `shanxi_loader.py`，长表展开 dateList/energyList/priceList
- **文件**：`ellectric/pipeline/shanxi_loader.py` (追加 ~40 行)
- **覆盖**：FR-001, D-001@v1, D-002@v1

## task-02 — ShanxiUserTransactionLoader

- **目标**：追加 `ShanxiUserTransactionLoader`，与 task-01 同模式，type→market_member
- **文件**：同上
- **覆盖**：FR-002, D-001@v1, D-002@v1
- **依赖**：task-01（同文件串行）

## task-03 — ShanxiYearTradeFitLoader

- **目标**：追加 `ShanxiYearTradeFitLoader`，seriesData/seriesName 长表展开
- **文件**：同上
- **覆盖**：FR-003, D-001@v1, D-002@v1
- **依赖**：task-02

## task-04 — ShanxiMonthSettle1Loader

- **目标**：追加 `ShanxiMonthSettle1Loader`，继承 ShanxiMonthSettleLoader 的 _standardize
- **文件**：同上
- **覆盖**：FR-004, D-001@v1
- **依赖**：task-03

## task-05 — ShanxiTimeDivTrendLoader

- **目标**：追加 `ShanxiTimeDivTrendLoader`，与 task-03 同模式，trend_value 含义
- **文件**：同上
- **覆盖**：FR-005, D-001@v1, D-002@v1
- **依赖**：task-04

## task-06 — create_loader 扩展

- **目标**：data_loader.py 加 5 个 elif（延迟导入）
- **文件**：`ellectric/pipeline/data_loader.py` (+ ~15 行)
- **覆盖**：FR-006
- **依赖**：task-01~05

## task-07 — verify_shanxi_loader 扩展

- **目标**：在现有 verify 脚本追加 5 个 source 验证段，每段 ≥ 2 项检查；docstring 标 inferred 字段（覆盖 D-003@v1）
- **文件**：`ellectric/scripts/verify_shanxi_loader.py` (+ ~30 行)
- **覆盖**：FR-007, D-003@v1
- **依赖**：task-06
