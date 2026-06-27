---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-05
title: 更新 scan 架构文档旧事实
priority: P1
depends_on:
  - task-03
blocks:
  - task-10
requirement_ids:
  - FR-005
decision_ids:
  - D-009@v1
allowed_paths:
  - docs/Ellectric/scan/ARCHITECTURE.md
---

# Task-05: 更新 scan 架构文档旧事实

## 修改文件

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `docs/Ellectric/scan/ARCHITECTURE.md` | 清理 OWID/hourly/Box(24)/gap=24/prepare_features tier='tier3' 等旧当前事实，加入 ShandongDataLoader、TimeConfig 15min、Tier4 weather、action shape TimeConfig 事实 |

只改 `ARCHITECTURE.md`。不改其他文件。

## 覆盖来源

| 需求/决策 | 覆盖方式 |
|---|---|
| FR-005 | ARCHITECTURE.md 中与当前代码冲突的旧事实被更新或标注为历史，不再作为当前架构事实 |
| D-009@v1 | scan 架构文档纳入文档对账；至少清理 TimeConfig、Data flow、TradingEnv action shape、phase data source 相关旧事实 |

## 实现要求

### 发现: ARCHITECTURE.md 中存在的旧事实

以下事实与当前项目状态（山东 15min MVP + TimeConfig 96点/日 + ShandongDataLoader + Tier4 weather）冲突，必须更新：

| # | 位置 (行号) | 旧事实 (当前文档) | 新事实 (目标) | 依据 |
|---|---|---|---|---|
| O1 | 数据流图 93-99 | OWID GitHub (urllib raw CSV) 作为主数据源；年级 TWh → 日均 MW | Shandong CSV 15min 作为 canonical 数据源；OWID 降级为历史参考 | 项目已完成 15min 数据迁移 |
| O2 | 模块职责 161 | DataLoader ABC → OWIDChinaLoader / ChineseDataLoader | DataLoader ABC → ShandongDataLoader (canonical) / OWIDChinaLoader (历史) / ChineseDataLoader (通用) | ShandongDataLoader 是 Phase 1-2 主线数据源 |
| O3 | 数据流 98 / 模块 163 | "年级 TWh → 日均 MW" 聚合逻辑 | 山东 CSV 直接加载 15min 点，无需年级→日均转换 | 数据源已切换 |
| O4 | 特征 195-196 | `prepare_features(df, tier="tier3")` (单数字符串签名)；最大 tier 为 Tier3 | `prepare_features(df, tiers=["tier1","tier2","tier3","tier4"])` (列表签名)；Tier4 weather 可选层 | D-006@v2, FR-001 |
| O5 | 特征 188-197 | FeatureEngineer 只有 add_tier1/add_tier2/add_tier3 | 新增 `add_tier4_weather_features()` 方法 | FR-001 |
| O6 | 预测 206, 211 | `TimeSeriesSplit(gap=24)` （小时级 24h gap） | `TimeSeriesSplit(gap=96)`（15min 24h=96点 gap） | TimeConfig.points_per_day=96 |
| O7 | 交易环境 236, 数据流 138 | `Box(0, 1, (24,))` （24h 动作空间） | `Box(0, 1, (TimeConfig.points_per_day,))` 即 `(96,)` （96 点动作空间） | TimeConfig 15min |
| O8 | 数据流 112 | clean_data → FeatureEngineer 单一链路 | clean_data → FeatureEngineer (Tier1-3) → 可选 Tier4 weather | FR-001 |
| O9 | 数据流 139 | `Box(0,1,(24,))` 动作空间 | `Box(0,1,(96,))` 或 `Box(0,1,(TimeConfig.points_per_day,))` | TimeConfig |
| O10 | 阶段边界 396 | Phase 1 数据源: "OWID GitHub" | Phase 1 数据源: "山东 15min CSV (canonical) + OWID GitHub (历史参考)" | 数据源已切换 |
| O11 | 阶段边界 394-395 | Phase 1 模块仅列 data_loader/cleaner/features/forecaster | 描述中体现 ShandongDataLoader 作为 data_loader 规范实现 | 模块职责已更新 |
| O12 | 关键设计模式 325 | "3-Tier 特征" 描述 | "3+Tier 特征" 或 "Tier 4 层渐进式" 描述（Tier4 weather 可选） | FR-001, D-006@v2 |

### 具体修改指引

#### 1. 更新 frontmatter `updated_at`

将 `updated_at: 2026-06-10T12:00:00+08:00` → `2026-06-27T19:12:11+08:00`

#### 2. 数据流图更新 (line ~93-150)

