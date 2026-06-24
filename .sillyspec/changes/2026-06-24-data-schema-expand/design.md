---
author: lmr
created_at: 2026-06-24T00:10:00+08:00
---

# 数据 schema 扩展 — 设计文档

## 背景

变更 `shanxi-spot-data-access` (PR #7) 只接入了 3 个核心 API（spot_da/spot_rt/month_settle）。原始数据下载时还有 5 个有效 API 已落盘但未实现 loader：

- `month_deal` — 批发市场中长期成交
- `user_transaction` — 用户侧成交
- `year_trade_fit` — 年度交易各标的月拟合分时价格曲线
- `month_settle1` — 用户侧月度统一结算点电价（2）
- `time_div_trend` — 分时浮动项历史参考值

D-006@v1 决策为"暂仅接入 3 个，其余归档"，留给后续变更。本次变更补完。

## 设计目标

1. 5 个新 loader 子类，沿用 `ShanxiBaseLoader` 抽象基类
2. `create_loader()` 扩展 5 个 source key（延迟导入）
3. 字段语义化重命名（保留 `inferred` 标注）
4. `verify_shanxi_loader.py` 扩展验证段
5. 不修改 shanxi_loader.py 已有 4 类

## 非目标

- ❌ 不做特征工程层利用新字段
- ❌ 不做新 API 抓取（数据已在 raw/shanxi/）
- ❌ 不重命名 month_settle1 → month_settle_alt
- ❌ 不添加新的 dataLoader 顶层模块

## 决策

### D-001@v1 — 同文件追加 5 子类（方案 A）

**决策**：在 `ellectric/pipeline/shanxi_loader.py` 末尾追加 5 个子类。

**备选**：
- B：独立 `shanxi_schema_ext.py`（被拒：拆文件后引用导入更复杂）
- C：配置表驱动（被拒：抽象过早，5 个字段差异大）

**理由**：与既有 ShanxiSpotDa/Rt/MonthSettle 三类同模式，文件膨胀到 1100 行可接受。

### D-002@v1 — 长表展开（series/dateList 类型字段）

**决策**：对 `dateList`/`energyList`/`priceList` 或 `seriesData`/`seriesName` 等 array-typed records，展开为长表：每个 (date/series, energy, price) 一行。

**理由**：保持 DataFrame 长表语义与已有 loaders 一致，下游消费简单。

### D-003@v1 — `inferred` 字段语义保留

**决策**：5 个新子类的字段含义未官方文档化时标 `inferred`。

## 总体方案

### 字段映射表

#### `ShanxiMonthDealLoader` (`month_deal_`)

原始记录形式：

```json
[
  {"type": "购方", "dateList": ["2026-05-01", ...], "energyList": [...], "priceList": [...]},
  {"type": "售方", "dateList": [...], "energyList": [...], "priceList": [...]}
]
```

输出列：

| 原始 | DataFrame 列 | 类型 | 含义 | 置信度 |
|---|---|---|---|---|
| `type` | `deal_side` | str | 购方/售方 | 高 |
| `dateList[i]` | `timestamp` | datetime64[ns, UTC] | 日期 | 高 |
| `energyList[i]` | `deal_energy_mwh` | float64 | 成交电量 (MWh) | inferred |
| `priceList[i]` | `deal_price` | float64 | 成交价 (元/MWh) | inferred |

加基础列：`province`/`source`/`granularity="daily"`、`load_mw=NaN`

#### `ShanxiUserTransactionLoader` (`user_transaction_`)

类似 month_deal，区别是 `type` 改 `marketMember`（市场主体名）。

输出列：`market_member` (str)、`timestamp`、`deal_energy_mwh`、`deal_price` (inferred)、`load_mw=NaN`、`province`/`source`/`granularity="daily"`。

#### `ShanxiYearTradeFitLoader` (`year_trade_fit_`)

原始记录形式：

```json
[
  {"seriesName": "标的A", "seriesData": [123.4, 456.7, ...]},
  {"seriesName": "标的B", "seriesData": [...]}
]
```

输出列：`series_name`、`time_index` (int)、`fit_price` (float, 元/MWh, inferred)、`load_mw=NaN`、`province`/`source`/`granularity="month-curve"`。

#### `ShanxiMonthSettle1Loader` (`month_settle1_`)

字段与 `month_settle` 完全一致 —— 复用基类逻辑。继承 `ShanxiMonthSettleLoader` 的 `_standardize`，仅改 `data_prefix` 和 `_metadata_source`。

输出列同 `month_settle`，granularity="daily-point"。

#### `ShanxiTimeDivTrendLoader` (`time_div_trend_`)

字段与 `year_trade_fit` 相同结构（seriesData/seriesName），但语义是分时浮动项。

输出列：`series_name`、`time_index`、`trend_value` (float)、`load_mw=NaN`、`province`/`source`/`granularity="time-div"`。

### 文件变更清单

| 操作 | 文件 | 说明 |
|---|---|---|
| 修改 | `ellectric/pipeline/shanxi_loader.py` | 追加 5 子类（约 +200 行） |
| 修改 | `ellectric/pipeline/data_loader.py` | create_loader 加 5 elif（延迟导入） |
| 修改 | `ellectric/scripts/verify_shanxi_loader.py` | 扩展 5 source 验证段 |

不修改：ShanxiBaseLoader/ShanxiSpotDaLoader/ShanxiSpotRtLoader/ShanxiMonthSettleLoader 既有逻辑。

### 接口定义

```python
class ShanxiMonthDealLoader(ShanxiBaseLoader):
    _metadata_source = "shanxi-month-deal"
    def __init__(self, data_dir: str | None = None):
        super().__init__(data_prefix="month_deal", data_dir=data_dir)
    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame: ...

# 类似 4 个其他
```

create_loader 扩展：

```python
elif source == "shanxi_month_deal":
    from ellectric.pipeline.shanxi_loader import ShanxiMonthDealLoader
    return ShanxiMonthDealLoader(**kwargs)
# 类似 4 个其他
```

### 验证标准

1. 5 个 source 都能 `create_loader().load_data()` 返回非空 DataFrame
2. 列名按设计严格匹配
3. 现有 24/24 验证仍通过（回归）
4. 不引入新依赖
5. 现有 ShanxiBaseLoader/SpotDa/SpotRt/MonthSettle 行为零变化

## 风险

| ID | 风险 | 等级 | 应对 |
|---|---|---|---|
| R-01 | 长表展开实现错误导致行数偏差 | P1 | 验证脚本严格检查行数 |
| R-02 | inferred 字段含义被下游误用 | P1 | README 标注，docstring 明示 |
| R-03 | 数据空文件多时 long-table 失败 | P2 | 沿用基类 graceful degradation |

## 自审

- 一致性：5 个子类沿用 ShanxiBaseLoader，与 D-006@v1 决策（仅 3 个核心）的"留给后续变更"约定一致
- 完备性：5 个 API 全覆盖，proposal 不在范围内列表明示 cleaner/forecaster 不动
- 风险登记齐：R-01 长表展开误差、R-02 inferred 误用、R-03 空数据降级
- 接口一致：5 个新子类 _metadata_source/_metadata_version/data_prefix 三件套与现有完全对齐
- 无生命周期关键词，无契约表
