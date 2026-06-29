---
author: lmr
created_at: 2026-06-29 20:40:04
---

# Weather Tier4 特征精度影响量化 — 设计文档

## 背景

项目已经完成 Weather Tier4 接入与首轮验证脚本：`ellectric/scripts/validate_weather_tier4.py` 会加载山东 15min 数据、合并 `ellectric/data/shandong/weather_2024-2026.parquet`、运行 baseline vs Tier4 ablation，并输出 `ellectric/reports/weather_tier4/weather_tier4_validation.json` 与 `.md`。

但当前仍有两个影响“精度影响量化”可信度的问题：

1. 现有报告产物是 degraded/fake-scale 状态，`input_rows=96` 且无 weather 指标，不能代表山东 745 天 × 96 点全量数据。
2. `run_ablation_experiment()` 的 weather 分支用 “除 timestamp/load_mw 外全部列” 作为特征，山东 loader 原始列可能包含价格、预测、出力等非 weather 字段；这会把 Weather Tier4 的影响与其他原始字段混在一起，不能回答“天气特征本身有没有贡献”。

本变更目标是把验证从“脚本可跑、报告结构可用”推进到“全量山东数据上可复现、可解释、只隔离 weather 变量的精度影响量化”。

## 设计目标

- 在默认山东 15min 全量数据上输出真实 baseline_tier3 vs weather_tier4 指标。
- 保证 ablation 只比较 “Tier1-3 特征” 与 “Tier1-3 + 实际 weather 列”，不混入价格、出力、预测等 raw columns。
- 报告明确区分负荷数据源 (`data_source=shandong`) 与天气来源 (`weather_source=cache|fetch|explicit|degraded`)。
- 报告记录 full-run 证据：输入行数、样本数、特征数、weather 列名、缺失率、delta、运行日志路径。
- 离线可复现：默认优先使用本地 weather cache；测试不触网。
- 保持 Weather Tier4 为可选增强层，不设置硬性精度提升阈值。

## 非目标

- 不新增天气数据源，不更换 Open-Meteo。
- 不改 `WeatherFetcher` 抓取逻辑。
- 不把 Tier4 weather 改成默认必选训练特征。
- 不调参、不做模型选择、不训练持久化生产模型。
- 不把价格、风光出力、日前预测等 raw columns 纳入本次“weather impact”实验。
- 不改 FastAPI、CLI、LLM、RL、backtester 流程。
- 不引入定时任务、daemon、队列或实时数据调度。

## 拆分判断

无需拆分为批量变更。本变更围绕单一验证闭环：修正 ablation 特征选择 → 增强报告语义 → 更新测试 → 跑 full-run 证据。涉及 1 个脚本、1 个测试文件、1 个模块文档和生成报告产物，边界清晰，按 Wave 顺序执行即可。

## 总体方案

### Wave 1: 修正 ablation 特征隔离

修改 `ellectric/scripts/validate_weather_tier4.py::run_ablation_experiment()`：

- baseline 继续使用 `FeatureEngineer().get_feature_columns("tier3")` 对应的 Tier1-3 列。
- weather 分支使用一个专用 `FeatureEngineer` 实例，手动顺序调用 `add_tier1_features()`、`add_tier2_features()`、`add_tier3_features()`、`add_tier4_weather_features()`，再读取该实例的 `_weather_columns` 作为实际 weather 列清单。
- 禁止用 “feature_df 除 timestamp/load_mw 外全部列” 推断 weather 特征，因为 `prepare_features()` 会保留输入 DataFrame 的 raw columns。
- `X_weather` 必须只包含 `tier3_cols + weather_cols_detected`。
- `weather_feature_count = len(tier3_cols) + len(weather_cols_detected)`。
- 若没有 weather 列，weather 分支 degraded，baseline 仍输出。

核心原则：两组实验除了 weather 列之外，其他特征完全一致。

### Wave 2: 报告语义与 full-run 证据

增强 `run_validation()` 和 report writer：

