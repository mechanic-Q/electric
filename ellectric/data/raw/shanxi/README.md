# 山西电力现货数据资产 (Shanxi Spot Market Data Assets)

> 原始数据归档目录。本文件为数据资产说明书，描述数据来源、字段语义、已知限制和使用方式。
> 纯文档，不含可执行命令。

---

## 1. 数据源

### 1.1 域名与认证

| 项目 | 值 |
|---|---|
| 数据源域名 | `pxf-phbsx-shop.pmos.sx.sgcc.com.cn` |
| 认证方式 | Cookie 认证（浏览器登录后从 DevTools → Application → Cookies 提取） |
| 采集方 | 人工脚本下载，非自动化爬虫 |

### 1.2 采集方法

数据采集通过浏览器登录山西电力交易平台后，调用后端 JSON API 逐月拉取。采集脚本位于 `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/` 目录下的勘探脚本中（仅作引用，不嵌入本文档；后续维护无需自动重跑）。

> **安全提示**: 本文档不包含任何 Cookie 值、登录凭据或具体下载命令。Cookie 为会话级敏感信息，需由使用者自行从浏览器提取。

### 1.3 文件命名约定

```
ellectric/data/raw/shanxi/<prefix>_YYYY-MM.json
```

- `<prefix>`: API 短标识（如 `spot_da`、`spot_rt`、`month_settle` 等，见第 2 节）
- `YYYY-MM`: 数据所属年月（如 `2024-01`）
- 全部文件均为 UTF-8 编码 JSON

### 1.4 全景概览

| 指标 | 值 |
|---|---|
| 归档文件总数 | 1947 |
| 归档总大小 | ~6.6 MB |
| API 总数 | 18 |
| 已接入 loader | 3（spot_da / spot_rt / month_settle） |
| 归档待接入 | 5（month_deal / user_transaction / year_trade_fit / time_div_trend / month_settle1） |
| 仅原始保留 | 10（非交易数据类 API） |
| 时间跨度 | 2018-01 ~ 2026-12（108 个月） |

---

## 2. API 接入清单

### 2.1 核心 API（8 个）

| prefix | API 路径 (queryXxx) | 中文名 | 接入状态 | 月份数 | 总行数 | fmt |
|---|---|---|---|---|---|---|
| `spot_da` | `querySpotMarketClearing` | 现货日前出清 | **loader** | 50 (2022-04~2026-05) | 4800 | dict |
| `spot_rt` | `queryRealTimeSpotMarketClearing` | 现货实时出清 | **loader** | 50 (2022-04~2026-05) | 4800 | dict |
| `month_settle` | `queryUserMonthSettlementPrice` | 月度结算电价 | **loader** | 108 (2018-01~2026-12) | 2525 | list |
| `month_deal` | `queryMonthDeal` | 月度成交 | 归档 | 108 | 216 | list |
| `user_transaction` | `queryUserTransaction` | 用户侧交易 | 归档 | 108 | 216 | list |
| `year_trade_fit` | `queryYearTradeFittingPrice` | 年度拟合电价 | 归档 | 108 | 216 | list |
| `time_div_trend` | `queryTimeDivisionPriceTrend` | 分时电价趋势 | 归档 | 108 | 432 | list |
| `month_settle1` | `queryUserMonthSettlementPrice1` | 月度结算电价(v1) | 归档 | 108 | 1073 | dict |

**接入状态说明**:
- **loader**: 已实现 `DataLoader` 子类，可通过 `create_loader()` 工厂函数加载为标准化 DataFrame
- **归档**: 原始 JSON 已下载保存，但尚未实现 loader；`create_loader()` 暂不可用

### 2.2 非核心 API（10 个，仅原始 JSON 保留）

以下 API 返回非交易数据（市场动态、政策文件、公共信息、零售结算等），仅保留原始 JSON 文件，不进入数据 pipeline 层，不承诺 loader 接入。

