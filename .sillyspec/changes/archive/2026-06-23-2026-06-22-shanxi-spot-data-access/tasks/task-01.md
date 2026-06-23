---
id: task-01
title: 写 data/raw/shanxi/README.md 数据资产说明
priority: P0
depends_on: []
blocks: []
requirement_ids: [FR-001, FR-002, NFR-005]
decision_ids: [D-002@v1, D-003@v1, D-006@v1]
author: lmr
created_at: 2026-06-23T15:10:00+08:00
allowed_paths:
  - ellectric/data/raw/shanxi/README.md
---

# task-01: 写 data/raw/shanxi/README.md 数据资产说明

## 修改文件 (必填)

- `ellectric/data/raw/shanxi/README.md` (新增, 纯 Markdown 文档)

## 覆盖来源

- Requirements: FR-001 (原始数据归档), FR-002 (README 数据资产说明), NFR-005 (字段推断免责)
- Decisions: D-002@v1 (record1/record2 → da_price_a/da_price_b 推断), D-003@v1 (rqRecord/ssRecord 重命名 + load_mw 映射), D-006@v1 (仅 3 个核心 API 接入, 其余归档)

## 实现要求

本任务为**纯文档任务**, 不涉及任何代码改动。产出 `ellectric/data/raw/shanxi/README.md` 一个文件, 内容必须涵盖以下 6 大块:

1. **数据源标识与采集方法**: 数据源域名 (`pxf-phbsx-shop.pmos.sx.sgcc.com.cn`), cookie 获取方式 (浏览器登录后从 DevTools 提取), 采集脚本路径 (位于 `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/` 下的勘探脚本; 实际执行时由人工脚本下载, 后续维护无需自动重跑), 文件命名约定 (`<prefix>_YYYY-MM.json`), 归档总文件数 (1947), 归档总大小 (~6.6 MB)。
2. **8 个数据查询 API 中英对照表**: 8 行表格, 列含 `prefix / API 路径 (queryXxx) / 中文名 / 接入状态 (loader|归档) / 月份数 / 总行数 / fmt`。
3. **三个核心 API 字段映射详表**: 每个 API 一张子表, 列含 `原始 JSON 字段 / DataFrame 列 / 类型 / 推断含义 / 置信度 (确定|高频|推断)`。**所有 inferred 字段必须打 `[inferred]` 角标并附风险说明**。
4. **三个核心 API 有效时间范围 + 数据形态说明**: spot_da/spot_rt 2022-04~2026-05 (50 月 × 96 点 ≈ 4800 行, 月度典型曲线非逐日历史), month_settle 2018-01~2026-12 (108 月 × 23-24 点 ≈ 2525 行, 逐日分时)。
5. **关键限制**: 列出至少 5 条已知限制(月度典型曲线非逐日序列、字段语义推断不可作生产决策依据、单位量纲未官方文档化、`24:00` 时间点跨日边界处理、`load_mw` 列对价格类 loader 为 NaN)。
6. **使用示例**: 用 `create_loader("shanxi_spot_da") / ("shanxi_spot_rt") / ("shanxi_month_settle")` 的 3 段最小 Python 示例代码块, 展示 `load_data(start, end)` 调用和返回 DataFrame 的预期列。

文档语言: 简体中文为主; API 路径名、字段名、DataFrame 列名保留英文原文。文档风格参考项目 `README.md` (中英双语 docstring 风格), 但作为纯数据资产说明书无需复杂 ASCII 图。

## 覆盖来源原文 (供参考, execute 子代理无需再翻 design/decisions)

### 决策 D-002@v1 (record1/record2 重命名)

`record1` → `da_price_a` (推断为日前出清价 A, 元/MWh, **inferred**); `record2` → `da_price_b` (推断为日前出清价 B, 元/MWh, **inferred**)。前端源码周围出现"均价(元/MWh)"但未明确两个 record 字段精确对应"价区"还是其他维度。实际可能是"挂牌价 vs 加权价"或其他维度; README 必须标注 `inferred` 并要求下游使用方自行交叉验证。

### 决策 D-003@v1 (rqRecord/ssRecord 重命名 + load_mw 映射)

