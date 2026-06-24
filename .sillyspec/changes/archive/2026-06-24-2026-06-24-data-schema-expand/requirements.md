---
author: lmr
created_at: 2026-06-24T00:10:00+08:00
---

# Requirements — 数据 schema 扩展

## 角色

| 角色 | 描述 |
|---|---|
| Pipeline Developer | 扩展 5 个 loader 子类 |
| 数据分析师 | 使用 create_loader 加载新字段做分析 |

## 功能需求

### FR-001 — ShanxiMonthDealLoader

**Given** `create_loader("shanxi_month_deal").load_data()`
**Then** 返回 DataFrame 含列：`timestamp`(UTC)、`deal_side`、`deal_energy_mwh`(inferred)、`deal_price`(inferred)、`load_mw`(NaN)、`province`、`source`、`granularity="daily"`

### FR-002 — ShanxiUserTransactionLoader

**Given** `create_loader("shanxi_user_transaction").load_data()`
**Then** 返回 DataFrame 含列：`timestamp`、`market_member`、`deal_energy_mwh`、`deal_price`、`load_mw=NaN`、基础列

### FR-003 — ShanxiYearTradeFitLoader

**Given** `create_loader("shanxi_year_trade_fit").load_data()`
**Then** 返回 DataFrame 含列：`series_name`、`time_index`、`fit_price`、`load_mw=NaN`、基础列、granularity="month-curve"

### FR-004 — ShanxiMonthSettle1Loader

**Given** `create_loader("shanxi_month_settle1").load_data()`
**Then** 返回 DataFrame 含列：`timestamp`、`time_point`、`settle_day_price`、`settle_rt_price`、`load_mw=NaN`、基础列、granularity="daily-point"

### FR-005 — ShanxiTimeDivTrendLoader

**Given** `create_loader("shanxi_time_div_trend").load_data()`
**Then** 返回 DataFrame 含列：`series_name`、`time_index`、`trend_value`、`load_mw=NaN`、基础列、granularity="time-div"

### FR-006 — create_loader 扩展

**Given** 现有 create_loader 函数
**When** 调用 5 个新 source key 中任一
**Then** 返回对应子类实例（延迟导入）；现有 source 行为不变

### FR-007 — 验证脚本扩展

**Given** `verify_shanxi_loader.py`
**Then** 增加 5 个新 source 测试段（每段 ≥ 2 项验证），总验证 ≥ 35 项；现有 24 项保持通过

## 非功能需求

### NFR-001 — 性能
- 单个 loader 的 load_data 在 5 秒内完成

### NFR-002 — 代码风格
- 遵循 CONVENTIONS.md（中英双语 docstring、logger、类型标注）

### NFR-003 — 兼容性
- 现有 ShanxiBaseLoader/SpotDa/SpotRt/MonthSettle 代码零修改
- requirements.txt 不变

### NFR-004 — 推断标注
- 标记 inferred 字段在 docstring，建议下游交叉验证

## 决策覆盖

| Requirement | Decision |
|---|---|
| FR-001~FR-005 | D-001@v1 同文件追加 |
| FR-001~FR-003,FR-005 | D-002@v1 长表展开 |
| FR-001~FR-005 | D-003@v1 inferred 字段标注 |
| FR-006 | D-001@v1 延迟导入沿用 |
| FR-007 | D-001@v1 单脚本扩展 |
