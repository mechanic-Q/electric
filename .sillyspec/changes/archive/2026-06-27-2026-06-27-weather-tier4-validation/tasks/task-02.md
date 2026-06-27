---
author: lmr
created_at: 2026-06-28 01:11:57
id: task-02
title: 实现 weather 来源解析与数据质量报告（覆盖：FR-02, FR-04, D-002@v1）
priority: P0
estimated_hours: 2
depends_on: [task-01]
blocks: [task-03, task-04, task-05, task-07]
requirement_ids: [FR-02, FR-04]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/scripts/validate_weather_tier4.py
---

# task-02: 实现 weather 来源解析与数据质量报告（覆盖：FR-02, FR-04, D-002@v1）

## 修改文件

| 操作 | 文件路径 |
|------|----------|
| 修改 | `ellectric/scripts/validate_weather_tier4.py` |

修改前一任务 task-01 建立的 `validate_weather_tier4.py`，将 `run_validation()` 桩函数替换为真实数据加载 + weather 来源解析 + 数据质量报告的流程。只改此一个文件。

## 覆盖来源

- **FR-02**（weather 来源解析）: 脚本内显式调用 ShandongDataLoader 和 FeatureEngineer 确定 weather 来源，不从日志反推。来源判定走四阶优先级：显式 weather_df → parquet cache → fetch（允许时）→ degraded。
- **FR-04**（降级与报告式验证）: 所有 weather 阻塞场景均降级处理，在报告中记录原因，不抛异常阻断。质量报告只记录、不设硬阈值。
- **D-002@v1**（Tier4 可选增强）: 降级场景下脚本仍完成 baseline 实验，weather_quality 记录 weather_features_available=false，产物包含降级原因。

## 实现要求

1. 将 `run_validation()` 桩函数体替换为以下流程：ShandongDataLoader 加载负荷数据 → 为后续 ablation 实验准备 feature DataFrame（借助已有的 `prepare_features` 或 `FeatureEngineer` 调用）→ 调用 `resolve_weather_source()` 判定 weather 来源 → 调用 `build_weather_quality_report()` 生成质量报告 → 将 quality 报告存入返回值 `weather_quality` 字段。

2. 新增 `resolve_weather_source()` 函数。它接收可选的显式 `weather_df`、`weather_cache_path`、`fetch_if_missing` 标志和 `load_df`（用于从数据时间范围驱动 fetch 的 `start`/`end`），返回一个标识来源的字符串和对应的 weather DataFrame（或 None）。来源判定逻辑：
   - 如果 `weather_df is not None` 且不为空且列数大于 0：来源为 `"explicit"`。
   - 否则如果 cache path 存在且可读且 parquet 内容非空：来源为 `"cache"`。
   - 否则如果 `fetch_if_missing` 为 True：尝试创建 WeatherFetcher 并调用 `fetch_historical`；成功且非空则来源为 `"fetch"`，失败则来源为 `"degraded"`。
   - 否则：来源为 `"degraded"`。
   - 对于 cache 读取错误（IOError、ParquetException、损坏等）和 fetch 网络错误（URLError、TimeoutError、JSONDecodeError 等），统一视为降级。cache 读取失败的 log level 为 WARNING（非 ERROR），fetch 失败的 log level 为 ERROR。

3. 新增 `build_weather_quality_report()` 函数。它接收原始负荷 DataFrame（load_df）、经过 Tier4 特征添加后的 feature DataFrame（feature_df）、最终 weather 列名列表、来源标识字符串，返回一个 dict 作为质量报告。返回 dict 的键和值的语义如下：
   - `weather_source`: 字符串，值为 `resolve_weather_source()` 输出的来源标识（`"explicit"` / `"cache"` / `"fetch"` / `"degraded"`）。
   - `weather_features_available`: 布尔值，True 表示 feature_df 中实际含有 weather 列，False 表示无 weather 列可用。
   - `weather_columns`: 字符串列表，列出最终的 weather 列名称；降级场景为空列表。
   - `weather_column_count`: 整数，weather_columns 的长度。
   - `missing_rate_by_column`: 字典，键为 weather 列名，值为该列在 feature_df 中的缺失率（NaN 数 / 总行数，浮点数范围 0.0-1.0）；降级场景为空字典。
   - `overall_missing_rate`: 浮点数，所有 weather 列合并后的整体缺失率；降级场景为 0.0。
   - `time_range`: 字典，包含 `start`（feature_df timestamp 最小值，ISO 格式）、`end`（最大值，ISO 格式）、`freq`（推断或默认 `"15min"`）。
   - `timezone`: 字符串，feature_df timestamp 列的时区标识（如 `"UTC"`）；缺失或无索引时返回 `"unknown"`。
   - `coverage`: 字典，包含 `total_points`（总行数）、`weather_covered_points`（至少有一个非空 weather 值的行数）、`coverage_ratio`（覆盖率，浮点数 0.0-1.0）。
   - `notes`: 字符串列表。降级场景至少包含一条说明原因的 note。其他可能的 note 包括：weather 数据时间范围窄于负荷数据、整体缺失率较高（超过 0.1）、某些列完全缺失。

