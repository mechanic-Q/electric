---
author: lmr
created_at: 2026-06-23T14:52:56+08:00
---

# Tasks — 山西现货数据接入

> 实现任务清单，按依赖顺序排列。每个任务覆盖 FR 编号；细节延后到 plan 阶段。

## T-001 — 原始数据下载（已完成 ✅）

- **目标**：山西零售商城 18 个 marketInfo API × 2018-01~2026-12 全部月份扫描下载
- **文件**：`ellectric/data/raw/shanxi/*.json`（1947 文件，6.6 MB）
- **覆盖**：FR-001
- **状态**：✅ 已完成（在 brainstorm 阶段已经下载）

## T-002 — 数据资产 README

- **目标**：写 `data/raw/shanxi/README.md` 详细说明 18 个 API、字段映射、有效范围、限制
- **文件**：`ellectric/data/raw/shanxi/README.md`（新增）
- **覆盖**：FR-002, NFR-005

## T-003 — ShanxiBaseLoader 抽象基类

- **目标**：实现抽象基类，封装 JSON 文件扫描、月份筛选、UTC 处理、24:00 边界、_metadata 设置
- **文件**：`ellectric/pipeline/shanxi_loader.py`（新增）
- **覆盖**：FR-003, NFR-002, NFR-003, NFR-004
- **依赖**：T-001（数据已下载）

## T-004 — ShanxiSpotDaLoader 子类

- **目标**：实现日前现货 loader，字段重命名 record1/record2 → da_price_a/da_price_b
- **文件**：`ellectric/pipeline/shanxi_loader.py`（同 T-003 文件）
- **覆盖**：FR-004
- **依赖**：T-003

## T-005 — ShanxiSpotRtLoader 子类

- **目标**：实现实时现货 loader，字段重命名 rqRecord/ssRecord → rt_energy_demand/rt_energy_supply；写 load_mw=rt_energy_demand
- **文件**：`ellectric/pipeline/shanxi_loader.py`（同上）
- **覆盖**：FR-005
- **依赖**：T-003

## T-006 — ShanxiMonthSettleLoader 子类

- **目标**：实现月度结算价 loader，dayPrice/realTimePrice → settle_day_price/settle_rt_price；处理 point 编号
- **文件**：`ellectric/pipeline/shanxi_loader.py`（同上）
- **覆盖**：FR-006
- **依赖**：T-003

## T-007 — create_loader 工厂扩展

- **目标**：在 `create_loader()` 添加 `shanxi_spot_da`/`shanxi_spot_rt`/`shanxi_month_settle` 三个分支，使用延迟导入
- **文件**：`ellectric/pipeline/data_loader.py`（修改，仅扩展工厂函数）
- **覆盖**：FR-007, FR-008
- **依赖**：T-004, T-005, T-006

## T-008 — 优雅降级验证

- **目标**：验证超出范围 start/end 返回空 DataFrame + WARNING，不报错
- **文件**：手工验证或写在 docstring 示例
- **覆盖**：FR-009
- **依赖**：T-007

## T-009 — 验收脚本

- **目标**：写一个最小验证脚本，跑通 3 个 source 的 `create_loader().load_data()`，打印行数/列名/时间范围
- **文件**：`ellectric/scripts/verify_shanxi_loader.py`（新增）
- **覆盖**：成功标准 3-7
- **依赖**：T-007