- `metadata.data_source` 固定为 `shandong`。
- `metadata.weather_source` 记录 weather 来源；保留 `weather_quality.weather_source`。
- `metadata.input_rows` 记录 `len(load_df)`。
- `metadata.report_scope` 记录 `full_dataset|custom_range`。
- `metadata.log_path` 记录 full-run 日志路径；`report_paths` 保持 JSON/Markdown 路径。
- `experiments.notes` 中明确写出是否隔离 raw columns。
- Markdown 增加一段 “Impact Conclusion”：说明 weather MAE delta 正负、是否改善、以及 report-only 不设门槛。
- 运行日志由验证命令重定向/tee 到 `ellectric/reports/weather_tier4/weather_tier4_impact.log`，作为 full-run 证据，不写 `/tmp`。

### Wave 3: 测试覆盖

更新 `tests/test_weather_tier4_validation.py`：

- 新增测试：当 input DataFrame 含 raw columns（如 `rt_price`、`da_price`、`wind_actual_mw`）时，weather 分支传给 forecaster 的 X columns 不包含这些 raw columns。
- 新增测试：weather 分支 columns 等于 Tier3 columns + fake weather columns。
- 更新 metadata schema 测试，允许/要求 `weather_source`、`input_rows`、`report_scope`、`log_path`。
- 保留 degraded path、write_reports、compute_metrics、delta 测试。

### Wave 4: 文档与 full-run 验证

- 更新 `docs/Ellectric/modules/feature-engineer.md` 的 Weather Tier4 验证段落，说明本验证是隔离 weather 特征的 ablation。
- 运行 targeted tests：`rtk pytest tests/test_weather_tier4_validation.py`。
- 运行脚本生成真实报告并保留日志：`python ellectric/scripts/validate_weather_tier4.py --no-fetch --output-dir ellectric/reports/weather_tier4 2>&1 | tee ellectric/reports/weather_tier4/weather_tier4_impact.log`。
- 若 full-run 太慢或依赖缺失，保留错误日志并修复；不以 degraded fake report 作为完成证据。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `ellectric/scripts/validate_weather_tier4.py` | 修正 weather ablation 特征选择，增强 metadata/Markdown/log 语义 |
| 修改 | `tests/test_weather_tier4_validation.py` | 覆盖 raw columns 不泄漏、metadata schema、报告结构 |
| 修改 | `docs/Ellectric/modules/feature-engineer.md` | 说明 Weather Tier4 impact quantification 的隔离实验语义 |
| 生成 | `ellectric/reports/weather_tier4/weather_tier4_validation.json` | full-run JSON 报告 |
| 生成 | `ellectric/reports/weather_tier4/weather_tier4_validation.md` | full-run Markdown 报告 |
| 生成 | `ellectric/reports/weather_tier4/weather_tier4_impact.log` | full-run 运行日志，忽略或不强制纳入 git |

## 接口定义

### `run_ablation_experiment`

```python
def run_ablation_experiment(
    load_df: pd.DataFrame,
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    ...
```

返回结构保持兼容：

```python
{
    "baseline_tier3": {
        "feature_count": int,
        "input_rows": int,
        "sample_count": int,
        "metrics": {"mae": float | None, "rmse": float | None, "mape": float | None},
    },
    "weather_tier4": {
        "feature_count": int,
        "input_rows": int,
        "sample_count": int,
        "metrics": {"mae": float | None, "rmse": float | None, "mape": float | None},
        "weather_columns": list[str],
    },
    "delta": {
        "mae_delta": float | None,
        "rmse_delta": float | None,
        "mape_delta": float | None,
        "mae_delta_pct": float | None,
    },
    "notes": list[str],
}
```

新增 `weather_tier4.weather_columns` 为向后兼容扩展；旧消费者读取原字段不受影响。

### `run_validation`

```python
def run_validation(
    start: str | None = None,
    end: str | None = None,
    output_dir: str = "ellectric/reports/weather_tier4",
    weather_cache: str | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    ...
```

返回结构保持顶层 `status / metadata / weather_quality / experiments / interpretation / report_paths`，扩展 metadata：

```python
"metadata": {
    "generated_at": str,
    "data_source": "shandong",
    "data_version": str,
    "weather_source": "cache|fetch|explicit|degraded",
    "input_rows": int,
    "report_scope": "full_dataset|custom_range",
    "log_path": str | None,
    "time_config": {"freq": "15min", "points_per_day": 96},
    "start": str | None,
    "end": str | None,
}
```

### CLI

现有 CLI 参数保持：

