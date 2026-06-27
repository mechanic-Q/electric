---
author: lmr
created_at: 2026-06-27 18:58:49
---

# Proposal

## 动机

Electric 已完成图迹对标主线中最关键的 15min 数据粒度迁移：山东 15min 数据成为 canonical 高频数据资产，`TimeConfig` 已统一 96 点/日、672 点/周。LLM Wiki 中 `electric-data-requirements-vs-tuji-20260622.md` 的核心判断（从小时级升级到 15min，并清理 24/168 硬编码）已基本达成。

下一步应继续做两件能增强项目学习价值且不扩大范围的事：

1. 把已存在的 `WeatherFetcher` 接入 `FeatureEngineer`，让天气从“能抓取”变成“能作为训练特征使用”。
2. 对齐 README、ROADMAP、REQUIREMENTS 与 LLM Wiki 的 Phase 4 状态，避免后续规划被旧结论或旧扫描文档误导。

## 关键问题

### 1. WeatherFetcher 现在只是孤立工具

`ellectric/fetch/weather.py` 已能从 Open-Meteo 获取济南/青岛小时级气象并对齐 15min 时间轴，但 `FeatureEngineer` 没有 Tier4 weather 层，训练流程无法自然消费天气列。

### 2. 文档状态存在时间线漂移

README、`.planning/ROADMAP.md`、`.planning/REQUIREMENTS.md`、`docs/Ellectric/scan/ARCHITECTURE.md` 与 LLM Wiki 中对 Phase 4 / 图迹对标状态的描述不完全一致。尤其 scan 架构文档仍有 OWID/hourly/Box(24) 旧事实，需要与当前山东 15min 主线对齐。

### 3. Wiki 需要增量记录，而不是覆盖历史

LLM Wiki `purpose.md` 要求“时间线感知”和“增量更新”，`schema.md` 要求 synthesis/entity/source/query 等页面类型和 frontmatter。当前应新增 2026-06-27 的状态 synthesis，而不是抹掉 2026-06-22 的历史结论。

## 变更范围

- 在 `FeatureEngineer` 中新增 Tier4 weather 特征层。
- 默认使用 `ellectric/data/shandong/weather_2024-2026.parquet` 作为派生缓存；缓存缺失可调用 `WeatherFetcher` 抓取并写入。
- 兼容现有 `prepare_features(df, tiers=list)` 调用方式。
- 修正/规避 `WeatherFetcher.align_to_15min()` 30min 容差可能造成 00:45 等点位缺失的风险。
- 增加测试覆盖 weather cache、显式 weather_df 合并、tier4 columns、降级路径。
- 对齐 README、ROADMAP、REQUIREMENTS、scan 架构文档、模块卡片、module-map。
- 按 LLM Wiki `purpose.md` / `schema.md` 更新 wiki：新增 closeout synthesis，更新 lmr-electric、图迹数据需求 synthesis、index、log。

## 不在范围内（显式清单）

- 不做准实时 T+15min/T+1h 调度。
- 不做中长期合约串 pipeline。
- 不做多省/多节点/多市场覆盖。
- 不做真实交易、付费数据源、账号制数据抓取。
- 不训练新模型，不承诺天气特征改善 MAE/RMSE/MAPE。
- 不改变 Tier1-3 的默认行为。
- 不新增独立 `weather_features.py` 模块，除非后续设计再次修订。

## 成功标准（可验证）

- `FeatureEngineer.add_tier4_weather_features()` 存在并能把 weather_df 合并到 15min load DataFrame。
- `prepare_features(df, tiers=["tier1", "tier2", "tier3", "tier4"], weather_df=...)` 可运行，且旧调用 `prepare_features(df, tiers=["tier1"])` 行为不变。
- cache 命中时不触发 Open-Meteo 网络调用。
- weather cache 缺失且 `fetch_if_missing=False` 时不触网，基础特征链路不失败。
- 15min 对齐覆盖每小时 4 个点，包括 00:45 这类边界点。
- `get_feature_columns("tier4")` 返回 Tier1-3 特征 + 实际存在天气列。
- README/ROADMAP/REQUIREMENTS/docs/wiki 均记录 Phase 4 状态与 out-of-scope 决策。
- LLM Wiki 新增/更新页面符合 `schema.md` frontmatter、wikilink、index、log 规则。
