---
author: lmr
created_at: 2026-06-28 00:57:11
---

# Weather Tier4 Validation 设计文档

## 背景

Phase 4 持续改进项中，WeatherFetcher Tier4 特征已经接入到 `FeatureEngineer`，但还缺少一次可复现的验证：

1. 数据接入是否正确：字段、时间索引、缺失、覆盖范围、15min 对齐是否符合现有契约。
2. 模型效果是否可量化：Tier1-3 baseline 与 Tier1-4 weather 特征在同一默认数据、同一切分、同一模型配置下的指标差异。
3. 学习者是否能复跑：需要机器可读 JSON 和人类可读 Markdown 报告，而不是只依赖 notebook 手动观察。

现有契约依据：

- `docs/Ellectric/modules/feature-engineer.md:14` 定义 `add_tier4_weather_features(...)`。
- `docs/Ellectric/modules/feature-engineer.md:23` 定义 weather 来源优先级：显式 `weather_df` → parquet cache → Open-Meteo 抓取 → 降级无 weather 列。
- `docs/Ellectric/scan/ARCHITECTURE.md:217` 明确 Tier4 是可选增强层，不保证预测精度提升。
- `ellectric/pipeline/features.py:57` 定义默认 weather cache。
- `ellectric/pipeline/shandong_loader.py:131` 定义默认山东 15min 数据路径。

## 设计目标

- 提供一个可复现脚本入口，运行默认山东 15min 数据上的 Weather Tier4 验证。
- 输出 weather 数据质量检查结果：字段、时间范围、时区、缺失率、对齐后空值、覆盖范围、weather 特征列清单。
- 输出 baseline vs Tier4 指标对比：MAE、RMSE、MAPE、样本数、特征数、指标 delta。
- 输出两类报告：JSON 用于自动化消费，Markdown 用于学习与归档。
- 保持首轮验证为报告式，不设置硬性精度提升阈值。
- 保持现有 feature/forecast/data loader API 兼容。

## 非目标

- 不新增或更换天气数据源。
- 不把 Weather Tier4 改成必选特征。
- 不要求 Weather Tier4 必须提升精度。
- 不改动真实交易、仿真或 LLM 接口。
- 不新增 notebook-only 流程作为唯一验证方式。
- 不引入在线服务或后台进程。
- 不重训或持久化生产模型。

## 拆分判断

无需拆分。

本变更是单一验证闭环：默认数据加载 → Tier4 数据质量检查 → baseline/Tier4 实验 → 报告输出 → 测试。它不包含 3 个以上可独立交付功能模块，不涉及多角色视图，也不是模板批量生成任务。

## 总体方案

### Wave 1: 验证脚本与报告结构

新增 `ellectric/scripts/validate_weather_tier4.py`。脚本负责加载默认山东数据，先显式解析 weather 来源（cache / fetch / degraded），再按现有 `FeatureEngineer` 契约生成 Tier1-3 baseline 和 Tier1-4 weather 特征，并输出固定结构报告。脚本默认写入 `ellectric/reports/weather_tier4/`，包含：

- `weather_tier4_validation.json`
- `weather_tier4_validation.md`

JSON 作为后续自动化验收基础；Markdown 面向学习者，解释数据质量和模型指标变化。

### Wave 2: 数据质量检查

脚本内实现小而明确的检查函数：

- 输入数据行数、时间范围、频率推断。
- weather cache 是否存在、是否读取成功、是否触发抓取、是否降级。
- weather 来源由脚本显式判定，不依赖 `FeatureEngineer` 内部日志反推。
- weather 原始列清单与 Tier4 合并后实际 weather 列清单。
- weather 时间索引类型、时区、最小/最大时间戳。
- 合并后 weather 列缺失率。
- 合并后 weather 列是否覆盖负荷数据主要时间范围。

检查只报告，不阻断；除非默认数据本身无法加载或训练所需列缺失。

### Wave 3: Baseline vs Tier4 实验

使用同一默认数据、同一 `XGBoostForecaster` 配置、同一 `TimeSeriesSplit` 语义：

- baseline：Tier1 + Tier2 + Tier3。
- weather：Tier1 + Tier2 + Tier3 + Tier4。
- `sample_count` 表示参与交叉验证评估的 actual/prediction 数量；`input_rows` 表示原始输入行数。