| prefix | API 路径 | 中文名 | fmt | 说明 |
|---|---|---|---|---|
| `price_trend` | `queryPriceTrend` | 价格趋势 | dict | 分时电价曲线数据 |
| `no_time_trend` | `queryNoTimeDivisionPriceTrend` | 非分时电价趋势 | dict | 非分时维度价格趋势 |
| `month_market` | `queryMonthTradeMarketList` | 月度交易市场列表 | dict | 市场元数据，`data=[]` |
| `market_list` | `queryMarketList` | 市场列表 | dict | 市场元数据，`data=[]` |
| `market_users` | `queryMarketUserList` | 市场用户列表 | dict | 用户元数据，`data=[]` |
| `public_info` | `queryPublicInfoClient` | 公共信息 | dict | 公示信息 |
| `dynamic` | `queryMarketDynamics` | 市场动态 | dict | 分页包装，嵌套 list |
| `policy` | `queryPolicyDocument` | 政策文件 | dict | 分页包装，嵌套 list |
| `retail_settle` | `queryRetailSettlement` | 零售结算 | dict | 分页包装，嵌套 list |
| `retail_prob` | `queryRetailProblemInfo` | 零售问题信息 | dict | 分页包装，嵌套 list |

以上 10 个 API 均覆盖 2018-01~2026-12（108 个月），每月 1 个 JSON 文件，`fmt` 为 `dict` 或 `list`。

---

## 3. 字段映射详表

### 3.1 spot_da — 现货日前出清 (querySpotMarketClearing)

| 原始 JSON 字段 | DataFrame 列 | 类型 | 推断含义 | 置信度 |
|---|---|---|---|---|
| `endPointTime` | `timestamp` | datetime64[ns, UTC] | 15min 时段结束时间（00:15~24:00，共 96 点/日） | 确定 |
| `record1` | `da_price_a` | float64 | 日前出清价 A（元/MWh） | **[inferred]** |
| `record2` | `da_price_b` | float64 | 日前出清价 B（元/MWh） | **[inferred]** |
| (注入) | `load_mw` | float64 | NaN — 价格数据，无负荷等效列 | 约定 |
| (注入) | `province` | str | `"shanxi"` | 确定 |
| (注入) | `source` | str | `"pxf-phbsx-shop"` | 确定 |
| (注入) | `granularity` | str | `"15min"` | 确定 |

> **[inferred] 说明**: `record1` / `record2` 在前端源码中周围出现"均价(元/MWh)"字样，但未明确两个字段的精确业务含义（可能为"挂牌价 vs 加权价"或不同价区维度）。`da_price_a` / `da_price_b` 为项目内部语义化重命名，**不可直接用作生产交易决策依据**，下游使用方应自行交叉验证。

### 3.2 spot_rt — 现货实时出清 (queryRealTimeSpotMarketClearing)

| 原始 JSON 字段 | DataFrame 列 | 类型 | 推断含义 | 置信度 |
|---|---|---|---|---|
| `dataTime` | `timestamp` | datetime64[ns, UTC] | 15min 时段（00:15~24:00，共 96 点/日） | 确定 |
| `rqRecord` | `rt_energy_demand` | float64 | 实时需求量（**万 MWh**） | **[inferred]** |
| `ssRecord` | `rt_energy_supply` | float64 | 实时供应量（**万 MWh**） | **[inferred]** |
| (映射) | `load_mw` | float64 | = `rt_energy_demand`（等效负荷） | 约定 |
| (注入) | `province` | str | `"shanxi"` | 确定 |
| (注入) | `source` | str | `"pxf-phbsx-shop"` | 确定 |
| (注入) | `granularity` | str | `"15min"` | 确定 |

> **[inferred] 说明**: `rqRecord` / `ssRecord` 在前端源码中做 `value/1e5` 转换为"亿千瓦时"显示，暗示数据为电量量级。`rt_energy_demand` / `rt_energy_supply` 为项目内部语义化重命名，**不可直接用作生产交易决策依据**。
>
> **量纲警示**: `rt_energy_demand` 和 `rt_energy_supply` 的实际单位为 **万 MWh**（非 MW）。`load_mw` 列名虽含 `_mw` 后缀，但对 spot_rt 实际承载的是万 MWh 数值（直接复制 `rt_energy_demand`）。这是为了满足 `DataLoader` 抽象合约要求 `load_mw` 列必须存在而做的等效映射，**下游运算时请注意量纲差异**。

### 3.3 month_settle — 月度结算电价 (queryUserMonthSettlementPrice)

