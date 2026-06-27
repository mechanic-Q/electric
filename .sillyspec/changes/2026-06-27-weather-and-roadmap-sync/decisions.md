---
author: lmr
created_at: 2026-06-27 18:58:49
---

# Decisions

## D-001@v1: 不做准实时 T+15min 调度

- type: boundary
- status: accepted
- source: user
- question: 本轮是否追求图迹 C 档 T+15min/T+1h 准实时能力？
- answer: 不做。当前确定准实时不是本项目范围。
- normalized_requirement: 本轮不得引入 cron、daemon、队列、live polling、准实时抓取或实时 API 依赖。
- impacts: [non-goal, FR-006, verify-docs]
- evidence: 用户明确说明「准实时：现在确定是不做的」。
- priority: P0

## D-002@v1: 不做中长期合约串 pipeline

- type: boundary
- status: accepted
- source: user
- question: 中长期合约是否必须进入 pipeline？
- answer: 不做。它是增强项，当前先不做。
- normalized_requirement: 本轮不得新增合约 loader、合约特征、合约结算逻辑或合约回测流程。
- impacts: [non-goal, docs]
- evidence: 用户明确说明「中长期合约未穿 pipeline：这个我们也先可以不做，因为它是增强性的」。
- priority: P0

## D-003@v1: MVP 保持单省山东，不做多省/多节点

- type: boundary
- status: accepted
- source: project + wiki
- question: 是否继续扩展广东/山西/蒙西/多节点数据？
- answer: 不做。本轮以山东 15min 作为 canonical MVP 数据资产。
- normalized_requirement: 文档对账时保留单省山东口径；不新增省份配置层。
- impacts: [FR-005, FR-006]
- evidence: `lmr-electric.md` 记录项目已从山西切换到山东；用户确认继续走可做项。
- priority: P1

## D-004@v1: 不做真实交易/付费数据源

- type: boundary
- status: accepted
- source: project + wiki
- question: 是否接真实交易或付费/账号制数据？
- answer: 不做。项目是学习原型，不做真实资金和账号依赖。
- normalized_requirement: 不新增认证、交易下单、付费数据源、商业 API key 或真实交易存储。
- impacts: [non-goal, wiki]
- evidence: PROJECT/REQUIREMENTS 约束与用户当前讨论一致。
- priority: P0

## D-005@v1: 本轮范围选择选项 B

- type: architecture
- status: accepted
- source: user
- question: 下一轮 SillySpec 做哪条线？
- answer: 选项 B：WeatherFetcher 集成 features + README/ROADMAP/wiki 文档对账。
- normalized_requirement: 本轮必须同时覆盖 WeatherFetcher Tier4 集成与 Phase 4 状态文档对账，不拆成多个活跃变更。
- impacts: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006]
- evidence: 用户回答「1.B 2.sillyspec run brainstorm 3用上面建议」。
- priority: P0

## D-006@v1: WeatherFetcher 集成方式采用 FeatureEngineer Tier4

- type: architecture
- status: accepted
- source: user
- question: WeatherFetcher 如何接入 features.py？
- answer: 新增 Tier 4 weather 层。
- normalized_requirement: 在 `FeatureEngineer` 中增加 `add_tier4_weather_features()`；不把 weather 并入 Tier3，也不新增独立 weather_features.py。
- impacts: [FR-001, FR-003, task-feature-engineer, tests]
- evidence: 用户在需求探索中选择「新增 Tier 4 weather 层」。
- priority: P0

## D-006@v2: Tier4 必须兼容现有 `prepare_features(df, tiers)` 签名

- type: compatibility
- priority: P1
- status: accepted
- supersedes: D-006@v1
- source: design-grill
- question: design.md 原写 `prepare_features(df, tier="tier4")`，但真实源码使用 `prepare_features(df, tiers: list)`，如何避免破坏兼容？
- answer: 保留 `tiers` 列表接口；新增 weather 参数均为默认值；当 `tiers` 含 `"tier4"` 时执行 Tier1→Tier4。
- normalized_requirement: 不引入 `tier` 单数字符串新签名；实现必须兼容旧调用 `prepare_features(df, tiers=[...])`。
- impacts: [FR-003, design-api, tests]
- evidence: `ellectric/pipeline/features.py:197` 现有 `prepare_features(df, tiers=None)`；Design Grill X-001。

## D-007@v1: 气象数据使用 parquet 缓存

- type: compatibility
- status: accepted
- source: user
- question: 气象数据每次现拉还是缓存？
- answer: 抓取后落盘 parquet 缓存，后续离线复跑。
- normalized_requirement: 默认使用 `ellectric/data/shandong/weather_2024-2026.parquet`；cache 命中时不触网；cache 缺失可抓取并写入；抓取失败允许降级。
- impacts: [FR-002, FR-004, tests]
- evidence: 用户在需求探索中选择「落盘 parquet 缓存」。
- priority: P0

## D-007@v2: Tier4 对齐不得继承 `align_to_15min` 的 30min 容差缺陷

- type: risk
- priority: P1
- status: accepted
- supersedes: D-007@v1
- source: design-grill
- question: `WeatherFetcher.align_to_15min()` 用 `tolerance="30min"`，是否会导致每小时第 4 个 15min 点（如 00:45）无法 ffill？
- answer: 是潜在风险。Tier4 要么修正 `align_to_15min()`，要么内部采用 safe ffill 对齐并加测试。
- normalized_requirement: 15min 时间轴每小时 4 个点均应获得上一小时 weather 值，测试必须覆盖 00:45 这类边界。
- impacts: [FR-003, FR-004, tests]
- evidence: `ellectric/fetch/weather.py:193`; Design Grill X-002。

## D-008@v1: Wiki 按 purpose/schema 增量记录

- type: documentation
- status: accepted
- source: user + docs
- question: 如何记录 LLM Wiki 侧状态？
- answer: 按 wiki `purpose.md` 与 `schema.md` 执行增量更新：新增 synthesis，更新 entity/synthesis/index/log。
- normalized_requirement: 新增页面必须 kebab-case、frontmatter 包含 type/title/tags/related/created/updated；使用 `[[wikilink]]`；`wiki/log.md` 逆时间记录；保留历史结论并添加 2026-06-27 状态段。
- impacts: [FR-006, wiki-files]
- evidence: 用户要求「同时按照 llm-wiki 的 purpose.md 和 schema.md 规则来记录 wiki」；已读取 `/mnt/e/Agent_memory/wiki_nashsu/wiki_nashsu/purpose.md` 与 `schema.md`。
- priority: P0

## D-009@v1: 扫描文档也属于本轮文档对账范围

- type: consistency
- priority: P1
- status: accepted
- source: design-grill
- question: `docs/Ellectric/scan/ARCHITECTURE.md` 仍有 24/h、OWID、Box(24) 等旧事实，会不会误导后续 plan/execute？
- answer: 会。把 scan 架构文档纳入本轮文档对账，不只改 README/ROADMAP/REQUIREMENTS/wiki。
- normalized_requirement: 更新 `docs/Ellectric/scan/ARCHITECTURE.md` 中与 15min 主线冲突的摘要事实；至少清理 TimeConfig、Data flow、TradingEnv action shape、phase data source 相关旧事实。
- impacts: [FR-005, docs, verify-docs]
- evidence: `docs/Ellectric/scan/ARCHITECTURE.md:138`, `:206`, `:211`, `:236`; Design Grill X-003。