`XGBoostForecaster.train_evaluate()` 已返回 predictions 和 actuals；脚本在其基础上计算 MAE、RMSE、MAPE，不需要修改 forecaster。若 Tier4 降级后没有 weather 列，报告中明确记录 `weather_features_available=false`，并仍输出 baseline 结果。

### Wave 4: 测试与文档补充

新增测试覆盖：

- 报告 schema 稳定。
- 无 weather 数据时降级并写入降级原因。
- 显式 `weather_df` 或临时 cache 时能产生 weather 列和质量指标。
- 指标 delta 计算正确。

可选更新模块文档，补充验证脚本入口与报告产物路径。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/scripts/validate_weather_tier4.py` | Weather Tier4 验证脚本，输出 JSON/Markdown 报告 |
| 新增 | `tests/test_weather_tier4_validation.py` | 验证脚本的报告 schema、降级、指标 delta 测试 |
| 修改 | `docs/Ellectric/modules/feature-engineer.md` | 补充 Weather Tier4 验证入口和报告产物说明 |
| 生成 | `ellectric/reports/weather_tier4/weather_tier4_validation.json` | 脚本运行后生成的机器可读报告，不作为源码核心文件 |
| 生成 | `ellectric/reports/weather_tier4/weather_tier4_validation.md` | 脚本运行后生成的人类可读报告，不作为源码核心文件 |

## 接口定义

### 脚本入口

```python
python ellectric/scripts/validate_weather_tier4.py \
  --output-dir ellectric/reports/weather_tier4 \
  --start 2024-01-01 \
  --end 2026-01-14
```

参数：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--output-dir` | `ellectric/reports/weather_tier4` | 报告输出目录 |
| `--start` | `None` | 可选起始日期；默认使用 loader 默认范围 |
| `--end` | `None` | 可选结束日期；默认使用 loader 默认范围 |
| `--weather-cache` | `None` | 可选 weather cache 路径；默认走 `FeatureEngineer` 默认 cache |
| `--no-fetch` | `False` | 禁止 cache miss 时抓取天气数据，用于离线复现 |

### 新增函数

```python
def run_validation(
    start: str | None = None,
    end: str | None = None,
    output_dir: str | Path = "ellectric/reports/weather_tier4",
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    ...
```

职责：执行完整验证并写报告。

```python
def build_weather_quality_report(
    load_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    weather_columns: list[str],
    weather_source: str,
) -> dict:
    ...
```

职责：汇总 weather 数据质量指标。

```python
def run_ablation_experiment(
    load_df: pd.DataFrame,
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    ...
```

职责：运行 baseline vs Tier4 对比实验。

```python
def compute_metrics(actuals: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    ...
```

职责：计算 MAE、RMSE、MAPE。

```python
def write_reports(result: dict, output_dir: str | Path) -> dict[str, str]:
    ...
```

职责：写 JSON 和 Markdown 报告，返回路径。

## 数据模型

### JSON 报告结构

```json
{
  "metadata": {
    "generated_at": "2026-06-28T00:00:00Z",
    "data_source": "shandong",
    "data_version": "shandong_2024-2026_15min_v1",
    "time_config": {"freq": "15min", "points_per_day": 96},
    "start": "2024-01-01T00:00:00+00:00",
    "end": "2026-01-14T00:00:00+00:00"
  },
  "weather_quality": {
    "weather_source": "cache|fetch|explicit|degraded",
    "weather_features_available": true,
    "weather_columns": ["temp_jinan"],
    "weather_column_count": 12,
    "missing_rate_by_column": {"temp_jinan": 0.0},
    "overall_missing_rate": 0.0,
    "notes": []
  },
  "experiments": {
    "baseline_tier3": {
      "feature_count": 11,
      "input_rows": 71520,
      "sample_count": 10000,
      "metrics": {"mae": 0.0, "rmse": 0.0, "mape": 0.0}
    },
    "weather_tier4": {
      "feature_count": 23,
      "input_rows": 71520,
      "sample_count": 10000,
      "metrics": {"mae": 0.0, "rmse": 0.0, "mape": 0.0}
    },
    "delta": {
      "mae_delta": 0.0,
      "rmse_delta": 0.0,
      "mape_delta": 0.0,
      "mae_delta_pct": 0.0
    }
  },
  "interpretation": {
    "hard_threshold_applied": false,
    "summary": "Tier4 weather validation completed as report-only evaluation."
  }
}
```

## 兼容策略

