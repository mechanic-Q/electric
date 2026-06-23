---
author: lmr
created_at: 2026-06-23T14:49:40+08:00
---

# 山西现货数据接入 — 设计文档

## 背景

当前 Electric 项目基于 OWID GitHub 公开数据集（年级数据→日均 MW）和本地示例 parquet 文件运行。代码硬编码为小时级系统（24 点/天、168 点/周、`freq="h"`），省份粒度为中国整体，无法反映省级现货市场的真实 15 分钟级波动。

2026-06-22 电力数据源穷举调研（`wiki/sources/electric-data-survey-2026-06-22`）确认：山西电力交易中心（`pmos.sx.sgcc.com.cn`）是唯二正式运行 15 分钟级现货市场的省份之一，其零售商城子域名（`pxf-phbsx-shop`）提供 8 项公开数据查询 API，无需企业认证即可访问。

本次变更是"对标图迹三阶段升级"的第一阶段（数据准备级），解决>从零到有接入真实省级现货数据的问题。

## 设计目标

1. 全量下载山西零售商城公开数据 API 至原始 JSON 归档
2. 实现 `ShanxiBaseLoader` 抽象基类 + 3 个 loader 子类，符合现有 DataLoader ABC + 工厂模式
3. 字段语义化重命名，标注推断置信度
4. 产出 `data/raw/shanxi/README.md` 完整说明
5. **不修改现有 pipeline 代码**（特征工程、预测器、RL 环境、API/CLI 全不动）

## 非目标

- ❌ 不修改 `trading_env.py`、`features.py`、`forecaster.py` 等现有 pipeline 代码
- ❌ 不做小时级聚合（留给后续变更）
- ❌ 不做 24/168 硬编码参数化（留给 `time-resolution-param` 变更）
- ❌ 不做准实时调度管道（留给 `realtime-data-pipeline` 变更）
- ❌ 不接入广东数据（留给 `gd-spot-data-access` 变更）
- ❌ 不做模型训练或回测
- ❌ 不接入 FastAPI/CLI/LLM

## 拆分判断

本变更按 SillySpec 方案 B 实现：不拆分单个变更为多子变更。三个 loader 子类共享同一抽象基类和文件目录，同一 `create_loader()` 工厂，适合在一个 change 中完成。

后续路线（独立变更）：

```
shanxi-spot-data-access (当前) → time-resolution-param → gd-spot-data-access → data-schema-expand → realtime-data-pipeline
```

## 决策与方案选择 (Decisions)

本节列出本变更的核心架构决策。完整决策台账见 `decisions.md`。

### D-001@v1：采用 Loader 三子类继承架构（方案B）

**决策**：新增 `ShanxiBaseLoader(DataLoader)` 抽象基类 + 三个具体子类（`ShanxiSpotDaLoader` / `ShanxiSpotRtLoader` / `ShanxiMonthSettleLoader`）。

**备选**：
- 方案A：单一 loader + `data_type` dispatch（被拒：内部分支臃肿，违反 SRP）
- 方案C：模块级函数（被拒：破坏现有 OOP 工厂模式一致性）

**理由**：
- 与现有 `OWIDChinaLoader` / `ChineseDataLoader` 双子类模式一致
- 三种数据 schema 差异大（15min 现货价 vs 实时电量 vs 逐日结算价），独立子类避免污染
- 后续扩展剩 4 个有效 API 时零负担新增子类

**覆盖**：FR-003, FR-004, FR-005, FR-006

### D-002@v1：record1/record2 重命名 da_price_a/da_price_b

**决策**：将 `record1`/`record2` 重命名为 `da_price_a`/`da_price_b`。

**置信度**：推断（前端源码周围出现"均价(元/MWh)"但未明确两个 record 字段精确对应"价区"还是其他维度）。

**风险与缓解**：实际可能是"挂牌价 vs 加权价"或其他维度；README 标注 `inferred`，要求下游使用方自行交叉验证。

### D-003@v1：rqRecord/ssRecord 重命名 + load_mw 映射

**决策**：
- `rqRecord` → `rt_energy_demand`（推断为实时需求量）
- `ssRecord` → `rt_energy_supply`（推断为实时供应量）
- 在 `ShanxiSpotRtLoader` 中，`load_mw` 列直接复制 `rt_energy_demand` 值（作为等效负荷）

