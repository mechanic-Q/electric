---
plan_level: light
author: lmr
created_at: 2026-06-23T15:10:00+08:00
---

# 轻量计划：山西现货数据接入

## 来源

- proposal.md：动机为 OWID 年数据无法支撑 15min 现货交易，山西 `pmos.sx.sgcc.com.cn` 是唯二正式运行省份
- design.md：方案 B（ShanxiBaseLoader + 3 子类）已通过 Design Grill 审查，6 条决策 D-001@v1~D-006@v1 全 active
- requirements.md：9 FR + 5 NFR + 决策覆盖
- tasks.md：9 任务，T-001 数据下载已完成

## 范围

涉及文件：

- 新增 `ellectric/pipeline/shanxi_loader.py`（核心 loader 模块）
- 新增 `ellectric/data/raw/shanxi/README.md`（数据资产文档）
- 新增 `ellectric/scripts/verify_shanxi_loader.py`（验证脚本）
- 修改 `ellectric/pipeline/data_loader.py`（仅 `create_loader()` 工厂分支扩展）

已存在原始数据：`ellectric/data/raw/shanxi/*.json`（1947 文件，6.6 MB）

不动文件：`features.py`、`forecaster.py`、`price_loader.py`、`trading_env.py`、`rl_trainer.py`、`api/server.py`、`cli/main.py`、所有 notebook。

## Tasks (Wave 重排)

### Wave 1 (并行，无依赖)
- [x] task-01: 写 `data/raw/shanxi/README.md`，含 API 表、字段映射、有效范围、限制（覆盖：FR-001, FR-002, D-002@v1, D-003@v1, D-006@v1, NFR-005）
- [x] task-02: 在 `pipeline/shanxi_loader.py` 实现 `ShanxiBaseLoader(DataLoader)` 抽象基类，封装 JSON 扫描、月份解析、UTC 化、24:00 边界、`_metadata` 设置（覆盖：FR-003, D-001@v1, D-005@v1, NFR-002, NFR-003）

### Wave 2 (依赖 task-02，可互相并行)
- [x] task-03: 在同文件实现 `ShanxiSpotDaLoader`：record1→da_price_a / record2→da_price_b，load_mw=NaN（覆盖：FR-004, D-002@v1）
- [x] task-04: 在同文件实现 `ShanxiSpotRtLoader`：rqRecord→rt_energy_demand / ssRecord→rt_energy_supply，load_mw=rt_energy_demand（覆盖：FR-005, D-003@v1）
- [x] task-05: 在同文件实现 `ShanxiMonthSettleLoader`：dayPrice→settle_day_price / realTimePrice→settle_rt_price，处理逐日分时（覆盖：FR-006, D-002@v1）

> ⚠️ 注意：task-03/04/05 在逻辑上独立可并行，但物理上修改同一文件 `shanxi_loader.py`。execute 阶段必须**串行追加**，不能真正并行编辑。

### Wave 3 (依赖 task-02~05)
- [x] task-06: 修改 `pipeline/data_loader.py` 的 `create_loader()`，添加 `shanxi_spot_da` / `shanxi_spot_rt` / `shanxi_month_settle` 三个分支（延迟导入）（覆盖：FR-007, FR-008, D-004@v1）

### Wave 4 (依赖 task-06)
- [x] task-07: 新增 `ellectric/scripts/verify_shanxi_loader.py` 验证脚本，调用 3 个 source 的 `load_data()`，打印行数/列名/时间范围/元数据，验证优雅降级（覆盖：FR-009, NFR-001）

## 验收

- [x] `python ellectric/scripts/verify_shanxi_loader.py` 退出码 0
- [x] 输出包含：shanxi_spot_da ≥ 4000 行；shanxi_spot_rt ≥ 4000 行；shanxi_month_settle ≥ 2000 行
- [x] 每个 source 返回的 DataFrame 必含列：`timestamp`(UTC)、`load_mw`、`province`、`source`、`granularity`
- [x] `loader.get_metadata()` 返回 dict 含 source/rows/start/end 非空
- [x] 超范围 start/end（如 `start="2010-01"`）返回空 DataFrame + WARNING 日志，无异常
- [x] `create_loader("owid")`、`create_loader("manual", data_path=...)`、`create_loader("ember")` 行为不变
- [x] `data/raw/shanxi/README.md` 列出 8 个数据 API + 字段表 + 推断置信度 + 关键限制
- [x] 单次 `load_data()` 在 5 秒内完成（NFR-001）
- [x] 无新依赖（NFR-003），所有 import 已在 requirements.txt
- [x] `shanxi_loader.py` 模块级 docstring 使用中英双语 + ASCII 图（NFR-002）
- [x] 全部函数签名带类型标注（NFR-002）
- [x] 现有 OWIDChinaLoader / ChineseDataLoader / cleaner / features / forecaster 源码零修改

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1（三子类继承） | task-02, task-03, task-04, task-05 | 验证脚本输出 3 个 source 返回非空 DataFrame |
| D-002@v1（record1/2 重命名） | task-01, task-03, task-05 | DataFrame 列含 da_price_a/b 及 settle_day_price/rt_price |
| D-003@v1（rqRecord 重命名 + load_mw 映射） | task-01, task-04 | DataFrame 列含 rt_energy_demand/supply 且 load_mw 与 rt_energy_demand 相等 |
| D-004@v1（延迟导入） | task-06 | `data_loader.py` 顶层 import 不含 shanxi_loader，仅函数内 |
| D-005@v1（独立文件） | task-02 | `shanxi_loader.py` 文件存在且 `data_loader.py` 行数变化 ≤ 30 行 |
| D-006@v1（仅 3 API） | task-02, task-03, task-04, task-05, task-06 | 验证脚本只调 3 个 source；其他 API 不进 create_loader 分支 |
| FR-001（数据归档） | T-001（已完成） | 1947 文件已在 raw/shanxi/ |
| FR-002（README） | task-01 | data/raw/shanxi/README.md 存在 |
| FR-003~FR-006（4 loader） | task-02, task-03, task-04, task-05 | 各 loader 返回正确字段 DataFrame |
| FR-007~FR-008（工厂 + 兼容） | task-06 | 3 新 source 可用且现有 source 不变 |
| FR-009（优雅降级） | task-07 | 超范围 start/end 返回空 DataFrame |
| NFR-001~NFR-005 | task-02, task-07 | 性能 5s + 风格 conventions + 0 新依赖 |