4. `resolve_weather_source()` 和 `build_weather_quality_report()` 都保持纯函数设计，不修改全局状态或缓存文件。

5. `run_validation()` 在调用 `build_weather_quality_report()` 后，将得到 dict 存入 `result["weather_quality"]` 字段。本任务不处理 ablation experiment（task-03）和报告输出（task-04）。

## 接口定义

新增函数签名（python 风格描述，勿用代码块避免格式限制）:

`resolve_weather_source` 接收参数：weather_df 可以为 None 或 pd.DataFrame；weather_cache_path 可以为 None、字符串或 pathlib.Path；fetch_if_missing 布尔值，默认 True；load_df pd.DataFrame（用于提取时间范围驱动 fetch 的 start/end，需含 timestamp 列）。返回两个值的元组：第一个是来源字符串（取 "explicit" / "cache" / "fetch" / "degraded" 之一），第二个是 weather DataFrame 或 None。

`build_weather_quality_report` 接收参数：load_df pd.DataFrame（含 timestamp 列）；feature_df pd.DataFrame（经过 Tier4 特征添加后的完整 DataFrame）；weather_columns 字符串列表；weather_source 字符串。返回一个 dict，键值结构参见实现要求第 3 条。

`run_validation` 扩展现有签名（保持与 task-01 一致：start、end、output_dir、weather_cache、fetch_if_missing）。新增行为：内部构造 ShandongDataLoader 实例，调用 load_data() 获取负荷 DataFrame，调用 resolve_weather_source 获取 weather 来源和原始 weather data，再调用 FeatureEngineer.add_tier4_weather_features（或 prepare_features）将 weather 合并到特征 DataFrame。然后调用 build_weather_quality_report 生成质量报告。最终返回 dict 的结构相比 task-01 增加 `"weather_quality"` 顶层键，原有的 `"status"` 改为 `"ok"`，`"report_paths"` 仍为空列表。

## 边界处理

1. 空 weather_df：显式传入的 weather_df 为 None、空 DataFrame 或仅含零列时，resolve_weather_source 跳过 explicit 分支，进入 cache 或 fetch 判定，最终仍可能降级。build_weather_quality_report 在 weather_features_available 为 false 时直接跳过缺失率计算，notes 追加 "Explicit weather_df provided but empty" 或由 source 判定决定。

2. 负荷 DataFrame 缺少 timestamp 列或索引非 DatetimeIndex：resolve_weather_source 不依赖 timestamp（它仅用于 fetch 的时间范围），但 build_weather_quality_report 需要 timestamp 列进行 time_range/timezone/coverage 计算。若 timestamp 缺失，time_range 设为 null 值，timezone 返回 "unknown"，coverage 中 total_points 用 len(feature_df) 代替，weather_covered_points 和 coverage_ratio 设为 0.0，notes 追加 "load_df missing timestamp column; time_range/coverage not computed"。

3. cache 文件损坏或不可读：pd.read_parquet 抛出异常（IOError、OSError、pyarrow.lib.ArrowInvalid 等），resolve_weather_source 在 except 块中捕获 Exception，记录 WARNING 日志含异常信息，继续进入 fetch 或降级分支。build_weather_quality_report 不受影响（来源为 degraded 或 fetch，无 cache 侧逻辑泄漏）。

4. WeatherFetcher 网络失败：URLError、TimeoutError、或 fetch_historical 返回空 DataFrame，resolve_weather_source 在 except 块中捕获，记录 ERROR 日志，返回 ("degraded", None)。build_weather_quality_report 中 weather_features_available 为 false，notes 追加 "WeatherFetcher fetch failed: {具体原因}"。

5. Tier4 合并后无 weather 列：可能因为 weather source 为空、对齐后目标时间轴没有匹配点、或 weather 列均已在 df 中存在。build_weather_quality_report 检查 weather_columns 列表长度，若为零则 weather_features_available 为 false，missing_rate_by_column 为空字典，overall_missing_rate 为 0.0，notes 视具体原因追加说明（如 "No weather columns found in feature_df after merge"）。

6. 缺失率边界：missing_rate_by_column 中某列完全缺失（rate=1.0）不阻断，不在 notes 中重复天气列名路径（避免敏感泄漏），只记录 "some weather columns are fully missing"。overall_missing_rate 高于 0.1 时在 notes 中追加 "Overall weather missing rate > 0.1"，不设硬阈值。