| 原始 JSON 字段 | DataFrame 列 | 类型 | 含义 | 置信度 |
|---|---|---|---|---|
| `dataTime` | `timestamp` | datetime64[ns, UTC] | 日期（YYYY-MM-DD） | 确定 |
| `point` | `time_point` | int64 | 每日分时点编号（0~23，2018-01~2022-10 为 23 点，2022-11 起为 24 点） | 确定 |
| `dayPrice` | `settle_day_price` | float64 | 月度日前统一结算点电价（元/MWh） | 高频 |
| `realTimePrice` | `settle_rt_price` | float64 | 月度实时统一结算点电价（元/MWh） | 高频 |
| (注入) | `load_mw` | float64 | NaN — 价格数据，无负荷等效列 | 约定 |
| (注入) | `province` | str | `"shanxi"` | 确定 |
| (注入) | `source` | str | `"pxf-phbsx-shop"` | 确定 |
| (注入) | `granularity` | str | `"daily-point"` | 确定 |

> **分时点数量变化**: 2018-01~2022-10 每月 23 个分时点，2022-11 起每月 24 个分时点。

---

## 4. 有效时间范围与数据形态

### 4.1 spot_da / spot_rt（现货日前/实时出清）

| 属性 | 值 |
|---|---|
| 文件覆盖 | 2018-01 ~ 2026-12（108 个月，每月 1 个 JSON 文件） |
| **有效数据范围** | **2022-04 ~ 2026-05**（50 个月） |
| 空数据月份 | 2018-01 ~ 2022-03（58 个月）`data=[]`（仅 1 行 wrapper） |
| 暂无数据月份 | 2026-06 ~ 2026-12（文件存在但 `data=[]`） |
| 每月数据行数 | 96 行（15 分钟粒度，每日 96 点） |
| 数据形态 | **月度典型曲线**（该月每日 96 点的代表值），**非逐日历史序列** |
| 有效总行数 | 50 月 × 96 点 = 4800 行 |

### 4.2 month_settle（月度结算电价）

| 属性 | 值 |
|---|---|
| 文件覆盖 | 2018-01 ~ 2026-12（108 个月，每月 1 个 JSON 文件） |
| **有效数据范围** | **2018-01 ~ 2026-12**（108 个月，全量有效） |
| 每月数据行数 | 23 行（2018-01~2022-10）/ 24 行（2022-11 起） |
| 数据形态 | **逐日分时结算电价**（每日一个分时点，一个月内逐日列出） |
| 有效总行数 | 2525 行 |

### 4.3 其余 5 个归档 API

| prefix | 月份数 | 总行数 | 数据形态 |
|---|---|---|---|
| `month_deal` | 108 | 216 | 月度成交汇总（每月 2 行） |
| `user_transaction` | 108 | 216 | 用户侧交易汇总（每月 2 行） |
| `year_trade_fit` | 108 | 216 | 年度拟合电价（每月 2 行） |
| `time_div_trend` | 108 | 432 | 分时电价趋势（每月 4 行） |
| `month_settle1` | 108 | 1073 | 月度结算电价 v1（dict 格式，含嵌套 data） |

---

## 5. 关键限制

1. **月度典型曲线，非逐日历史序列**: `spot_da` 和 `spot_rt` 的每月 96 行数据是该月各 15 分钟时段的**代表值/典型曲线**，而非该月每一天的实际逐日历史数据。因此**不能用于逐日价格波动分析或日级别回测**。

2. **字段语义推断不可作生产决策依据**: `record1` → `da_price_a`、`record2` → `da_price_b`、`rqRecord` → `rt_energy_demand`、`ssRecord` → `rt_energy_supply` 均为基于前端源码片段推断的语义化重命名，**无官方 API 文档支撑**。下游使用方应自行交叉验证字段含义后方可用于分析或建模。

3. **单位量纲未官方文档化**: `rt_energy_demand` 和 `rt_energy_supply` 的推断单位为**万 MWh**（基于前端 `value/1e5` 转"亿千瓦时"的逻辑），但**未经官方文档确认**。`load_mw` 列在 spot_rt 中直接复制 `rt_energy_demand` 值，列名与实际量纲不一致（列名含 `_mw` 但实际为万 MWh），**下游运算时请注意量纲差异**。

