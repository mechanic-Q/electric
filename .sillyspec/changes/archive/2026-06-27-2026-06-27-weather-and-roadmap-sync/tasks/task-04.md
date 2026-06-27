---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-04
title: 更新 feature-engineer 模块文档与 module-map
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
  - docs/Ellectric/modules/feature-engineer.md
  - docs/Ellectric/modules/_module-map.yaml
---

# Task-04: 更新 feature-engineer 模块文档与 module-map

## 修改文件

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `docs/Ellectric/modules/feature-engineer.md` | 新增 Tier4 weather 契约：`add_tier4_weather_features`、`prepare_features` 扩展签名、`get_feature_columns("tier4")`、天气列数据模型、缓存与降级说明 |
| 修改 | `docs/Ellectric/modules/_module-map.yaml` | feature-engineer 增加 weather-related tags/aliases/entrypoints/main_symbols；新增 weather-fetcher 模块条目（路径 `ellectric/fetch/weather.py`） |

## 覆盖来源

| 需求/决策 | 覆盖方式 |
|---|---|
| FR-005 | 仓库模块文档与 Phase 4 状态对齐：feature-engineer 文档同步 Tier4 weather 契约，module-map 增加 weather-fetcher 模块条目与 feature-engineer 的 weather 标记 |
| D-009@v1 | scan 架构文档属于本轮文档对账范围（task-05 覆盖扫描文档，本 task 覆盖模块文档 + module-map）；模块文档对账是 D-009@v1 的组成部分 |

## 实现要求

### 1. `feature-engineer.md` 修改

现有 3 层（Tier1→Tier3）改为 4 层（Tier1→Tier4），保持已有内容不变，在 Tier3 之后追加：

- **定位段**: 更新 "提供3层渐进式" → "提供4层渐进式"
- **契约摘要段**: 追加 `add_tier4_weather_features` 签名说明
- **关键逻辑段**: 追加 Tier4 小节描述 weather 缓存策略、对齐方式、降级行为
- **注意事项段**: 追加 weather 相关注意事项（cache 派生数据、小时级→15min ffill、网络失败降级）

weather 列数据模型（新增表格或自然语言描述）：

| 列模式 | 类型 | 来源 |
|---|---|---|
| `temp_<city>` | float | Open-Meteo 2m 气温 |
| `ghi_<city>` | float | 地表短波辐射 |
| `wind_speed_<city>` | float | 10m 风速 |
| `precip_<city>` | float | 降水 |
| `humidity_<city>` | float | 相对湿度 |
| `cloud_<city>` | float | 云量 |

城市源自 `SHANDONG_CITIES`（`jinan`, `qingdao`）。

### 2. `_module-map.yaml` 修改

**feature-engineer 模块**修改项：

```yaml
  feature-engineer:
    tags: 追加 - weather / - weather-features / - tier4
    aliases: 保持已有，不删
    entrypoints: 追加 - add_tier4_weather_features（非主要入口，但作为新方法标记）
    main_symbols: 追加 - add_tier4_weather_features
    depends_on: 追加 - weather-fetcher（Tier4 可选依赖）
```

**新增 weather-fetcher 模块条目**（放在 feature-engineer 之后，forecaster 之前）：

```yaml
  weather-fetcher:
    status: active
    doc: null  # 无独立模块文档，功能描述内联在 feature-engineer 中
    paths:
      - ellectric/fetch/weather.py
    tags:
      - weather
      - open-meteo
      - fetch
      - shandong
    aliases:
      - WeatherFetcher
      - weather
    entrypoints:
      - WeatherFetcher
    main_symbols:
      - WeatherFetcher
      - fetch_historical
      - align_to_15min
    depends_on: []
    used_by:
      - feature-engineer  # Tier4 可选依赖
    needs_review: false
    concerns: []
    review_reasons: []
```

## 接口定义

文档任务，N/A。输出为 `.md` 与 `.yaml` 格式的模块描述文件，不涉及 Python 代码接口。

接口的最终权威来源是源码 `ellectric/pipeline/features.py` 与 `ellectric/fetch/weather.py`。文档契约必须与 task-01 测试和 task-03 实现保持一致：

- `add_tier4_weather_features(df, weather_df=None, weather_cache_path=None, fetch_if_missing=True)` → `pd.DataFrame`
- `prepare_features(df, tiers=None, weather_df=None, weather_cache_path=None, fetch_if_missing=True)` → `pd.DataFrame`
- `get_feature_columns(tier="tier4")` → `list[str]`

## 边界处理

