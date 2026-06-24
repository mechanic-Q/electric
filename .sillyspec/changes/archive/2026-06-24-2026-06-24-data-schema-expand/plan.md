---
plan_level: light
author: lmr
created_at: 2026-06-24T00:15:00+08:00
---

# 轻量计划：数据 schema 扩展

## 来源

- proposal.md: shanxi-spot-data-access (#7) D-006@v1 决策"暂仅接入 3 个 API"，本变更补完其余 5 个
- design.md: 同文件追加 5 子类 + create_loader 5 elif + verify 扩展
- tasks.md: 7 任务

## 范围

修改 3 个文件：

- `ellectric/pipeline/shanxi_loader.py` — 追加 5 个新子类（约 +200 行）
- `ellectric/pipeline/data_loader.py` — create_loader 加 5 elif（延迟导入）
- `ellectric/scripts/verify_shanxi_loader.py` — 扩展 5 个 source 验证段

不动文件：`features.py` / `forecaster.py` / `cleaner.py` / `trading_env.py` / `price_forecaster.py` / `data_loader.py` 既有 source / `ShanxiBaseLoader` 及现有 3 子类

## Tasks

### Wave 1 (同文件串行追加)
- [x] task-01: 追加 ShanxiMonthDealLoader（覆盖：FR-001, D-001@v1, D-002@v1）
- [x] task-02: 追加 ShanxiUserTransactionLoader（覆盖：FR-002, D-001@v1, D-002@v1）
- [x] task-03: 追加 ShanxiYearTradeFitLoader（覆盖：FR-003, D-001@v1, D-002@v1）
- [x] task-04: 追加 ShanxiMonthSettle1Loader（覆盖：FR-004, D-001@v1）
- [x] task-05: 追加 ShanxiTimeDivTrendLoader（覆盖：FR-005, D-001@v1, D-002@v1）

> ⚠️ task-01~05 物理上修改同一文件 `shanxi_loader.py`，必须串行追加

### Wave 2 (依赖全部子类)
- [x] task-06: data_loader.py create_loader 加 5 elif 分支（覆盖：FR-006）

### Wave 3 (依赖工厂扩展)
- [x] task-07: verify_shanxi_loader.py 扩展 5 source 验证段（覆盖：FR-007, D-003@v1）

## 验收

- [x] `python ellectric/scripts/verify_shanxi_loader.py` 退出码 0
- [x] 总验证 ≥ 35 项
- [x] 5 个新 source 全部 create_loader().load_data() 返回非空
- [x] 现有 24 项验证（spot_da/spot_rt/month_settle/优雅降级/兼容性）全通过
- [x] shanxi_loader.py 既有 4 类源码零修改
- [x] requirements.txt 不变
- [x] data_loader.py 顶层无 shanxi_loader import（延迟导入）

## 覆盖矩阵

| ID | 任务 | 验收 |
|---|---|---|
| D-001@v1 | task-01~07 | 同文件追加沿用 ShanxiBaseLoader |
| D-002@v1 | task-01,02,03,05 | 长表展开输出 |
| D-003@v1 | task-01~07 | docstring + verify 标 inferred |
| FR-001~005 | task-01~05 | 5 source 各自验证 |
| FR-006 | task-06 | create_loader 工厂 |
| FR-007 | task-07 | verify 扩展 |