**理由**：前端源码做 `value/1e5` 转成"亿千瓦时"，说明它是电量量级（万 MWh）；`DataLoader` 抽象合约要求 `load_mw` 列存在；`rqRecord` 是"需求"侧，最接近"负荷"概念。

**风险**：单位实际为万 MWh 不是 MW，下游使用时需注意量纲。

### D-004@v1：create_loader 使用延迟导入

**决策**：在 `create_loader()` 工厂的 shanxi 分支中使用函数内 `from ellectric.pipeline.shanxi_loader import ...`，而不是顶层 import。

**理由**：与现有 EmberLoader 的延迟导入模式一致；减少 import 时的副作用；符合 CLAUDE.md "可选依赖防护" 原则。

### D-005@v1：拆独立 shanxi_loader.py 文件

**决策**：所有 3 个 loader 类放在独立文件 `ellectric/pipeline/shanxi_loader.py`，不放进 `data_loader.py`。

**理由**：`data_loader.py` 已 500+ 行，再加 3 个 loader 会膨胀；模块职责更清晰；后续加广东等省份 loader 走相同模式。

### D-006@v1：仅 3 个核心 API 接入，其余归档

**决策**：本变更只接入 `spot_da` / `spot_rt` / `month_settle` 三个 API 为 loader 子类。其余 5 个有效 API（month_deal/user_transaction/year_trade_fit/time_div_trend/month_settle1）只保留下载数据，不实现 loader。

**理由**：YAGNI；范围控制避免一次变更代码量过大；抽象基类已可复用，后续按需扩展零成本。

## 总体方案

### I. 数据采集（已完成）

| API | 范围 | 粒度 | 月份数 | 总行数 | 状态 |
|---|---|---|---|---|---|
| `querySpotMarketClearing` (spot_da) | 2022-04 ~ 2026-05 | 15min × 24h = 96 点/月 | 50 | 4800 | ✅ |
| `queryRealTimeSpotMarketClearing` (spot_rt) | 2022-04 ~ 2026-05 | 15min × 24h = 96 点/月 | 50 | 4800 | ✅ |
| `queryUserMonthSettlementPrice` (month_settle) | 2018-01 ~ 2026-12 | 逐日分时 23-24 点/月 | 108 | 2525 | ✅ |
| `queryMonthDeal` (month_deal) | 2018-01 ~ 2026-12 | 2 行/月(概要) | 108 | 216 | 归档 |
| `queryUserTransaction` (user_transaction) | 2018-01 ~ 2026-12 | 2 行/月(概要) | 108 | 216 | 归档 |
| `queryYearTradeFittingPrice` (year_trade_fit) | 2018-01 ~ 2026-12 | 2 行/月 | 108 | 216 | 归档 |
| `queryTimeDivisionPriceTrend` (time_div_trend) | 2018-01 ~ 2026-12 | 4 行/月 | 108 | 432 | 归档 |
| 其余 11 个 API (dynamic/policy 等) | — | 空/非交易数据 | — | — | 保存原始 |

### II. Loader 架构

```ascii
ellectric/pipeline/__init__.py
ellectric/pipeline/data_loader.py          ← 修改：新增 ShanxiBaseLoader + 3 子类 + 工厂扩展
ellectric/data/raw/shanxi/README.md         ← 新增：数据资产说明
ellectric/data/raw/shanxi/                  ← 原始 JSON 数据（gitignored）
├── spot_da_YYYY-MM.json                    (50 文件)
├── spot_rt_YYYY-MM.json                    (50 文件)
├── month_settle_YYYY-MM.json               (108 文件)
├── month_settle_YYYY-MM_dict.json          (66 文件，空 wrapper)
├── month_deal_YYYY-MM.json                 (108 文件，归档)
├── ... (其余 API 文件)
├── _full_summary.json
└── _summary.json (已移除或覆盖)
```

类层次：

```ascii
DataLoader (ABC) — extant in data_loader.py
├── OWIDChinaLoader        — 不变
├── ChineseDataLoader      — 不变
├── ShanxiBaseLoader       — 新增抽象基类
│   ├── ShanxiSpotDaLoader      — 新增
│   ├── ShanxiSpotRtLoader      — 新增
│   └── ShanxiMonthSettleLoader — 新增
```

