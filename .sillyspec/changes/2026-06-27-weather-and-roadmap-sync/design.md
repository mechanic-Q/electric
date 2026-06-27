---
author: lmr
created_at: 2026-06-27 18:58:49
---

# Design: WeatherFetcher Tier4 集成 + Phase 4 文档/wiki 对账

## 背景

Electric 已完成图迹对标主线中的 15min 数据粒度迁移：山东 15min CSV 成为当前 canonical 高频数据资产，`TimeConfig` 已统一为 96 点/日、672 点/周、`freq="15min"`。LLM Wiki 中 `wiki/synthesis/electric-data-requirements-vs-tuji-20260622.md` 的核心目标（从小时级升级到 15min、清理 24/168 硬编码）已通过上一轮变更达成。

剩余可做项集中在两个非核心但有价值的方向：

1. `WeatherFetcher` 已存在并能通过 Open-Meteo 抓取济南/青岛历史气象，但尚未进入 `FeatureEngineer` 的训练特征链路。
2. README、ROADMAP、REQUIREMENTS 与 LLM Wiki 的项目状态描述存在时间线差异，需要按照 wiki `purpose.md` 的增量更新原则与 `schema.md` 的页面规则同步。

本变更执行用户确认的选项 B：集成 WeatherFetcher 功能特性，同时对齐 README、ROADMAP 和 Wiki 文档，并将 Phase 4 的项目状态统一。

## 设计目标

- FR-001: `FeatureEngineer` 新增 Tier4 weather layer，将气象特征作为显式可选层，而不改变 Tier1-3 的默认行为。
- FR-002: 气象数据优先使用 parquet 缓存，支持离线复跑；缓存缺失时可调用 `WeatherFetcher` 抓取并落盘。
- FR-003: 气象数据与山东 15min `timestamp` 对齐，天气列可进入 `get_feature_columns("tier4")` 与 `prepare_features(tier="tier4")`。
- FR-004: 缺少天气数据或抓取失败时，基础特征链路保持可用，降级为无 weather 特征而非中断。
- FR-005: README、ROADMAP、REQUIREMENTS、scan 架构文档、模块文档与当前 Phase 4 状态一致。
- FR-006: LLM Wiki 按 `purpose.md` 与 `schema.md` 规则进行时间线感知增量更新：新增 synthesis、更新 entity/synthesis/index/log。

## 非目标

- 不做准实时 T+15min/T+1h 调度，不引入 cron、daemon、队列或 live API。
- 不做中长期合约接入 pipeline。
- 不做多省、多节点、多城市市场覆盖；MVP 仍以山东为中心。
- 不做真实交易、付费数据源、账号制数据抓取。
- 不训练新模型、不承诺天气特征提升精度；本轮只打通数据/特征接口与可验证合约。
- 不让 Tier1-3 依赖网络或 weather cache。

## 拆分判断

无需拆分。原因：本变更只有两个紧密相关的目标：GAP-1 气象特征接入与 GAP-6 状态文档对账。二者共同服务 Phase 4 收尾，文件影响面有限，不涉及 3+ 独立模块、3+ 角色视图、跨页面状态流转，也不是模板×数据批量任务。

## 总体方案

### Wave 1: Weather Tier4 契约

在 `FeatureEngineer` 中新增 `add_tier4_weather_features(df, weather_df=None, weather_cache_path=None, fetch_if_missing=True)`。调用者可显式传入 `weather_df`，也可传入/使用默认 cache path。函数只在 Tier4 被请求时工作，不改变 Tier1-3。

Tier4 的列为 WeatherFetcher 当前输出的城市天气列，例如：`temp_jinan`, `ghi_jinan`, `wind_speed_jinan`, `precip_jinan`, `humidity_jinan`, `cloud_jinan` 以及青岛对应列。字段名沿用 `WeatherFetcher` 既有输出，不新增别名层。

### Wave 2: 缓存与对齐策略

默认 cache path 为 `ellectric/data/shandong/weather_2024-2026.parquet`。读取优先级：

1. 显式 `weather_df`：直接按 `timestamp` 对齐并合并。
2. cache 存在：读取 parquet 后按 `timestamp` 对齐并合并。
3. cache 缺失且 `fetch_if_missing=True`：根据 df 时间范围推导 `start/end`，调用 `WeatherFetcher.fetch_historical()`，将小时级天气 reindex 到 df 的 15min 时间轴并 `ffill`，写入 cache。
4. 无法获取天气：记录 warning，返回原 df，不追加 weather columns。

### Wave 3: Feature API 扩展

