---
author: lmr
created_at: 2026-06-23T14:52:56+08:00
---

# Requirements — 山西现货数据接入

## 角色 (Roles)

| 角色 | 描述 |
|---|---|
| Researcher | Electric 项目使用者，需要省级 15min 现货数据做学习/原型 |
| Pipeline Developer | 后续开发者，扩展更多数据源时复用 ShanxiBaseLoader 模式 |
| LLM Agent | 通过 `create_loader()` 工厂访问数据的 AI 工具 |

## 功能需求 (Functional Requirements)

### FR-001 — 原始数据归档

**Given** 山西零售商城公开 18 个 marketInfo API
**When** 全量扫描 2018-01 ~ 2026-12 所有月份
**Then** 所有响应（含空响应）原始 JSON 落盘至 `ellectric/data/raw/shanxi/`，并产出 `_full_summary.json` 总结表

### FR-002 — README 数据资产说明

**Given** 原始 JSON 已下载
**When** 用户/开发者打开 `ellectric/data/raw/shanxi/README.md`
**Then** 文档包含：
- 8 个数据查询 API 中英对照表
- 每个 API 的字段映射、有效时间范围
- 关键限制（月度典型曲线非逐日序列、字段推断置信度）
- 数据采集方法（cookie 来源、调用脚本路径）

### FR-003 — ShanxiBaseLoader 抽象基类

**Given** 需要复用文件扫描、月份解析、UTC 转换、24:00 边界处理逻辑
**When** 实现新的山西数据 loader
**Then** 提供 `ShanxiBaseLoader(DataLoader)` 基类，封装：
- `__init__(data_prefix, data_dir)` 接收前缀和目录
- `load_data(start, end) -> pd.DataFrame` 默认实现：扫描 + 月份筛选 + 调用 `_standardize`
- `_standardize(records, year_month)` 抽象方法，子类必须实现
- `_make_timestamp(date_str, time_str)` 处理 24:00 边界 + UTC 标准化
- 设置 `_metadata_source` 和 `_metadata_version`

### FR-004 — ShanxiSpotDaLoader

**Given** 用户调用 `create_loader("shanxi_spot_da").load_data(start="2022-04", end="2026-05")`
**When** loader 执行
**Then** 返回 DataFrame，列包括：
- `timestamp` (datetime64[ns, UTC])
- `da_price_a` (float64, 推断为日前出清价 A，元/MWh)
- `da_price_b` (float64, 推断为日前出清价 B，元/MWh)
- `load_mw` (float64, NaN — 价格数据无负荷等效)
- `province` ("shanxi")
- `source` ("pxf-phbsx-shop")
- `granularity` ("15min")
- 行数 ≈ 50 月 × 96 点 = 4800 行

### FR-005 — ShanxiSpotRtLoader

**Given** 用户调用 `create_loader("shanxi_spot_rt").load_data(start="2022-04", end="2026-05")`
**When** loader 执行
**Then** 返回 DataFrame，列包括：
- `timestamp` (datetime64[ns, UTC])
- `rt_energy_demand` (float64, 推断为实时需求量，万 MWh)
- `rt_energy_supply` (float64, 推断为实时供应量，万 MWh)
- `load_mw` (float64, 同 `rt_energy_demand`，作为等效负荷)
- `province`/`source`/`granularity` 同上
- 行数 ≈ 50 月 × 96 点 = 4800 行

### FR-006 — ShanxiMonthSettleLoader

**Given** 用户调用 `create_loader("shanxi_month_settle").load_data()`
**When** loader 执行
**Then** 返回 DataFrame，列包括：
- `timestamp` (datetime64[ns, UTC])
- `time_point` (int64, 每日分时点编号)
- `settle_day_price` (float64, 月度统一日结算点电价)
- `settle_rt_price` (float64, 月度实时结算点电价)
- `load_mw` (NaN)
- `province`/`source`/`granularity` ("daily-point")
- 行数 ≈ 108 月 × 23-24 点 ≈ 2525 行

### FR-007 — 工厂扩展

**Given** 现有 `create_loader(source, **kwargs)`
**When** 调用 `create_loader("shanxi_spot_da" | "shanxi_spot_rt" | "shanxi_month_settle")`
**Then** 返回对应子类实例，采用延迟导入（与现有 EmberLoader 一致）

### FR-008 — 现有 API 兼容性

**Given** 现有代码 `create_loader("owid")`/`create_loader("manual", data_path=...)`/`create_loader("ember")`
**When** 本变更落地后
**Then** 所有现有调用行为完全不变，OWIDChinaLoader/ChineseDataLoader/EmberLoader 源码零修改

### FR-009 — 优雅降级

**Given** 用户请求超出有效范围的 start/end（如 `start="2020-01"` for spot_da）
**When** loader 执行
**Then** 不抛异常，返回空 DataFrame + WARNING 日志，仍保持基础列结构

## 非功能需求 (Non-Functional Requirements)

### NFR-001 — 性能
- 单次 `load_data()` 应在 5 秒内完成（本地 JSON 扫描）

### NFR-002 — 代码风格
- 遵循 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md`：中英双语 docstring、`logger = logging.getLogger(__name__)`、`_` 前缀内部方法、`# ═════` 分隔符、类型标注

### NFR-003 — 依赖管理
- 不引入新依赖，复用 `pandas`/`pathlib`/`json`/`logging` 等

### NFR-004 — 文件组织
- 三个 loader 类放在独立文件 `ellectric/pipeline/shanxi_loader.py`，避免污染 `data_loader.py`
- `create_loader()` 内使用延迟导入

### NFR-005 — 字段推断免责
- `record1/record2/rqRecord/ssRecord` 精确业务含义未通过官方文档确认
- README 必须明确标注 `inferred` 置信度，建议下游使用方自行交叉验证

## 决策覆盖 (Decision Coverage)

| Requirement | Decision | 说明 |
|---|---|---|
| FR-003, FR-004, FR-005, FR-006 | D-001@v1 (方案B) | ShanxiBaseLoader + 3 子类继承 |
| FR-004 | D-002@v1 | record1/record2 → da_price_a/da_price_b 推断 |
| FR-005 | D-003@v1 | rqRecord/ssRecord → rt_energy_demand/rt_energy_supply 推断；load_mw=rt_energy_demand |
| FR-007 | D-004@v1 | 工厂延迟导入（参照 EmberLoader） |
| NFR-004 | D-005@v1 | 拆独立 shanxi_loader.py 文件 |