- 顶部数据源框: OWID GitHub 降级为副线/历史标注，Shandong CSV 15min 列为主数据源入口
- "年级 TWh → 日均 MW" 行改为 "直接加载 15min 时间序列"
- DataLoader 节点增加 ShandongDataLoader
- FeatureEngineer 节点标注 Tier1→Tier3 + 可选 Tier4 weather
- `Box(0,1,(24,))` 改为 `Box(0,1,(96,))` 或基于 TimeConfig 的描述
- `TimeSeriesSplit(gap=24)` 改为 `gap=96`

#### 3. 模块职责更新 (line ~156-293)

**data_loader.py (line 156-170):**
- OWIDChinaLoader 标注为历史参考（前缀 `⏳` 或说明文字）
- 新增 `ShandongDataLoader` — 加载山东 15min CSV，直接输出 `timestamp, load_mw, price_da, price_rt, wind_mw, solar_mw, tie_line_mw`，无需年级→日均转换
- `create_loader()` 的 source 参数扩展说明支持 `"shandong_csv"`、`"shandong_parquet"`、`"owid"`(历史)

**features.py (line 186-198):**
- `prepare_features()` 签名更新为 `(df, tiers=[...], weather_df=None, ...)` 列表形式
- 新增 `add_tier4_weather_features()` 方法说明
- `get_feature_columns("tier4")` 返回 Tier1-3 + 实际 weather columns
- `max_tier` 提及从 tier3 扩展到 tier4（可选层）

**forecaster.py (line 200-211):**
- `TimeSeriesSplit(gap=96)`——15min 数据 24h 窗口 = 96 个点
- 防泄漏说明中的 `gap=24` 更新为 `gap=96`

**trading_env.py (line 233-239):**
- `Box(0, 1, (96,))` 或 `Box(0, 1, (TimeConfig.points_per_day,))` 动作空间
- 时间相关说明从 "24h" 改为 `TimeConfig.points_per_day`

#### 4. 阶段边界表更新 (line ~394-399)

- Phase 1 数据源: "山东 15min CSV (canonical) + OWID GitHub (历史参考)"
- Phase 1 描述: 体现 ShandongDataLoader 规范实现

#### 5. 关键设计模式更新 (line ~320-331)

- "3-Tier 特征" → "4-Tier 渐进式特征"：Tier1 基础日历 → Tier2 节日/长滞后 → Tier3 滚动统计/循环编码 → Tier4 气象特征（可选，依赖网络或 cache）

#### 6. 文件布局检查 (line ~335-390)

无新文件变更影响文件布局，保持现状。

## 接口定义

N/A。文档更新任务无接口定义。变更仅涉及文本描述修正。

## 边界处理

1. **旧事实与新事实混存**: 更新时不得只改一处而遗漏镜像副本（如 `Box(24,)` 出现在数据流图 138 和模块职责 236 两处，必须全部更新）
2. **stage phase 表与模块职责不一致**: 阶段边界表 396 的数据源描述必须与数据流图 93 的数据源入口保持一致；若不一致需统一口径
3. **OWID 完全移除 vs 保留历史标注**: OWID 不应完全删除（项目阶段 1 历史记录仍有价值），应在数据流图或注释中标注为"历史数据源 / 参考"而非"当前 primary"
4. **prepare_features 旧签名在文档中消失导致困惑**: 必须保留对旧 `(df, tiers=[...])` 签名的说明，而不是只写新签名；明确声明兼容性
5. **TimeConfig 引用不一致**: 所有 `gap=96` 和 `(96,)` 数字应优先使用 `TimeConfig.points_per_day` 语义描述，避免后续从 15min 切换回 30min/1h 时需要全文替换数字
6. **Tier4 描述不应承诺精度提升**: 文档须说明 Tier4 是可选增强层，天气数据是小时级 ffill 到 15min，不保证预测精度提升
7. **更新 updated_at 但漏更新版本文档历史**: 确保 frontmatter `updated_at` 正确更新，但不在文档中新增版本号段（遵循已有格式）
8. **概念"当前"与"历史"混淆**: 对旧事实如 OWID 加注 "⏳ 历史 / 参考" 前缀而非删除，避免 Agent 读取时将历史数据源误判为活动状态

## 非目标

- 不修改 ARCHITECTURE.md 中的文件布局部分（line 335-390，无新增文件）
- 不改动接口层 (API/Service/CLI/LLM) 描述（Phase 4 未变更）
- 不修改模块职责中除 data_loader/features/forecaster/trading_env 外的其他模块
- 不重新组织文档结构或段落顺序
- 不新增流程图或 ASCII art（只改既有图）
- 不改其他 scan 文档（ORGANIZATION.md, CONVENTIONS.md 等）

## 参考