1. **Tier4 文档不影响现有 Tier1-3 文档内容**: 已有三段保持不动，仅追加；不删除、不改写任何现有 Tier1-3 描述
2. **module-map 已有模块顺序不变**: 新增 weather-fetcher 条目插入在 feature-engineer 与 forecaster 之间，不重排现有模块
3. **feature-engineer 的 `depends_on` 标注为可选**: weather-fetcher 是 Tier4 的运行时依赖，但旧 Tier1-3 调用不依赖它；`depends_on` 在 map 中体现为 feature-engineer → weather-fetcher 的引用关系，但文档须说明"可选"或"Tier4 场景下"
4. **weather-fetcher 模块 doc 为 null**: 不创建独立 `weather-fetcher.md`；功能描述由 `feature-engineer.md` 覆盖（YAGNI — 无独立模块文档需求）
5. **module-map `generated_at` 与 `source_commit` 不更新**: 此 map 为静态引用，本轮不对 map 元数据做自动时间戳/commit 更新；仅 `modules` 下的条目变更
6. **文档中涉及的列名须与 features.py 实际输出一致**: 不虚构列模式；weather 列名格式 `{var}_{city}` 源自 `WeatherFetcher` 输出格式（如 `temp_jinan`, `ghi_qingdao`）
7. **`prepare_features` 扩展签名的文档描述须说明兼容旧调用**: 旧签名 `prepare_features(df, tiers=["tier1"])` 行为不变；新增 weather 参数均为默认值，不破坏现有 notebook/script 代码

## 非目标

- 不创建独立 `docs/Ellectric/modules/weather-fetcher.md`（Tier4 文档内联在 feature-engineer 中）
- 不更新 `generated_at` / `source_commit` 等 map 元数据
- 不修改 `docs/Ellectric/scan/ARCHITECTURE.md`（属于 task-05）
- 不修改 README、ROADMAP、REQUIREMENTS（属于 task-06）
- 不修改 `features.py`、`weather.py` 等源码文件
- 不修改 `_module-map.yaml` 已有的 feature-engineer 模块路径和主符号列表（仅追加 tags/entrypoints/main_symbols/depends_on）

## 参考

- `docs/Ellectric/modules/feature-engineer.md` — 当前 3 层文档，需原地追加 Tier4 内容
- `docs/Ellectric/modules/_module-map.yaml` — 完整模块映射文件，参考已有模块（如 data-loader、forecaster）的 tags/aliases/entrypoints 范式
- `ellectric/fetch/weather.py` — WeatherFetcher 类签名与输出列格式
- `ellectric/pipeline/features.py` — Tier4 方法真实签名（task-03 实现后）
- `docs/Ellectric/modules/data-loader.md` — 作为模块文档格式参照
- `design.md` 非目标 & 兼容策略 — 确保文档口径与 design 一致

## TDD 步骤

1. 读取现有 `feature-engineer.md`，确认已有的前 3 层内容无误不删
2. 在定位段将 "提供3层" → "提供4层"
3. 在契约摘要段追加 `add_tier4_weather_features` 条目
4. 在关键逻辑段追加 Tier4 小节（weather cache 策略、ffill 对齐、降级行为）
5. 在注意事项段追加 weather 注意事项
6. 追加 weather 列数据模型表格
7. 读取 `_module-map.yaml`，确认 feature-engineer 现有条目
8. 修改 feature-engineer 条目：tags 追加 weather/weather-features/tier4；entrypoints 追加 add_tier4_weather_features；main_symbols 追加 add_tier4_weather_features；depends_on 追加 weather-fetcher
9. 在 feature-engineer 与 forecaster 之间插入 weather-fetcher 新条目
10. grep 验证：`rg 'tier4|weather.*fetcher|add_tier4' docs/Ellectric/modules/` 应返回新增内容

## 验收标准表格

| # | 标准 | 验证方式 | 覆盖 |
|---|---|---|---|
| 1 | `feature-engineer.md` 定位段写明 "4层渐進式" | grep "4层" 或 "Tier4" | FR-005 |
| 2 | `feature-engineer.md` 契约摘要包含 `add_tier4_weather_features` | grep 确认方法名存在 | FR-005 |
| 3 | `feature-engineer.md` 关键逻辑包含 weather 缓存与降级说明 | grep cache/降级/ffill 或 safe ffill | FR-005 |
| 4 | `feature-engineer.md` 注意事项包含 weather 注意事项 | grep weather cache / 网络失败 / 小时级 | FR-005 |
| 5 | `feature-engineer.md` 列数据模型包含 `temp_jinan`/`ghi_qingdao` | grep 确认列名模式 | FR-005 |
| 6 | `_module-map.yaml` feature-engineer tags 包含 `weather` / `weather-features` / `tier4` | yq 或 grep 确认 | FR-005, D-009@v1 |
| 7 | `_module-map.yaml` feature-engineer entrypoints 包含 `add_tier4_weather_features` | grep 确认 | FR-005, D-009@v1 |
| 8 | `_module-map.yaml` feature-engineer depends_on 包含 `weather-fetcher` | grep 确认 | FR-005, D-009@v1 |
| 9 | `_module-map.yaml` 新增 weather-fetcher 模块条目 | grep "weather-fetcher:" + 确认 paths/aliases/entrypoints | FR-005, D-009@v1 |
| 10 | 现有 Tier1-3 内容未被删除或改写 | diff 显示仅追加、无删除 | 兼容性 |
| 11 | 不修改 `_module-map.yaml` 的 `generated_at` / `source_commit` | grep 确认元数据未变 | 非目标 |
| 12 | 无新增 `.md` 文件（weather-fetcher 无独立文档） | `git diff --name-only` 不出现新 md 文件 | YAGNI |