`ShanxiBaseLoader` 职责：
- 扫描 `data/raw/shanxi/` 下匹配前缀的 JSON 文件
- 解析 `YYYY-MM` 从文件名中提取月份
- 支持 `load_data(start, end)` 中 start/end 的年月筛选
- 处理 `24:00` 时间点（跨日边界 → 次日 00:00）
- UTC 标准化
- 文件缺失记录警告不报错

### III. 字段映射

#### spot_da

| 原始 JSON | DataFrame 列 | 类型 | 推断含义 | 置信度 |
|---|---|---|---|---|
| `endPointTime` | `timestamp` | datetime64[ns, UTC] | 15min 时段结束时间 | 确定 |
| `record1` | `da_price_a` | float64 | 日前出清价(价区A)，元/MWh | 推断 |
| `record2` | `da_price_b` | float64 | 日前出清价(价区B)，元/MWh | 推断 |

#### spot_rt

| 原始 JSON | DataFrame 列 | 类型 | 推断含义 | 置信度 |
|---|---|---|---|---|
| `dataTime` | `timestamp` | datetime64[ns, UTC] | 15min 时段 | 确定 |
| `rqRecord` | `rt_energy_demand` | float64 | 实时需求量/日前申报，万 MWh | 推断 |
| `ssRecord` | `rt_energy_supply` | float64 | 实时供应量/出清量，万 MWh | 推断 |

#### month_settle

| 原始 JSON | DataFrame 列 | 类型 | 含义 | 置信度 |
|---|---|---|---|---|
| `dataTime` | `timestamp` | datetime64[ns, UTC] | 日期 | 确定 |
| `point` | `time_point` | int64 | 每日分时点编号 | 确定 |
| `dayPrice` | `settle_day_price` | float64 | 月度一中日统一结算点电价 | 高频 |
| `realTimePrice` | `settle_rt_price` | float64 | 月度实时统一点结算价 | 高频 |

#### 基础列（三合一）

所有 loader 额外注入：

| 列名 | 类型 | 值 |
|---|---|---|
| `province` | str | `"shanxi"` |
| `source` | str | `"pxf-phbsx-shop"` |
| `granularity` | str | `"15min"` / `"daily-point"` |

#### `load_mw` 合约说明

`DataLoader` 抽象基类合约要求返回包含 `load_mw` 列。由于山西现货数据含有电量/负荷类数值（spot_rt 的 `rt_energy_demand`/`rt_energy_supply`，万 MWh 量级可换算为 MW 或等效负荷），处理方式：

- `ShanxiSpotRtLoader`：`rt_energy_demand` 同步写入 `load_mw`（作为"等效负荷"）
- `ShanxiSpotDaLoader`：纯价格数据，`load_mw` 置 NaN（价格类数据无负荷等效）
- `ShanxiMonthSettleLoader`：纯价格数据，`load_mw` 置 NaN

此举满足 `DataLoader` 接口合约的同时，不影响下游处理（NaN 可忽略）。

### IV. 工厂扩展

`create_loader()` 新增三个 source key：

| source key | loader 类 |
|---|---|
| `"shanxi_spot_da"` | `ShanxiSpotDaLoader` |
| `"shanxi_spot_rt"` | `ShanxiSpotRtLoader` |
| `"shanxi_month_settle"` | `ShanxiMonthSettleLoader` |

### V. 时间限制

- spot_da/spot_rt 有效范围为 **2022-04 ~ 2026-05**
- 2022-04 之前文件存在但 data=[]（API 无数据）
- 2026-06 暂无数据（月内未发布）
- 数据是**月度 96 点典型曲线**，不是逐日 96 点历史序列
- month_settle 有效范围为 **2018-01 ~ 2026-12**（108 个月全覆盖）

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | ellectric/data/raw/shanxi/README.md | 数据资产说明 |
| 新增 | ellectric/pipeline/shanxi_loader.py | 新增 ShanxiBaseLoader + 3 子类（独立文件，避免污染 data_loader.py） |
| 修改 | ellectric/pipeline/data_loader.py | create_loader 扩展 3 个 source（延迟导入 shanxi_loader） |
| 新增 | ellectric/data/raw/shanxi/ | 原始 JSON 数据已下载（1947 文件，6.6 MB） |

## 接口定义

### ShanxiBaseLoader

