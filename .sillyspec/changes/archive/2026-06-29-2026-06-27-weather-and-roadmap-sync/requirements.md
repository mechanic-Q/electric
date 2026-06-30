---
author: lmr
created_at: 2026-06-27 18:58:49
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 学习者 | 运行 notebook/API/CLI，理解天气特征如何进入负荷/电价预测链路 |
| 开发者 | 维护 FeatureEngineer、WeatherFetcher、文档和测试 |
| 未来 Agent | 读取 SillySpec 和 LLM Wiki 文档，继续 Phase 4 或后续增强 |

## 功能需求

### FR-001: FeatureEngineer 提供 Tier4 weather 特征层

覆盖决策：D-005@v1, D-006@v2

Given 一个包含 `timestamp` 和 `load_mw` 的 15min DataFrame
When 开发者调用 `FeatureEngineer.add_tier4_weather_features(df, weather_df=weather_df)`
Then 返回 DataFrame 包含原始列、已有特征列和 weather columns

Given 调用者只使用 Tier1~Tier3
When 调用 `add_tier1_features` / `add_tier2_features` / `add_tier3_features`
Then 行为与本变更前保持一致，不依赖 weather cache 或网络

### FR-002: Weather parquet cache 优先于网络抓取

覆盖决策：D-007@v2

Given `weather_cache_path` 指向存在的 parquet 文件
When 调用 `add_tier4_weather_features(df, weather_cache_path=path)`
Then 系统从 parquet 读取天气数据并合并，不调用 Open-Meteo 网络接口

Given cache 不存在且 `fetch_if_missing=False`
When 调用 `add_tier4_weather_features(df, weather_cache_path=missing, fetch_if_missing=False)`
Then 系统记录 warning 并返回无 weather columns 的 df，不抛出异常

Given cache 不存在且 `fetch_if_missing=True`
When 调用 Tier4 weather layer
Then 系统可调用 `WeatherFetcher.fetch_historical()` 抓取天气、对齐 15min、写入 cache 并合并天气列

### FR-003: Weather 与 15min 时间轴安全对齐

覆盖决策：D-006@v2, D-007@v2

Given 小时级 weather_df 覆盖 `2024-01-01 00:00 UTC`
When 目标 DataFrame 有 `00:00`, `00:15`, `00:30`, `00:45` 四个 15min 点
Then 四个点都应获得同一小时天气值，不因 30min 容差导致 `00:45` 缺失

Given weather_df 使用 timestamp index 或 timestamp 列
When 合并到 load DataFrame
Then 输出 DataFrame 按 load DataFrame 的行顺序和时间轴返回

### FR-004: Feature column 契约支持 tier4

覆盖决策：D-006@v2

Given DataFrame 已有 weather columns
When 调用 `get_feature_columns("tier4")`
Then 返回 Tier1~Tier3 特征列 + 实际存在的 weather columns

Given DataFrame 未加入 weather columns
When 调用 `get_feature_columns("tier4")`
Then 不返回不存在的天气列，训练特征列表不包含缺失列

### FR-005: 仓库文档对齐 Phase 4 状态

覆盖决策：D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-005@v1, D-009@v1

Given README/ROADMAP/REQUIREMENTS/docs/scan 中存在 Phase 4 或图迹对标状态
When 本变更完成
Then 文档说明当前主线已完成 15min 对齐，Weather Tier4 已作为可选增强接入，并明确不做准实时、中长期合约、多省/多节点、真实交易/付费数据源

Given `docs/Ellectric/scan/ARCHITECTURE.md` 仍含 OWID/hourly/Box(24) 等旧事实
When 文档对账执行
Then 这些与当前代码冲突的旧事实被更新或标注为历史，不再作为当前架构事实

### FR-006: LLM Wiki 按 purpose/schema 增量更新

覆盖决策：D-008@v1

Given LLM Wiki 的 `purpose.md` 要求策展、增量更新、时间线感知和冲突显式记录
When 本变更同步 wiki
Then 新增 synthesis 不覆盖历史结论，而是记录 2026-06-27 状态、Out-of-scope 决策、当前 Phase 4 收尾结论

Given LLM Wiki 的 `schema.md` 要求 frontmatter、kebab-case、wikilink、index、log
When 新增 `wiki/synthesis/electric-phase4-closeout-20260627.md`
Then 页面包含 `type/title/tags/related/created/updated`，使用 `[[wikilink]]`，并被加入 `wiki/index.md` 和 `wiki/log.md`

## 非功能需求

- 兼容性：旧 Tier1~Tier3 调用和 `prepare_features(df, tiers=list)` 调用不破坏。
- 可回退：天气 cache/网络失败时不阻断基础 pipeline。
- 可测试：测试不得真实调用 Open-Meteo；使用 fake weather_df/cache。
- 可复现：parquet cache 是派生数据，文档必须说明来源和可重建方式。
- 文档一致性：仓库文档和 LLM Wiki 使用时间线补充，不删除历史判断。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-005, FR-006 | 准实时为非目标，文档/wiki 明确记录 |
| D-002@v1 | FR-005, FR-006 | 中长期合约为增强项，当前不做 |
| D-003@v1 | FR-005, FR-006 | MVP 单省山东，文档/wiki 保持一致 |
| D-004@v1 | FR-005, FR-006 | 不做真实交易/付费数据源 |
| D-005@v1 | FR-001~FR-006 | 本轮范围为 weather 集成 + 文档/wiki 对账 |
| D-006@v2 | FR-001, FR-003, FR-004 | Tier4 集成并兼容 `prepare_features(df, tiers)` |
| D-007@v2 | FR-002, FR-003 | parquet cache 与 15min safe ffill 对齐 |
| D-008@v1 | FR-006 | LLM Wiki 增量记录规则 |
| D-009@v1 | FR-005 | scan 架构文档纳入文档对账 |