`rqRecord` → `rt_energy_demand` (推断为实时需求量, 万 MWh, **inferred**); `ssRecord` → `rt_energy_supply` (推断为实时供应量, 万 MWh, **inferred**); 在 `ShanxiSpotRtLoader` 中 `load_mw` 列直接复制 `rt_energy_demand` 值 (作为等效负荷)。前端源码做 `value/1e5` 转成"亿千瓦时"暗示电量量级; `DataLoader` 抽象合约要求 `load_mw` 列存在; `rqRecord` 是"需求"侧最接近"负荷"。**风险**: 单位实际为万 MWh 不是 MW, 下游使用时需注意量纲。

### 决策 D-006@v1 (仅 3 API 接入, 其余归档)

仅接入 `spot_da` / `spot_rt` / `month_settle` 三个 API 为 loader 子类; 其余 5 个有效 API (`month_deal` / `user_transaction` / `year_trade_fit` / `time_div_trend` / `month_settle1`) 只保留下载数据, 不实现 loader; 11 个其余 API (`dynamic` / `policy` / `market_list` 等) 保存原始 JSON 不进入数据层。README 必须明确标注 8 个核心 API + 11 个非核心 API 的接入状态。

## 接口定义 (代码类任务必填, task-01 README 类填字段表)

### 文档结构 (Markdown 标题层级)

```
# 山西电力现货数据资产 (Shanxi Spot Market Data Assets)

## 1. 数据源
   - 1.1 域名与认证
   - 1.2 采集方法
   - 1.3 文件命名约定

## 2. API 接入清单 (8 行表格)

## 3. 字段映射详表
   - 3.1 spot_da (querySpotMarketClearing)
   - 3.2 spot_rt (queryRealTimeSpotMarketClearing)
   - 3.3 month_settle (queryUserMonthSettlementPrice)

## 4. 有效时间范围与数据形态

## 5. 关键限制 (≥5 条)

## 6. 使用示例
```

### 第 2 节: API 接入清单表 (必须完整 8 行 + 11 行非核心归档表)

| prefix | API 路径 | 中文名 | 接入状态 | 月份数 | 总行数 | fmt |
|---|---|---|---|---|---|---|
| `spot_da` | `querySpotMarketClearing` | 现货日前出清 | **loader** | 50 (2022-04~2026-05) | 4800 | dict |
| `spot_rt` | `queryRealTimeSpotMarketClearing` | 现货实时出清 | **loader** | 50 (2022-04~2026-05) | 4800 | dict |
| `month_settle` | `queryUserMonthSettlementPrice` | 月度结算电价 | **loader** | 108 (2018-01~2026-12) | 2525 | list |
| `month_deal` | `queryMonthDeal` | 月度成交 | 归档 | 108 | 216 | list |
| `user_transaction` | `queryUserTransaction` | 用户侧交易 | 归档 | 108 | 216 | list |
| `year_trade_fit` | `queryYearTradeFittingPrice` | 年度拟合电价 | 归档 | 108 | 216 | list |
| `time_div_trend` | `queryTimeDivisionPriceTrend` | 分时电价趋势 | 归档 | 108 | 432 | list |
| `month_settle1` | `queryUserMonthSettlementPrice1` | 月度结算电价(v1) | 归档 | 108 | 1073 | dict |

其余 11 个 API (dynamic / market_list / market_users / month_market / no_time_trend / policy / price_trend / public_info / retail_prob / retail_settle 等) 列表 + 一行说明 "非交易数据, 仅原始 JSON 保留"。

### 第 3 节: 字段映射详表 (3 张子表)

#### 3.1 spot_da

| 原始 JSON | DataFrame 列 | 类型 | 推断含义 | 置信度 |
|---|---|---|---|---|
| `endPointTime` | `timestamp` | datetime64[ns, UTC] | 15min 时段结束时间 (00:15~24:00) | 确定 |
| `record1` | `da_price_a` | float64 | 日前出清价 A (元/MWh) | **inferred** |
| `record2` | `da_price_b` | float64 | 日前出清价 B (元/MWh) | **inferred** |
| (注入) | `load_mw` | float64 | NaN — 价格数据无负荷等效 | 约定 |
| (注入) | `province` | str | `"shanxi"` | 确定 |
| (注入) | `source` | str | `"pxf-phbsx-shop"` | 确定 |
| (注入) | `granularity` | str | `"15min"` | 确定 |

#### 3.2 spot_rt

