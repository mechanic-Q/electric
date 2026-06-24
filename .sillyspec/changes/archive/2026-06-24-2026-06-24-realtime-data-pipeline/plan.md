---
plan_level: light
author: lmr
created_at: 2026-06-24T15:10:00+08:00
---

# 轻量计划：数据抓取管道

## 来源

- proposal.md: 山西数据现需可重复抓取 + LLM/网站可调用接口
- design.md: ShanxiFetcher 模块 + CLI 壳 + snapshots 归档；3 条决策 D-001~D-003@v1
- tasks.md: 4 任务

## 范围

新增 4 个文件：

- `ellectric/fetch/__init__.py` — 模块入口
- `ellectric/fetch/shanxi.py` — `ShanxiFetcher` 类
- `ellectric/scripts/fetch_shanxi.py` — CLI 壳
- `ellectric/scripts/verify_fetch_shanxi.py` — 验证脚本

不动文件：`shanxi_loader.py`/`data_loader.py`/`config.py`/所有 pipeline 现有代码

## Tasks

### Wave 1 (无依赖)
- [x] task-01: 新建 `ellectric/fetch/__init__.py` 导出 ShanxiFetcher（覆盖：FR-001, D-001@v1）

### Wave 2 (依赖 task-01)
- [x] task-02: 实现 ShanxiFetcher 类（fetch_one/fetch_range/_save_snapshot/_save_latest，cookie 从 env 读）（覆盖：FR-001~FR-005, FR-007, D-001@v1, D-002@v1, D-003@v1）

### Wave 3 (依赖 task-02)
- [x] task-03: 新建 `ellectric/scripts/fetch_shanxi.py` CLI 壳（覆盖：FR-006）

### Wave 4 (依赖 task-03)
- [x] task-04: 新建 `ellectric/scripts/verify_fetch_shanxi.py` 验证脚本，测 fetch_one/snapshot/latest（覆盖：所有 FR）

## 验收

- [x] `from ellectric.fetch.shanxi import ShanxiFetcher` 成功
- [x] `python ellectric/scripts/verify_fetch_shanxi.py` 退出码 0
- [ ] `python ellectric/scripts/fetch_shanxi.py --month 2026-06 --source spot_da` 成功执行
- [x] snapshot 文件落到 `data/raw/shanxi/snapshots/<today>/spot_da_2026-06.json`
- [x] latest 文件 `data/raw/shanxi/spot_da_2026-06.json` 同步更新
- [x] 现有 `verify_shanxi_loader.py` 37/37 仍通过
- [x] cookie 默认从 `SHANXI_COOKIE` 环境变量读
- [x] 不引入新依赖

## 覆盖矩阵

| ID | 任务 | 验收 |
|---|---|---|
| D-001@v1（模块+脚本双模式） | task-01, task-02, task-03 | import + CLI 都能用 |
| D-002@v1（snapshots 归档） | task-02 | snapshot 文件存在 |
| D-003@v1（cookie 外部化） | task-02 | 默认从 env 读 |
| FR-001~FR-007 | task-01~task-04 | verify 脚本全过 |