```bash
python ellectric/scripts/validate_weather_tier4.py \
  --output-dir ellectric/reports/weather_tier4 \
  --weather-cache ellectric/data/shandong/weather_2024-2026.parquet \
  --no-fetch
```

不新增必填参数。

## 数据模型

不涉及数据库或持久化 schema。报告 JSON 是文件型数据模型，扩展字段必须满足：

- `metadata.data_source` 表示负荷数据源，不再复用 weather source。
- `metadata.weather_source` 与 `weather_quality.weather_source` 一致。
- `metadata.log_path` 指向 `ellectric/reports/weather_tier4/weather_tier4_impact.log` 或在非 full-run 单元测试中为 `None`。
- `experiments.weather_tier4.weather_columns` 列出本次真正加入模型的 weather 列。
- `experiments.weather_tier4.feature_count == baseline_tier3.feature_count + len(weather_columns)`。
- `delta.mae_delta = weather_tier4.metrics.mae - baseline_tier3.metrics.mae`；负值表示 weather 改善 MAE。

## 兼容策略

- 不修改 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster`、`ShandongDataLoader` 的公开签名。
- 现有 `run_validation()`、`run_ablation_experiment()` 参数保持不变。
- JSON 报告只增加字段，不删除旧字段。
- weather cache 缺失且 `--no-fetch` 时仍 degraded，不阻断 baseline。
- 未配置新功能时，普通 forecast/API/CLI/RL 行为不变。
- 报告路径沿用 `ellectric/reports/weather_tier4/`。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 全量 XGBoost 两次训练耗时较长 | P1 | 保持 targeted unit tests 快速；full-run 作为最终验证并写日志 |
| R-02 | weather cache 缺失导致 degraded | P1 | 使用已有 `ellectric/data/shandong/weather_2024-2026.parquet`；验证命令带 `--no-fetch` 避免网络不确定性 |
| R-03 | raw columns 泄漏导致 weather impact 被高估 | P0 | 测试断言 raw columns 不进入 weather forecaster；只允许 Tier3 + weather columns |
| R-04 | 报告字段变更破坏旧测试 | P2 | 只做兼容扩展，更新 schema 测试 |
| R-05 | Weather Tier4 指标不改善 | P2 | 作为事实报告，不设硬阈值；Markdown 明确解释负/正 delta 含义 |
| R-06 | 本地环境缺 xgboost/sklearn/pyarrow | P1 | 先跑 unit tests 暴露依赖；失败则报告并修复依赖/命令路径，不伪造报告 |

## 决策追踪

- D-001@v1 覆盖：非目标、设计目标、Wave 2、R-05。首轮量化继续 report-only，不设置精度提升硬门槛。
- D-002@v1 覆盖：Wave 1、接口定义、数据模型、R-03。Weather impact 实验必须隔离 raw columns。
- D-003@v1 覆盖：Wave 2、Wave 4、文件变更清单。full-run 证据写入 `ellectric/reports/weather_tier4/`。
- D-004@v1 覆盖：Wave 4、兼容策略、R-02。最终验证优先离线 cache，不依赖网络。

无未解决的 D-xxx 决策。

## 自审

| 检查项 | 结果 | 说明 |
|---|---|---|
| 需求覆盖 | 通过 | 覆盖“Weather Tier4 特征精度影响量化”：全量真实报告、指标 delta、weather-only ablation |
| 决策覆盖 | 通过 | design.md 引用所有当前版本 D-001@v1~D-004@v1 |
| 约束一致性 | 通过 | 使用山东 15min、TimeConfig、现有报告目录；不引入生产交易或实时调度 |
| 真实性 | 通过 | 文件、函数、报告路径均来自当前代码；新增字段已标注为扩展 |
| YAGNI | 通过 | 不调参、不新增服务、不扩展数据源 |
| 验收标准 | 通过 | tests + full-run script + JSON/Markdown/log 可验证 |
| 非目标清晰 | 通过 | 明确不做模型选择、默认必选 Tier4、API/RL 变更 |
| 兼容策略 | 通过 | 公开函数参数保持，JSON 只增字段 |
| 风险识别 | 通过 | 覆盖耗时、cache、raw column 泄漏、依赖、指标不改善 |
| 生命周期契约表 | 不适用 | 不涉及 session/lease/daemon/lifecycle/heartbeat |
