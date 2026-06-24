---
author: lmr
created_at: 2026-06-24T15:00:00+08:00
---

# Tasks — 数据抓取管道

## task-01 — 新建 fetch 模块入口

- **目标**：新建 `ellectric/fetch/__init__.py`，导出 ShanxiFetcher
- **文件**：`ellectric/fetch/__init__.py`
- **覆盖**：FR-001, D-001@v1

## task-02 — 实现 ShanxiFetcher 核心类

- **目标**：写 `ShanxiFetcher.__init__`/`fetch_one`/`fetch_range`/`_save_snapshot`/`_save_latest`
- **文件**：`ellectric/fetch/shanxi.py`
- **覆盖**：FR-001~005, D-001@v1, D-002@v1, D-003@v1
- **依赖**：task-01

## task-03 — CLI 壳

- **目标**：写 `fetch_shanxi.py`，argparse 解析 `--month`/`--source`/`--all`/`--range`
- **文件**：`ellectric/scripts/fetch_shanxi.py`
- **覆盖**：FR-006
- **依赖**：task-02

## task-04 — 验证脚本

- **目标**：新建 `verify_fetch_shanxi.py`，测 fetch_one/snapshot 生成/latest 更新/不破坏现有
- **文件**：`ellectric/scripts/verify_fetch_shanxi.py`
- **覆盖**：所有 FR
- **依赖**：task-03