7. timezone 缺失或推断失败：feature_df timestamp 是 naive（无时区）或为其他类型时，timezone 返回 "unknown" 而非 "UTC"，notes 追加 "timestamp column has no timezone info"。

8. coverage 中 weather_covered_points 计算：用 weather_columns 中任一张量在 feature_df 上的非空行数（any(axis=1) 代替 all(axis=1)），避免单列极低缺失率导致覆盖率为 0 的误判。

## 非目标

- ❌ 不实现 ablation 实验与指标计算（task-03）。
- ❌ 不实现 JSON/Markdown 报告写入（task-04）。
- ❌ 不添加验证脚本的自动化测试（task-05）。
- ❌ 不更新 feature-engineer 模块文档（task-06）。
- ❌ 不修改 ShandongDataLoader、FeatureEngineer、XGBoostForecaster、WeatherFetcher 的任何代码。
- ❌ 不新增独立的工具函数（resolve_weather_source 和 build_weather_quality_report 是脚本私有函数，不导出到 ellectric 包）。
- ❌ 不依赖外部配置或开关文件。
- ❌ 不做 weather 缓存写回或删除操作（resolve_weather_source 只读 cache，不写入）。
- ❌ 不引入新的第三方依赖（pandas 已在现有依赖中，不涉及）。

## 参考

- `design.md:49-57` — Wave 1 方案描述，新增脚本加载数据后显式解析 weather 来源。
- `design.md:60-72` — Wave 2 数据质量检查的具体检查项列表，包括 cache 状态、来源判定、列清单、缺失率、时区、覆盖范围。
- `design.md:72` — "检查只报告，不阻断" 语义，本 task 所有质量函数遵守此原则。
- `design.md:126-137` — `run_validation` 函数整体职责说明。
- `design.md:141-151` — `build_weather_quality_report` 函数签名和职责说明。
- `design.md:182-226` — JSON 报告结构中 weather_quality 字段的完整 schema（10 个字段 + notes：201-207 行）。
- `design.md:230-235` — 兼容策略：不修改 FeatureEngineer 签名，降级遵循现有语义。
- `design.md:242-244` — 风险 R-02：Open-Meteo 网络不可用时的降级策略。
- `design.md:252-254` — 决策 D-002@v1：Tier4 可选增强，缺失时降级记录。
- `features.py:215-302` — `add_tier4_weather_features` 实现代码，weather_df/cache path/fetch_if_missing 三个入参在调用时的映射关系。
- `features.py:238-282` — FeatureEngineer 内部的 weather 来源判定（四阶优先级），脚本的 resolve_weather_source 需与此语义对齐但独立实现，不依赖内部分支。
- `weather.py:91-117` — `WeatherFetcher.fetch_historical` 返回格式（timestamp 索引的 DataFrame，列名如 temp_jinan）。
- `weather.py:136-140` — URLError/JSONDecodeError 的异常处理模式，脚本的 fetch 分支复用此捕获但不跨模块依赖。
- `tests/test_weather_features.py:28-38` — `_fake_weather_hourly` 构造参考，用于理解 weather 列命名约定。
- `plan.md:25` — task-02 覆盖 FR-02、FR-04、D-002@v1 的关系确认。
- `plan.md:36` — AC-03 要求 weather_quality 包含 6 个指定字段。
- `plan.md:39` — AC-06 要求报告明确 hard_threshold_applied=false（本任务 weather_quality 不包含此字段，属 task-04 interpretation 字段）。

## TDD 步骤

1. [RED] 运行现有脚本 `python ellectric/scripts/validate_weather_tier4.py --help`，确认 task-01 桩函数仍然可用。确认 task-01 验收标准 AC-01-01 到 AC-01-09 保持通过。

2. [GREEN] 在 `run_validation()` 内添加 ShandongDataLoader import 和 load_data 调用，包裹在 try-except 中以处理数据文件缺失。日志记录加载行数和时间范围。对于数据加载失败，设置 result["status"] 为 "error" 并包含错误信息。

3. [RED] 编写并运行 Python 单测验证 resolve_weather_source 四个分支的判定是否正确：传入显式 weather_df 返回 ("explicit", df)；存在有效 cache 返回 ("cache", df)；cache 损坏 + fetch_if_missing=True 返回 ("fetch", df) 或 ("degraded", None)；cache 损坏 + fetch_if_missing=False 返回 ("degraded", None)。

4. [GREEN] 实现 resolve_weather_source：严格按 cache path 存在性、读取正确性、fetch 允许性的先后顺序判定。每个分支记录相应级别日志（INFO/WARNING/ERROR）。返回值类型严格一致（str, pd.DataFrame | None）。