`get_feature_columns("tier4")` 返回 Tier1-3 特征 + 已知 weather columns 中实际存在的列。`prepare_features(df, tiers=["tier1", "tier2", "tier3", "tier4"], weather_df=None, weather_cache_path=None, fetch_if_missing=True)` 支持一键执行 Tier1→Tier4。

兼容策略：`tier="tier3"` 及以下保持当前行为；旧调用者不受影响。

### Wave 4: 文档与 Wiki 对账

本仓库文档：

- `ellectric/README.md`: 更新 Phase 4 todo，说明 weather features 已接入/待验证状态。
- `.planning/ROADMAP.md`: 对齐 Phase 4 与持续改进项状态。
- `.planning/REQUIREMENTS.md`: 标注对应集成需求状态。
- `docs/Ellectric/scan/ARCHITECTURE.md`: 更新 stale 的 24/h 架构摘要，加入 ShandongDataLoader 与 TimeConfig 15min 事实，避免后续规划被旧扫描结果误导。
- `docs/Ellectric/modules/feature-engineer.md`: 新增 Tier4 weather 契约。
- `docs/Ellectric/modules/_module-map.yaml`: 给 feature-engineer 增加 weather 相关 tags/entrypoints，必要时新增 weather-fetcher 模块条目。

LLM Wiki：

- 新增 `wiki/synthesis/electric-phase4-closeout-20260627.md`，记录主线已对齐、Out-of-scope 决策与本轮 Phase 4 收尾范围。
- 更新 `wiki/entities/lmr-electric.md`，补充 Weather Tier4 与 Phase 4 状态。
- 更新 `wiki/synthesis/electric-data-requirements-vs-tuji-20260622.md`，加入 2026-06-27 状态段，说明 15min 主线已达成，准实时/中长期合约保持非目标。
- 更新 `wiki/index.md` 与 `wiki/log.md`，遵守 `schema.md` 的 wikilink 与 log 格式。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `ellectric/pipeline/features.py` | 新增 Tier4 weather 特征层、cache 读取/抓取/对齐辅助逻辑 |
| 修改 | `ellectric/fetch/weather.py` | 如需补充 cache helper 或 docstring，保持 Open-Meteo 抓取职责 |
| 修改 | `tests/test_weather_features.py` | 新增 Tier4/cache/对齐/降级测试 |
| 修改 | `docs/Ellectric/scan/ARCHITECTURE.md` | 更新 stale 的 24/h 与 OWID 架构摘要，加入山东 15min 与 TimeConfig 事实 |
| 修改 | `docs/Ellectric/modules/feature-engineer.md` | 同步 Tier4 weather 契约 |
| 修改 | `docs/Ellectric/modules/_module-map.yaml` | 更新 feature-engineer tags/entrypoints，必要时加入 weather-fetcher 模块 |
| 修改 | `ellectric/README.md` | Phase 4 todo/状态对账 |
| 修改 | `.planning/ROADMAP.md` | Phase 4 状态与持续改进项对账 |
| 修改 | `.planning/REQUIREMENTS.md` | 集成需求状态对账 |
| 新增 | `wiki/synthesis/electric-phase4-closeout-20260627.md` | LLM Wiki synthesis 页面，记录本轮收尾结论 |
| 修改 | `wiki/entities/lmr-electric.md` | 更新项目实体状态 |
| 修改 | `wiki/synthesis/electric-data-requirements-vs-tuji-20260622.md` | 更新图迹对账状态 |
| 修改 | `wiki/index.md` | 增加新 synthesis 索引 |
| 修改 | `wiki/log.md` | 记录本次 wiki 增量更新 |

## 接口定义

### FeatureEngineer 新增方法

```python
class FeatureEngineer:
    def add_tier4_weather_features(
        self,
        df: pd.DataFrame,
        weather_df: pd.DataFrame | None = None,
        weather_cache_path: str | Path | None = None,
        fetch_if_missing: bool = True,
    ) -> pd.DataFrame: ...
```

语义：

- `df` 必须包含 `timestamp`。
- `weather_df` 可以是 index 为 timestamp 或含 `timestamp` 列的 DataFrame。
- `weather_cache_path=None` 时使用默认山东 weather cache path。
- `fetch_if_missing=False` 且 cache 缺失时，不触网，返回无 weather 列的 df。

### prepare_features 扩展

```python
def prepare_features(
    df: pd.DataFrame,
    tiers: list | None = None,
    weather_df: pd.DataFrame | None = None,
    weather_cache_path: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> pd.DataFrame: ...
```

兼容现有签名：`tiers` 仍是层级列表，默认仍为 `["tier1"]`；当 `tiers` 中包含 `"tier4"` 时，函数会确保 Tier1→Tier3 已按顺序执行，再调用 `add_tier4_weather_features()`。`get_feature_columns("tier4")` 返回 Tier1-3 columns + 实际存在的 weather columns。