| 原始 JSON | DataFrame 列 | 类型 | 推断含义 | 置信度 |
|---|---|---|---|---|
| `dataTime` | `timestamp` | datetime64[ns, UTC] | 15min 时段 (00:15~24:00) | 确定 |
| `rqRecord` | `rt_energy_demand` | float64 | 实时需求量 (万 MWh) | **inferred** |
| `ssRecord` | `rt_energy_supply` | float64 | 实时供应量 (万 MWh) | **inferred** |
| (映射) | `load_mw` | float64 | = `rt_energy_demand` (等效负荷) | 约定 |
| (注入) | `province` / `source` / `granularity` | str | `"shanxi"` / `"pxf-phbsx-shop"` / `"15min"` | 确定 |

#### 3.3 month_settle

| 原始 JSON | DataFrame 列 | 类型 | 含义 | 置信度 |
|---|---|---|---|---|
| `dataTime` | `timestamp` | datetime64[ns, UTC] | 日期 (YYYY-MM-DD) | 确定 |
| `point` | `time_point` | int64 | 每日分时点编号 (0~23) | 确定 |
| `dayPrice` | `settle_day_price` | float64 | 月度日前统一结算点电价 (元/MWh) | 高频 |
| `realTimePrice` | `settle_rt_price` | float64 | 月度实时统一结算点电价 (元/MWh) | 高频 |
| (注入) | `load_mw` | float64 | NaN | 约定 |
| (注入) | `province` / `source` / `granularity` | str | `"shanxi"` / `"pxf-phbsx-shop"` / `"daily-point"` | 确定 |

## 边界处理 (至少 5 条)

1. **`inferred` 字段必须打角标**: `record1/record2/rqRecord/ssRecord` 任一表格行内涉及推断含义的, 在"推断含义"列必须显式以 `**inferred**` 或 `[inferred]` 标注; 文档第 3 节末尾必须有一段独立 "**字段推断免责声明**", 说明前端源码无明确语义文档, 下游使用方应自行交叉验证。
2. **空文件/无数据月份必须说明**: spot_da/spot_rt 在 2022-03 及之前虽有文件但 `data=[]` (1 行 wrapper), 2026-06~12 暂无数据 — 文档第 4 节有效范围段落必须显式写出"有效范围", 防止下游误把空数据当成"loader 坏了"。
3. **量纲单位标注不可省略**: `rt_energy_demand` 单位是 **万 MWh** (非 MW), `load_mw` 列名虽然叫 `_mw` 但对 spot_rt 实际承载万 MWh 数值, 文档第 3.2 节字段表 + 第 5 节限制必须各出现一次 "单位为万 MWh, 不是 MW, 下游运算请注意量纲" 的警示。
4. **`24:00` 时间点边界**: spot_da/spot_rt 的 `endPointTime` 第 96 个点是 `24:00`, 不是有效 ISO 时间 — 文档第 5 节必须列出"`24:00` 跨日边界由 loader 转为次日 `00:00`"的处理约定, 让读 README 的人理解为何最后一行 `timestamp` 落在下个自然日。
5. **README 自身不下载数据/不修改代码**: 本文档只描述事实, 不含任何 `wget` / `curl` / `python download.py` 指令; 采集脚本路径仅作引用不嵌入命令, 防止读者误把 README 当成可执行 runbook。
6. **不擅自重命名 11 个非核心 API**: 第 2 节非核心 API 列表保留原 prefix 不重命名, 不为它们设计字段映射, 不承诺 loader 接入 (D-006 范围控制)。
7. **不引用未确认决策**: 仅引用 decisions.md 中 active 状态的 D-002@v1 / D-003@v1 / D-006@v1, 不提及未来变更 (`gd-spot-data-access` / `realtime-data-pipeline` 等)。

## 非目标 (本任务不做的事)

- ❌ 不实现任何 Python 代码 (`shanxi_loader.py` 由 task-02~05 负责)
- ❌ 不修改 `data_loader.py` 的工厂 (由 task-06 负责)
- ❌ 不写验证脚本 (由 task-07 负责)
- ❌ 不写 cookie/采集脚本的具体登录步骤 (安全敏感, 仅指向已有勘探脚本路径)
- ❌ 不评估字段推断是否正确 (NFR-005 明确要求下游自行验证, README 只标置信度)
- ❌ 不画 Mermaid/ASCII 大图 (本任务为字段说明书, 文字 + 表格即可)
- ❌ 不重新下载或校验 1947 个 JSON 文件 (T-001 已完成, README 只描述事实)