```python
class ShanxiBaseLoader(DataLoader):
    _metadata_source = "shanxi-pxf-phbsx-shop"  # 子类可覆盖

    def __init__(self, data_prefix: str, data_dir: str | None = None):
        self.data_prefix = data_prefix
        self.data_dir = Path(data_dir or "ellectric/data/raw/shanxi")
        self._metadata_version = f"{data_prefix}/local-json"

    def load_data(self, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        """扫描匹配前缀的 JSON 文件，按月份筛选，调用 _standardize 拼接结果。"""

    @abstractmethod
    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        """子类实现：将原始 records 转为标准化 DataFrame。"""

    def _make_timestamp(self, date_str: str, time_str: str) -> pd.Timestamp:
        """处理 24:00 → 次日 00:00 + UTC 标准化。"""
```

### 子类

```python
class ShanxiSpotDaLoader(ShanxiBaseLoader):
    def __init__(self, data_dir: str = None)
        super().__init__(data_prefix="spot_da", data_dir=data_dir)
    def _standardize(self, records) -> pd.DataFrame
        # record1 → da_price_a, record2 → da_price_b

class ShanxiSpotRtLoader(ShanxiBaseLoader):
    def __init__(self, data_dir: str = None)
        super().__init__(data_prefix="spot_rt", data_dir=data_dir)
    def _standardize(self, records) -> pd.DataFrame
        # rqRecord → rt_energy_demand, ssRecord → rt_energy_supply

class ShanxiMonthSettleLoader(ShanxiBaseLoader):
    def __init__(self, data_dir: str = None)
        super().__init__(data_prefix="month_settle", data_dir=data_dir)
    def _standardize(self, records) -> pd.DataFrame
        # dayPrice → settle_day_price, realTimePrice → settle_rt_price
```

### 工厂扩展

`create_loader()` 新增分支，采用延迟导入模式（与已有 EmberLoader 一致）：

```python
# data_loader.py 新增
elif source == "shanxi_spot_da":
    from ellectric.pipeline.shanxi_loader import ShanxiSpotDaLoader
    return ShanxiSpotDaLoader(**kwargs)
elif source == "shanxi_spot_rt":
    from ellectric.pipeline.shanxi_loader import ShanxiSpotRtLoader
    return ShanxiSpotRtLoader(**kwargs)
elif source == "shanxi_month_settle":
    from ellectric.pipeline.shanxi_loader import ShanxiMonthSettleLoader
    return ShanxiMonthSettleLoader(**kwargs)
```

### 无生命周期契约

本变更不涉及 `session / lease / agent_run / daemon / lifecycle / state transition / complete / end / claim / heartbeat` 等关键词。不产生生命周期契约表。

## 验收标准

1. ✅ `data/raw/shanxi/README.md` 存在，包含 API 说明、字段映射、有效范围、限制
2. ✅ `create_loader("shanxi_spot_da").load_data(start="2022-04", end="2026-05")` 返回 DataFrame
3. ✅ `create_loader("shanxi_spot_rt").load_data(start="2022-04", end="2026-05")` 同上
4. ✅ `create_loader("shanxi_month_settle").load_data()` 返回 2018-01~2026-12
5. ✅ 返回的 DataFrame 必含 `timestamp`(UTC)、`load_mw`、`province`、`source`、`granularity` 列
6. ✅ `loader.get_metadata()` 返回非空 dict 含 source/rows/start/end
7. ✅ 超出有效范围的 start/end 优雅降级（警告日志 + 空 DataFrame）
8. ✅ 不修改现有 OWIDChinaLoader / ChineseDataLoader / clean_data / FeatureEngineer / forecaster 等

## Design Grill 自审记录

- 矛盾1（已修复）：`load_mw` 合约 vs 价格/电量数据 → 增加 `load_mw` 映射规则
- 矛盾2（已修复）：`create_loader` 直接导入会污染顶层 → 改延迟导入（参照 EmberLoader）
- 矛盾3（已修复）：子类需设 `_metadata_source/_metadata_version` → 接口定义明确写入
- 矛盾4（已修复）：扩展放 `data_loader.py` 会增加 500+ 行 → 拆为独立 `shanxi_loader.py`
- 矛盾5（保留）：`record1/record2/rqRecord/ssRecord` 精确语义未渲染确认 → 标 `inferred` 在 README，下游使用方需自行验证