4. **`24:00` 时间点跨日边界**: `spot_da` 和 `spot_rt` 的 `endPointTime` 原始值中，每日第 96 个点为 `24:00`（非有效 ISO 8601 时间）。loader 在解析时会将 `24:00` 转换为次日 `00:00`，因此 DataFrame 中每日最后一行 `timestamp` 落在下一个自然日。这是预期行为，**不是数据错误**。

5. **`load_mw` 列对价格类 loader 为 NaN**: `spot_da` 和 `month_settle` 为纯价格数据，不含负荷信息，其 `load_mw` 列全部为 NaN。这是 `DataLoader` 抽象合约要求 `load_mw` 列必须存在的约定，**不是数据缺失**。

6. **空数据月份与有效范围不匹配**: `spot_da` / `spot_rt` 在 2018-01~2022-03 虽有 JSON 文件但 `data=[]`（仅含 `{"msg":"操作成功","code":200,"data":[]}` 的 wrapper 结构），2026-06~2026-12 同样无有效数据。**仅 2022-04~2026-05 有实际数据**，下游使用 `load_data(start, end)` 时超出此范围将返回空 DataFrame。

7. **非核心 API 不承诺 loader 接入**: 第 2.2 节列出的 10 个非核心 API 仅保留原始 JSON 文件，不实现 `DataLoader` 子类，不进入 `create_loader()` 工厂。这是 D-006 决策的范围控制，后续如有需求需单独评估。

---

## 6. 字段推断免责声明

本节第 3 节中所有标注为 **[inferred]** 的字段（`da_price_a`、`da_price_b`、`rt_energy_demand`、`rt_energy_supply`）均来自对前端 JavaScript 源码的逆向分析，**无官方 API 字段说明文档支撑**。推断依据包括：

- 前端页面中字段周围的汉字标签（如"均价(元/MWh)"）
- 前端对原始数值的换算逻辑（如 `value/1e5` 转亿千瓦时）
- 字段在 API 响应中的位置和上下文

**这些推断仅供内部数据探索使用，不可直接作为生产交易决策、学术发表或对外报告的字段语义依据。** 下游使用方应通过以下方式之一验证：

- 对比山西电力交易中心官方发布的结算单据
- 与同期其他公开数据源（如电力交易中心月报）交叉校验
- 联系平台运营方确认字段精确定义

---

## 7. 使用示例

以下示例展示如何通过 `create_loader()` 工厂函数加载三个核心数据集。所有 loader 返回标准 `DataFrame[timestamp, load_mw, ...]` 格式。

### 7.1 加载现货日前出清数据

```python
from ellectric.pipeline.data_loader import create_loader

loader = create_loader("shanxi_spot_da")
df = loader.load_data("2024-01", "2024-03")

# 预期列: timestamp, load_mw(NaN), da_price_a, da_price_b, province, source, granularity
# 预期行数: 3 月 × 96 点 = 288 行
print(df.columns.tolist())
print(df.shape)
```

### 7.2 加载现货实时出清数据

```python
from ellectric.pipeline.data_loader import create_loader

loader = create_loader("shanxi_spot_rt")
df = loader.load_data("2024-06", "2024-08")

# 预期列: timestamp, load_mw(=rt_energy_demand), rt_energy_demand, rt_energy_supply, province, source, granularity
# 注意: load_mw 实际承载万 MWh 数值，非 MW
print(df.columns.tolist())
print(df.shape)
```

### 7.3 加载月度结算电价数据

```python
from ellectric.pipeline.data_loader import create_loader

loader = create_loader("shanxi_month_settle")
df = loader.load_data("2023-01", "2023-12")

# 预期列: timestamp, load_mw(NaN), time_point, settle_day_price, settle_rt_price, province, source, granularity
# 预期行数: 12 月 × 24 点 ≈ 288 行
print(df.columns.tolist())
print(df.shape)
```

---

## 参考

- 蓝图: `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md`
- 决策: `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/decisions.md` (D-002@v1, D-003@v1, D-006@v1)
- 需求: `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/requirements.md` (FR-001, FR-002, NFR-005)
- 数据全景: `ellectric/data/raw/shanxi/_full_summary.json`
- 项目规范: `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md`