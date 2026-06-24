---
author: lmr
created_at: 2026-06-24T15:00:00+08:00
---

# Requirements — 数据抓取管道

## 角色

| 角色 | 描述 |
|---|---|
| Pipeline Developer | 复用 ShanxiFetcher 抓取数据 |
| 数据分析师 | 跑 CLI 更新数据 |
| LLM/API (未来) | 通过模块 import 调用 |

## 功能需求

### FR-001 — ShanxiFetcher 模块

**Given** `from ellectric.fetch.shanxi import ShanxiFetcher`
**Then** ShanxiFetcher 类可实例化 with cookie 和 data_dir

### FR-002 — fetch_one 单 API 抓取

**Given** `ShanxiFetcher(...).fetch_one(source="spot_da", month="2026-06")`
**Then** 返回 dict 含 status/rows/snapshot_path/latest_path

### FR-003 — fetch_range 批量抓取

**Given** `ShanxiFetcher(...).fetch_range(sources=None, months=None)`
**Then** 默认抓全 18 API × 2018-01~当月范围

### FR-004 — snapshot 归档

**Given** 抓取成功
**Then** 保存到 `data/raw/shanxi/snapshots/<today>/<source>_<month>.json`，永不覆盖

### FR-005 — latest 视图同步

**Given** 抓取成功
**Then** 同时更新 `data/raw/shanxi/<source>_<month>.json`（与现有 loader 兼容）

### FR-006 — CLI 壳

**Given** `python ellectric/scripts/fetch_shanxi.py --month 2026-06`
**Then** 调用 ShanxiFetcher.fetch_range 处理参数

### FR-007 — cookie 配置外部化

**Given** 未传 cookie 时
**Then** 从环境变量 `SHANXI_COOKIE` 读

## 非功能需求

### NFR-001 — 性能
- 单 API 单月抓取 < 10s（含网络延迟）

### NFR-002 — 代码风格
- 遵循 CONVENTIONS.md

### NFR-003 — 兼容性
- 不修改 ShanxiSpotDaLoader/SpotRtLoader 等已有 loader
- 不引入新依赖（已用 playwright）

### NFR-004 — 安全
- cookie 不写死在代码
- 默认从 SHANXI_COOKIE 环境变量读

## 决策覆盖

| Req | Decision |
|---|---|
| FR-001~003 | D-001@v1 模块+脚本双模式 |
| FR-004~005 | D-002@v1 snapshots 归档 |
| FR-007 | D-003@v1 cookie 外部化 |