- `docs/Ellectric/scan/ARCHITECTURE.md` — 本文档（全线 399 行，9 个章节）
- `.sillyspec/changes/2026-06-27-weather-and-roadmap-sync/design.md` — Wave 4 文档对账设计描述
- `.sillyspec/changes/2026-06-27-weather-and-roadmap-sync/requirements.md` — FR-005 文档验收标准
- `.sillyspec/changes/2026-06-27-weather-and-roadmap-sync/decisions.md` — D-009@v1 至少清理 TimeConfig/Data flow/TradingEnv action shape/phase data source
- `ellectric/config.py` — `TimeConfig.points_per_day=96`, `freq="15min"` 等常量定义
- `ellectric/pipeline/data_loader.py` — `ShandongDataLoader` 当前完整类实现
- `ellectric/pipeline/features.py` — `FeatureEngineer` 当前完整实现（包括 Tier4 新增后）
- `ellectric/pipeline/trading_env.py` — `ElectricityMarketEnv` 动作空间当前实现

## TDD 步骤

1. 读取 `ARCHITECTURE.md` 全文，标记所有包含 OWID/hourly/24h/gap=24/Box(24)/tier3/prepare_features(tier=...) 的段落（共 12 处旧事实，见实现要求表格）
2. 对照 `data_loader.py` 确认 `ShandongDataLoader` 合约描述
3. 对照 `features.py` 确认 `prepare_features` 当前签名和 Tier4 方法签名
4. 对照 `config.py` 确认 `TimeConfig` 常量值（points_per_day=96, freq=15min）
5. 对照 `trading_env.py` 确认动作空间 shape 实现
6. 按实现在要求表格 O1→O12 顺序逐一替换旧事实
7. 全文 grep 确认无残留 `OWID` (除了历史标注)、`Box\(0,1,\(24`、`gap=24`、`prepare_features(df, tier=`、`tier="tier3"` 等旧模式
8. 检查阶段边界表与数据流图描述一致性（O1 vs O10 对齐）
9. 检查 `updated_at` 已更新
10. 输出 `git diff docs/Ellectric/scan/ARCHITECTURE.md` 确认变更范围

## 验收标准表格

| # | 标准 | 验证方式 | 覆盖 |
|---|---|---|---|
| 1 | 数据流图顶部数据源入口从 OWID GitHub 主入口改为 Shandong CSV 15min 主入口 + OWID 历史注释 | grep "OWID" 确认出现 2 次（含历史标注），Shandong 出现在数据源位置 | FR-005, D-009@v1 |
| 2 | data_loader 模块职责包含 ShandongDataLoader | grep "ShandongDataLoader" 在模块职责 section 出现 | FR-005, D-009@v1 |
| 3 | `prepare_features` 签名使用 `tiers` 列表形式而非 `tier` 字符串 | grep "prepare_features(" 确认签名含 `tiers` 而非 `tier=` | FR-005, D-009@v1 |
| 4 | FeatureEngineer 提及 Tier4 weather | grep "add_tier4_weather_features" 或 "Tier4" 在 features section 出现 | FR-005 |
| 5 | `TimeSeriesSplit(gap=` 值为 96 而非 24 | grep "TimeSeriesSplit" 确认 gap 值为 96 或 TimeConfig 引用 | FR-005, D-009@v1 |
| 6 | `Box(0,1,` 动作空间使用 `(96,)` 或 `TimeConfig.points_per_day` | grep "Box" 确认 shape 为 `(96,)` 或 `points_per_day` | FR-005, D-009@v1 |
| 7 | Phase 1 数据源描述更新为山东 15min | grep "Phase 1" 在阶段边界表确认数据源不再只写 OWID | FR-005, D-009@v1 |
| 8 | 关键设计模式中特征层描述为 4-Tier 而非 3-Tier | grep "Tier" 在 design patterns section 确认描述 | FR-005 |
| 9 | 数据流图中 FeatureEngineer 标注体现可选 Tier4 | 数据流 ASCII 图中 features 节点的下级标注含 Tier4 | FR-005, D-009@v1 |
| 10 | updated_at 更新为 2026-06-27 | grep "updated_at" 确认日期 | — |
| 11 | 无残留 `gap=24` 或 `Box(0, 1, (24,))` 作为当前事实 | rg "gap=24" 或 "Box\(0, 1, \(24" 确认 0 匹配（允许历史注释中的数据流描述含旧值） | FR-005, D-009@v1 |
| 12 | 无残留 `prepare_features.*tier=` 单字符串签名 | rg 'prepare_features.*tier=' 或 'prepare_features.*"tier[0-9]"' 确认 0 匹配（prepare_features 签名行用 tiers 列表形式） | FR-005, D-009@v1 |