5. [RED] 编写 Python 单测验证 build_weather_quality_report 的输出 dict 包含所有必需键：weather_source、weather_features_available、weather_columns、weather_column_count、missing_rate_by_column、overall_missing_rate、time_range、timezone、coverage、notes。确认含真实 weather 列的 feature_df 产生正确的列清单和缺失率。确认空 weather_columns 列表导致 weather_features_available=False。

6. [GREEN] 实现 build_weather_quality_report：遍历 weather_columns 计算每列缺失率；计算 overall_missing_rate 为所有 weather 列缺失率的均值；从 feature_df 中提取 time_range 和 timezone；计算 coverage 的三个子字段；根据来源和缺失情况构造 notes。不在此函数中做任何阈值检查或告警（仅记录事实）。

7. [RED] 测试边界场景 build_weather_quality_report 处理：feature_df 无 timestamp 列时 timezone 返回 "unknown"；weather_columns 为空时 missing_rate_by_column 为空字典；所有 weather 列完全缺失时 missing_rate 为 1.0，notes 包含相应说明；coverage 使用 any(axis=1) 而非 all(axis=1)。

8. [GREEN] 修改 build_weather_quality_report 处理以上边界场景，每个场景的分支路径均在日志中记录 debug 级别细节。

9. [RED] 端到端运行脚本确认 run_validation 返回 dict 包含 "weather_quality" 键且结构正确：`python -c "from ellectric.scripts.validate_weather_tier4 import run_validation; r = run_validation(); assert 'weather_quality' in r; assert r['weather_quality']['weather_source'] in ('explicit','cache','fetch','degraded')"`。

10. [GREEN] 调整 run_validation 内联逻辑直到端到端断言通过。

11. [REFACTOR] 提取 run_validation 中较长的内联代码块为具名步骤函数（如 `_load_data_or_fail`、`_resolve_weather`、`_build_quality`），保持 run_validation 本身为高层编排函数，易于阅读和后续 task-03/04 扩展。

## 验收标准

| ID | 标准 | 验证方式 | 关联需求/决策 |
|----|------|----------|---------------|
| AC-02-01 | resolve_weather_source 根据优先级返回正确来源字符串和 weather DataFrame | Python 单测覆盖四个分支 | FR-02 |
| AC-02-02 | cache 损坏时 resolve_weather_source 不抛异常，降级到 fetch 或 degraded | 模拟损坏 cache + 观察日志 | FR-02, D-002@v1 |
| AC-02-03 | fetch 失败时 resolve_weather_source 返回 degraded，weather_data 为 None | mock WeatherFetcher 扔异常 | FR-02, D-002@v1 |
| AC-02-04 | build_weather_quality_report 的返回 dict 包含全部 10 个必需键 | 断言 keys 集合 | FR-04 |
| AC-02-05 | weather_features_available 为 true 时 weather_columns 非空、missing_rate_by_column 含对应列名 | 断言类型和长度 | FR-04 |
| AC-02-06 | weather_features_available 为 false 时 weather_columns 为空列表、missing_rate_by_column 为空字典 | 降级场景断言 | FR-04, D-002@v1 |
| AC-02-07 | overall_missing_rate 在 0.0-1.0 范围内，且为各列缺失率的均值 | 断言范围和数学关系 | FR-04 |
| AC-02-08 | time_range 包含 start、end、freq 三个子字段，值类型正确（str 或 null） | 断言子字段存在性 | FR-04 |
| AC-02-09 | timezone 为 "UTC"、"Asia/Shanghai" 或 "unknown"，取决于 timestamp 时区类型 | 断言可选值集合 | FR-04 |
| AC-02-10 | coverage 包含 total_points、weather_covered_points、coverage_ratio，ratio 范围 0.0-1.0 | 断言子字段存在性和范围 | FR-04 |
| AC-02-11 | notes 是字符串列表；降级场景下至少包含一条说明原因的 note | 断言类型和长度下限 | FR-02, D-002@v1 |
| AC-02-12 | feature_df 缺少 timestamp 列时，timezone 返回 "unknown"，coverage 不抛异常 | 构造缺失 timestamp 的 feature_df | FR-04 |
| AC-02-13 | resolve_weather_source 和 build_weather_quality_report 不写文件、不修改全局状态 | 检查函数副作用 | FR-04 |
| AC-02-14 | run_validation 返回 dict 包含 status 和 weather_quality 键，report_paths 为空列表 | 断言返回结构 | FR-02 |
| AC-02-15 | ShandongDataLoader 数据加载失败时，run_validation 不抛异常，返回 status 为 error | 模拟数据文件缺失 | FR-04 |
| AC-02-16 | 未修改 ellectric/pipeline/ 和 ellectric/fetch/ 下任何文件 | diff 检查 | FR-02 |