## 数据模型

无数据库表变更。DataFrame 增加可选天气列：

| 列模式 | 类型 | 说明 |
|---|---|---|
| `temp_<city>` | float | 2m 气温 |
| `ghi_<city>` | float | 地表短波辐射 |
| `wind_speed_<city>` | float | 10m 风速 |
| `precip_<city>` | float | 降水 |
| `humidity_<city>` | float | 相对湿度 |
| `cloud_<city>` | float | 云量 |

城市默认来自 `SHANDONG_CITIES`: `jinan`, `qingdao`。

## 兼容策略

- Tier1-3 默认行为不变。
- `prepare_features()` 原有 `df, tier` 调用仍可用；新增参数均有默认值。
- 缺天气 cache 或 Open-Meteo 失败不阻断，返回原 df 并 warning。
- 不改变 `WeatherFetcher.fetch_historical()` 和 `align_to_15min()` 的 public behavior。
- Wiki 更新为增量补充，不覆盖既有历史结论；保留 2026-06-22 历史判断和 2026-06-27 更新段。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | Open-Meteo 网络失败导致测试不稳定 | P0 | 测试不触网；用 fake weather_df/cache 覆盖 |
| R-02 | weather cache 变成隐式真值，污染可复现性 | P1 | 明确 cache 是派生数据；文档记录来源和可重建方式 |
| R-03 | FeatureEngineer 变厚，职责混杂 | P1 | 仅保留最小 cache/load/align helper；若后续扩展再拆 weather_features.py |
| R-04 | Weather hourly → 15min ffill 容易被误解为 15min 真实气象 | P1 | 文档明确天气源为小时级，15min 仅对齐/前向填充 |
| R-04b | 现有 `WeatherFetcher.align_to_15min(tolerance="30min")` 可能让每小时第 4 个 15min 点变 null | P1 | Tier4 采用不带 30min 容差的 safe ffill 对齐，或修正 align_to_15min 逻辑并加测试 |
| R-05 | Wiki 与仓库双写导致状态漂移 | P1 | 用新 synthesis 作为一次性对账锚点，并更新 log/index |
| R-06 | `.planning/ROADMAP.md` 与 README 的 Phase 编号冲突 | P2 | 只做状态对账，不大改路线图结构；冲突写入 wiki synthesis |

## 决策追踪

- D-001@v1 覆盖非目标：不做准实时 T+15min。
- D-002@v1 覆盖非目标：不做中长期合约串 pipeline。
- D-003@v1 覆盖非目标：不做多省/多节点。
- D-004@v1 覆盖非目标：不做真实交易/付费数据源。
- D-005@v1 覆盖 FR-001~FR-006：本轮范围为 WeatherFetcher Tier4 + 文档/wiki 对账。
- D-006@v2 覆盖 FR-001/FR-003：气象集成方式为 FeatureEngineer Tier4，并兼容现有 `prepare_features(df, tiers)` 签名。
- D-007@v2 覆盖 FR-002/FR-004：气象数据用 parquet cache，缺失可降级；Tier4 对齐必须覆盖 00:45 等 15min 边界。
- D-008@v1 覆盖 FR-006：wiki 按 purpose/schema 进行增量记录。
- D-009@v1 覆盖 FR-005：scan 架构文档纳入本轮文档对账范围。

未解决决策：无。剩余风险见风险登记。

## 自审

| 检查项 | 结果 | 说明 |
|---|---|---|
| 需求覆盖 | 通过 | 覆盖用户确认的方案 A 与四个 out-of-scope 决策 |
| Grill 覆盖 | 通过 | design 引用 D-001@v1 至 D-009@v1，并引用当前版本 D-006@v2 / D-007@v2 |
| 约束一致性 | 通过 | 延续 FeatureEngineer Tier 模式、DataFrame 合约、可选依赖降级风格 |
| 真实性 | 通过 | WeatherFetcher/FeatureEngineer/README/ROADMAP/wiki 文件均真实存在；新增文件标注为新增 |
| YAGNI | 通过 | 不做准实时/合约/多省/真实交易；不新增独立 weather_features 模块 |
| 验收标准 | 通过 | FR 可用 pytest +文档 grep/wiki 文件检查验证 |
| 非目标清晰 | 通过 | 明确四个用户锁定的非目标 |
| 兼容策略 | 通过 | Tier1-3 和旧 prepare_features 调用不变 |
| 风险识别 | 通过 | 覆盖网络、缓存、职责、对齐语义、wiki 漂移、路线图冲突 |
| 生命周期契约表 | 不适用 | 未涉及 session/lease/agent_run/daemon/lifecycle/claim/heartbeat |
