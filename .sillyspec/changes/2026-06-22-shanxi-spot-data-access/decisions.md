---
author: lmr
created_at: 2026-06-23T14:52:56+08:00
---

# Decisions — 山西现货数据接入

## D-001@v1 — 采用 Loader 三子类继承架构（方案B）

**决策**：新增 `ShanxiBaseLoader(DataLoader)` 抽象基类 + 三个具体子类（`ShanxiSpotDaLoader`/`ShanxiSpotRtLoader`/`ShanxiMonthSettleLoader`）。

**备选**：
- 方案A：单一 loader + data_type dispatch（被拒：内部分支臃肿，违反 SRP）
- 方案C：模块级函数（被拒：破坏现有 OOP 工厂模式一致性）

**理由**：
- 与现有 `OWIDChinaLoader` / `ChineseDataLoader` 双子类模式一致
- 三种数据 schema 差异大（15min 现货价 vs 实时电量 vs 逐日结算价），独立子类避免污染
- 后续扩展剩 4 个有效 API 时零负担新增子类

**覆盖**：FR-003, FR-004, FR-005, FR-006

## D-002@v1 — record1/record2 重命名 da_price_a/da_price_b

**决策**：将 `record1`/`record2` 重命名为 `da_price_a`/`da_price_b`。

**置信度**：推断（前端源码周围出现"均价(元/MWh)"但未明确两个 record 字段精确对应"价区"还是其他维度）。

**风险**：实际可能是"挂牌价 vs 加权价"或其他维度。

**缓解**：README 标注 `inferred`，要求下游使用方自行交叉验证。

**覆盖**：FR-004, NFR-005

## D-003@v1 — rqRecord/ssRecord 重命名 + load_mw 映射

**决策**：
- `rqRecord` → `rt_energy_demand`（推断为实时需求量）
- `ssRecord` → `rt_energy_supply`（推断为实时供应量）
- 在 `ShanxiSpotRtLoader` 中，`load_mw` 列直接复制 `rt_energy_demand` 值（作为等效负荷）

**理由**：
- 前端源码做 `value/1e5` 转成"亿千瓦时"，说明它是电量量级（万 MWh）
- `DataLoader` 抽象合约要求 `load_mw` 列存在
- `rqRecord` 是"需求"侧，最接近"负荷"概念

**风险**：`rt_energy_demand` 单位实际为万 MWh，不是 MW；下游使用时需注意量纲。

**覆盖**：FR-005, NFR-005

## D-004@v1 — create_loader 使用延迟导入

**决策**：在 `create_loader()` 工厂的 shanxi 分支中使用函数内 `from ellectric.pipeline.shanxi_loader import ...`，而不是顶层 import。

**理由**：
- 与现有 EmberLoader 的延迟导入模式一致
- 减少 import 时的副作用（即使用户不用 shanxi，也不强制加载）
- 符合 CLAUDE.md "可选依赖防护" 原则

**覆盖**：FR-007

## D-005@v1 — 拆独立 shanxi_loader.py 文件

**决策**：所有 3 个 loader 类放在独立文件 `ellectric/pipeline/shanxi_loader.py`，不放进 `data_loader.py`。

**理由**：
- `data_loader.py` 已 500+ 行，再加 3 个 loader 会膨胀到 800+ 行
- 模块职责更清晰：`data_loader.py` 管核心抽象 + 通用 loader，`shanxi_loader.py` 管省级特化
- 后续加广东等省份 loader 走相同模式（独立文件）

**覆盖**：NFR-004

## D-006@v1 — 仅 3 个核心 API 接入，其余归档

**决策**：本变更只接入 `spot_da`/`spot_rt`/`month_settle` 三个 API 为 loader 子类。其余 5 个有效 API（month_deal/user_transaction/year_trade_fit/time_div_trend/month_settle1）只保留下载数据，不实现 loader。

**理由**：
- YAGNI：当前 Electric 用例不需要中长期成交/分时浮动等
- 按需扩展：后续变更需要时新增子类零成本
- 范围控制：避免一次变更代码量过大

**风险**：未来需要时还要重写。

**缓解**：抽象基类 `ShanxiBaseLoader` 已可复用，新增子类只需实现 `_standardize`。

**覆盖**：proposal "不在范围内"