## 参考

- `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` — 第 III 节字段映射, 第 IV 节工厂扩展, 第 V 节时间限制 (核心引用)
- `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/decisions.md` — D-002@v1 / D-003@v1 / D-006@v1
- `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/requirements.md` — FR-001 / FR-002 / NFR-005
- `/mnt/e/Electric/ellectric/data/raw/shanxi/_full_summary.json` — 8 个核心 + 11 个非核心 API 的真实月份覆盖与行数 (照抄即可)
- `/mnt/e/Electric/ellectric/data/raw/shanxi/spot_da_2024-01.json` — record1/record2 JSON 真实样本
- `/mnt/e/Electric/ellectric/data/raw/shanxi/spot_rt_2024-01.json` — rqRecord/ssRecord JSON 真实样本
- `/mnt/e/Electric/ellectric/data/raw/shanxi/month_settle_2024-01.json` — dayPrice/realTimePrice JSON 真实样本
- `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md` — 文档风格 (中英双语标题、表格、分隔符)
- `/mnt/e/Electric/ellectric/pipeline/data_loader.py` — 参考 `OWIDChinaLoader` / `ChineseDataLoader` 模块级 docstring 写作风格, 但本任务无需照搬代码注释规范 (这是纯 README)

## TDD 步骤 (代码类任务, 文档类任务跳过)

本任务为纯文档任务, 跳过 TDD。改用以下文档撰写流程:

1. 先列大纲 (6 大节标题), 自查覆盖 FR-001/FR-002/NFR-005 + D-002/D-003/D-006
2. 第 2 节先填 API 接入清单表 (照抄 `_full_summary.json` 的 path/total)
3. 第 3 节填字段映射表 (3 张子表, `inferred` 角标到位)
4. 第 4 节填有效时间范围 (照抄 design.md 第 V 节)
5. 第 5 节列 ≥5 条限制 (覆盖边界处理 1~7 条)
6. 第 6 节写 3 段使用示例代码块
7. 自检: 关键词 `inferred` 出现 ≥4 次, `万 MWh` 出现 ≥2 次, `24:00` 出现 ≥1 次

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | 文件存在性: `test -f /mnt/e/Electric/ellectric/data/raw/shanxi/README.md && echo OK` | 输出 `OK` |
| AC-02 | 文档长度: `wc -l ellectric/data/raw/shanxi/README.md` | 行数 ≥ 120 行 |
| AC-03 | API 接入清单完整性: `grep -E '^\| .*(spot_da\|spot_rt\|month_settle\|month_deal\|user_transaction\|year_trade_fit\|time_div_trend\|month_settle1)' ellectric/data/raw/shanxi/README.md \| wc -l` | 至少 8 行 (8 个核心 API 各一行表格) |
| AC-04 | 字段推断免责标注: `grep -ic inferred ellectric/data/raw/shanxi/README.md` | 出现次数 ≥ 4 (record1/record2/rqRecord/ssRecord 各一次) |
| AC-05 | 量纲警示: `grep -c '万 MWh' ellectric/data/raw/shanxi/README.md` | 出现次数 ≥ 2 |
| AC-06 | 24:00 边界说明: `grep -c '24:00' ellectric/data/raw/shanxi/README.md` | 出现次数 ≥ 1 |
| AC-07 | 6 个一级标题章节齐全: `grep -cE '^## [0-9]\. ' ellectric/data/raw/shanxi/README.md` | 至少 6 个 (节 1~6) |
| AC-08 | 关键字段名全部出现: `grep -E '(da_price_a\|da_price_b\|rt_energy_demand\|rt_energy_supply\|settle_day_price\|settle_rt_price\|time_point)' ellectric/data/raw/shanxi/README.md \| wc -l` | 至少 7 行(7 个新字段名各出现 ≥1 行) |
| AC-09 | 不含 shell 下载命令(README 不应是 runbook): `grep -cE '(wget\|curl -X\|python download)' ellectric/data/raw/shanxi/README.md` | 输出 0 |
| AC-10 | `create_loader` 三个 source 示例齐全: `grep -E 'create_loader\("shanxi_(spot_da\|spot_rt\|month_settle)"\)' ellectric/data/raw/shanxi/README.md \| wc -l` | 至少 3 行 |