- 不修改 `FeatureEngineer.add_tier4_weather_features(...)` 的现有签名。
- 不修改 `prepare_features(...)` 的默认行为。
- 不修改 `XGBoostForecaster.train_evaluate(...)`，脚本基于返回的 predictions/actuals 计算扩展指标。
- 未运行新脚本时，现有 notebooks、API、CLI、测试行为不变。
- weather cache 缺失或 Open-Meteo 失败时，遵循现有降级语义：返回无 weather 列，并在报告中记录。
- 生成报告属于派生产物；删除后可重新运行脚本生成。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 默认山东 CSV 在本地不存在，脚本无法运行完整实验 | P1 | 复用 `ShandongDataLoader` 的明确错误；报告设计不隐藏数据缺失 |
| R-02 | Open-Meteo 网络不可用导致 Tier4 无 weather 列 | P1 | 优先使用 cache；支持 `--no-fetch`；报告记录 degraded |
| R-03 | Weather 特征未提升精度，被误读为失败 | P1 | 报告明确 hard_threshold_applied=false，解释 Tier4 是可选增强 |
| R-04 | 实验运行时间较长 | P2 | 脚本参数支持 start/end 缩小窗口；测试使用小样本和 fake weather |
| R-05 | MAPE 遇到接近 0 的 actual 产生异常值 | P2 | `compute_metrics` 对 0 值做 mask 或输出 `null` 并记录 notes |

## 决策追踪

- D-001@v1：报告式验证优先于硬阈值验收。
  - 覆盖章节：设计目标、Wave 3、JSON 报告结构、风险 R-03。
  - 覆盖需求：输出可复现实验报告，指标只报告不硬性判失败。
- D-002@v1：Tier4 是可选增强，不保证精度提升。
  - 覆盖章节：背景、非目标、兼容策略、风险 R-02/R-03。
  - 覆盖需求：weather 缺失时降级并记录，不破坏现有管道。
- D-003@v1：采用方案B，可复现脚本 + 报告产物。
  - 覆盖章节：总体方案、文件变更清单、接口定义。
  - 覆盖需求：比 notebook-only 更可复现，比测试-only 更满足学习报告目标。

## 自审

| 检查项 | 结果 | 说明 |
|---|---|---|
| 需求覆盖 | 通过 | 覆盖接入正确性、精度影响评估、可复现实验报告 |
| 决策覆盖 | 通过 | design.md 引用 D-001@v1、D-002@v1、D-003@v1 |
| 架构一致性 | 通过 | 复用 `ShandongDataLoader`、`FeatureEngineer`、`XGBoostForecaster` |
| 真实性 | 通过 | 现有类/函数路径来自真实代码；新增函数均标注为新增 |
| YAGNI | 通过 | 未新增数据源、服务、硬阈值、生产模型持久化 |
| 验收可测试 | 通过 | 明确报告 schema、降级、指标 delta 测试 |
| 非目标清晰 | 通过 | 明确不做在线服务、硬阈值、交易/仿真变更 |
| 兼容策略 | 通过 | 不改现有公开 API，新增脚本为旁路验证 |
| 风险识别 | 通过 | 覆盖数据缺失、网络失败、指标误读、运行耗时、MAPE 边界 |

自审结论：通过。

## Design Grill Result

status: passed

### Cross-Check Matrix

| ID | 层级 | 交叉点 | 证据 A | 证据 B | 结论 | 决策 |
|---|---|---|---|---|---|---|
| X-001 | consistency | Tier4 降级语义 vs 报告式验收 | `features.py:277-282` | design 兼容策略 | 一致：降级不阻断，报告记录 | D-002@v1 |
| X-002 | feasibility | weather 来源判定 vs FeatureEngineer 返回值 | `features.py:235-301` | design Wave 1/2 | 已修正：脚本显式解析来源，不从日志反推 | D-003@v1 |
| X-003 | definition | sample_count 含义 | `forecaster.py:369-382` | JSON schema | 已修正：sample_count 为 CV actual/pred 数量，input_rows 单独记录 | D-003@v1 |
| X-004 | compatibility | 新脚本 vs 现有 API | `tests/test_weather_features.py` | design 兼容策略 | 一致：新增旁路脚本，不改现有签名 | D-002@v1 |

### Question Distribution

| 分类 | 数量 | 含义 |
|---|---|---|
| immediately_answered | 2 | weather 来源判定、sample_count 定义已由代码查证并修正 |
| needs_thinking | 0 | 无需用户判断 |
| unresolved | 0 | 无未解决设计漏洞 |

### Unresolved Blockers

无 P0/P1 blocker。
