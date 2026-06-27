---
author: lmr
created_at: 2026-06-28 01:11:57
id: task-05
title: 新增验证脚本测试（覆盖：FR-02, FR-03, FR-04, FR-05, D-001@v1, D-002@v1, D-003@v1）
priority: P0
estimated_hours: 2
depends_on: [task-01, task-02, task-03, task-04]
blocks: [task-07]
requirement_ids: [FR-02, FR-03, FR-04, FR-05]
decision_ids: [D-001@v1, D-002@v1, D-003@v1]
allowed_paths:
  - tests/test_weather_tier4_validation.py
---

# task-05: 新增验证脚本测试（覆盖：FR-02, FR-03, FR-04, FR-05, D-001@v1, D-002@v1, D-003@v1）

## 修改文件

| 操作 | 文件路径 |
|------|----------|
| 新增 | `tests/test_weather_tier4_validation.py` |
| 只读参考 | `ellectric/scripts/validate_weather_tier4.py` — 通过 `importlib.util.spec_from_file_location` 加载 |

只新增测试文件，不修改任何已有文件。测试覆盖 `validate_weather_tier4.py` 中 task-02/03/04 实现的所有函数。现有 `tests/test_weather_features.py` 和 `tests/test_time_resolution_15min.py` 不被修改。

## 覆盖来源

- **FR-02**（weather 数据质量报告）: 测试 `build_weather_quality_report` 的输出 schema、缺失率计算、timezone 推断、coverage 字段和 notes 构造。
- **FR-03**（Baseline vs Tier4 指标对比）: 测试 `compute_metrics` 的 MAE/RMSE/MAPE 计算正确性；测试 `run_ablation_experiment` 的返回结构包含 baseline_tier3 和 weather_tier4 两个子字段及 delta。
- **FR-04**（Report-only 验收语义）: 测试 degraded 路径下脚本不抛异常、报告包含 `weather_features_available=false`、`hard_threshold_applied=false`。
- **FR-05**（报告格式稳定）: 测试 `write_reports` 写入的 JSON 文件包含 `metadata`、`weather_quality`、`experiments`、`interpretation` 四个顶层字段；Markdown 报告包含关键指标文本。
- **D-001@v1**（报告式验证优先于硬阈值）: 测试 `hard_threshold_applied` 字段为 `false`；指标 delta 为负值时不被测试判定为失败。
- **D-002@v1**（Tier4 可选增强）: 测试 weather 降级场景的完整路径：degraded 来源 → `weather_features_available=false` → 脚本仍输出包含 baseline 的报告。
- **D-003@v1**（可复现脚本 + 报告产物）: 测试 `run_validation` 使用 monkeypatched loader 和实验路径时返回符合 schema 的 dict；测试 `write_reports` 实际写文件。

## 实现要求

1. 创建 `tests/test_weather_tier4_validation.py`，包含模块级 docstring 说明测试覆盖的 FR 和决策。全部测试使用 fake 小 DataFrame（`_sample_load_df`、`_fake_weather_hourly` 等辅助函数）和 monkeypatch，不依赖真实网络和完整默认数据集。

2. 辅助函数（测试内部私有，不导出）:
   - `_sample_load_df(n)` → 与 `test_weather_features.py` 同模式：`pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")`，返回含 `timestamp` 和 `load_mw` 的 DataFrame。
   - `_fake_weather_hourly()` → 与 `test_weather_features.py` 同模式：48 行小时级数据，含 `temp_jinan`、`ghi_jinan`、`wind_speed_jinan` 等列，DatetimeIndex 带 UTC 时区。
   - `_minimal_report_dict()` → 返回符合 JSON 报告 schema 的最小有效 dict，用于 `write_reports` 测试。

3. 测试分组（按 Group 组织，用注释区隔，每组对应一到多个 FR）:

   **Group A: compute_metrics (FR-03)**
   - `test_compute_metrics_basic`: 传入已知 actuals 和 predictions 数组，断言 MAE/RMSE/MAPE 值与手动计算一致。使用 `np.array([100.0, 200.0, 300.0])` 和 `np.array([110.0, 190.0, 290.0])` 手动算出 MAE=10.0, RMSE≈11.547, MAPE≈5.56%。
   - `test_compute_metrics_identical`: actuals == predictions 时 MAE=0, RMSE=0, MAPE=0。
   - `test_compute_metrics_zero_actual_mask`: actuals 包含 0 值时 MAPE 对该点 mask 不贡献，分母安全不抛异常。确认返回 dict 中 `mape` 为剩余有效点的 MAPE（无除零错误）。
   - `test_compute_metrics_all_zero_actual`: 全部 actuals 为 0 时 MAPE 返回 `None`（或 `null`），notes 包含 "all actual values are zero; MAPE undefined"。

   **Group B: delta sign and consistency (FR-03, D-001@v1)**
   - `test_delta_calculation_positive`: baseline_mae=10.0, weather_mae=8.0 → mae_delta=-2.0, mae_delta_pct=-20.0。正收益为负值（越低越好）。
   - `test_delta_calculation_negative`: baseline_mae=8.0, weather_mae=10.0 → mae_delta=+2.0, mae_delta_pct=+25.0。负收益为正值。
   - `test_delta_pct_from_baseline`: `mae_delta_pct = (weather_mae - baseline_mae) / baseline_mae * 100` 语义验证。
   - `test_delta_no_division_by_zero`: baseline_mae=0 时 mae_delta_pct 返回 `None` 而非抛异常。

   **Group C: report schema (FR-02, FR-05)**
   - `test_report_schema_top_level_keys`: `write_reports` 使用的报告 dict 包含 `metadata`、`weather_quality`、`experiments`、`interpretation` 四个顶层键。
   - `test_report_schema_weather_quality_keys`: `weather_quality` 包含 `weather_source`、`weather_features_available`、`weather_columns`、`weather_column_count`、`missing_rate_by_column`、`overall_missing_rate`、`time_range`、`timezone`、`coverage`、`notes`。
   - `test_report_schema_experiments_keys`: `experiments` 包含 `baseline_tier3`、`weather_tier4`、`delta` 三个子键。
   - `test_report_schema_experiment_subkeys`: `baseline_tier3` 和 `weather_tier4` 各包含 `feature_count`、`input_rows`、`sample_count`、`metrics`；`metrics` 包含 `mae`、`rmse`、`mape`。
   - `test_report_schema_delta_keys`: `delta` 包含 `mae_delta`、`rmse_delta`、`mape_delta`、`mae_delta_pct`。
   - `test_report_schema_metadata_keys`: `metadata` 包含 `generated_at`、`data_source`、`data_version`、`time_config`、`start`、`end`。
   - `test_report_schema_interpretation_keys`: `interpretation` 包含 `hard_threshold_applied`、`summary`。
   - `test_report_hard_threshold_false`: `hard_threshold_applied` 值为 `false`（布尔值，非字符串）。

   **Group D: weather degraded path (FR-02, FR-04, D-002@v1)**
   - `test_weather_degraded_report_structure`: `build_weather_quality_report` 在 weather_columns 为空时返回 `weather_features_available=false`、`weather_columns=[]`、`weather_column_count=0`、`missing_rate_by_column={}`、`overall_missing_rate=0.0`。
   - `test_weather_degraded_with_source_degraded`: 传入 `weather_source="degraded"` 且 weather_columns=[]，notes 至少包含一条说明。
   - `test_weather_degraded_does_not_block_experiment`: `run_ablation_experiment` 在 fetch_if_missing=False 且无 cache 时仍返回包含 `baseline_tier3` 的 dict，`weather_tier4` 的 `sample_count` 为 0（或 metrics 为 null）但不抛异常。

   **Group E: write_reports file output (FR-05)**
   - `test_write_reports_creates_json`: 传入 `_minimal_report_dict()` 和 tmp_path，运行 `write_reports` 后确认 `{output_dir}/weather_tier4_validation.json` 存在且为有效 JSON。
   - `test_write_reports_creates_markdown`: 同上，确认 `{output_dir}/weather_tier4_validation.md` 存在。
   - `test_write_reports_json_content`: 从写入的 JSON 文件反序列化，断言 `metadata`、`weather_quality`、`experiments`、`interpretation` 存在且值与输入一致。
   - `test_write_reports_markdown_includes_metrics`: 读取写入的 Markdown 文件，断言包含 "MAE"、"RMSE"、"MAPE"、"baseline"、"weather" 等关键词。
   - `test_write_reports_creates_directory`: output_dir 不存在时 `write_reports` 创建目录（`os.makedirs`）。

   **Group F: run_validation integration (FR-02, FR-03, FR-04, FR-05, D-003@v1)**
   - `test_run_validation_returns_dict`: monkeypatch ShandongDataLoader 返回 fake load_df，monkeypatch `resolve_weather_source` 返回 `("explicit", fake_weather_df)`，monkeypatch `run_ablation_experiment` 返回标准实验 dict，monkeypatch `write_reports` 返回路径。调用 `run_validation` 后返回 dict 包含 `status`（非 error）、`weather_quality`、`experiments`、`report_paths`。
   - `test_run_validation_data_load_failure`: monkeypatch ShandongDataLoader.load_data 抛 FileNotFoundError，调用 `run_validation` 返回 dict 含 `status="error"`，不抛异常。
   - `test_run_validation_degraded_path`: monkeypatch `resolve_weather_source` 返回 `("degraded", None)`，验证 `run_validation` 返回 dict 的 `weather_quality.weather_features_available` 为 false，`experiments` 仍然包含 `baseline_tier3` 且不为 null。

4. 测试数据构造和 mock 策略：
   - 所有测试不使用真实文件路径（cache、数据目录等），使用 `tmp_path` fixture 或 `monkeypatch`。
   - 对于 `run_validation` 集成测试，mock 全部外部依赖（loader、weather source、experiment、report），只测试编排逻辑和返回结构。
   - `compute_metrics` 和 `build_weather_quality_report` 是纯函数，无需 mock，直接传假数据测试。
   - `write_reports` 测试使用 `tmp_path` 作为输出目录。

5. 测试独立性：每个测试函数独立构造数据，不共享全局 fixture 或状态。`_sample_load_df` 和 `_fake_weather_hourly` 在每个测试函数内调用。

## 接口定义

测试文件 `tests/test_weather_tier4_validation.py` 不导出公共 API。测试内部通过 `importlib.util.spec_from_file_location` 或 `sys.path.insert` 加载 `ellectric/scripts/validate_weather_tier4.py`（`ellectric/scripts/` 不是 package，不能包导入），然后从中导入以下函数签名：

```python
def compute_metrics(
    actuals: np.ndarray, predictions: np.ndarray
) -> dict[str, float | None]:
    ...

def run_ablation_experiment(
    load_df: pd.DataFrame,
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    ...

def build_weather_quality_report(
    load_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    weather_columns: list[str],
    weather_source: str,
) -> dict:
    ...

def write_reports(result: dict, output_dir: str | Path) -> dict[str, str]:
    ...

def run_validation(
    start: str | None = None,
    end: str | None = None,
    output_dir: str | Path = "ellectric/reports/weather_tier4",
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    ...
```

## 边界处理

1. **compute_metrics 的 MAPE 零值**: actuals 包含 0 时，MAPE 计算对该点做 mask（不贡献分子不分母），非抛异常。`test_compute_metrics_zero_actual_mask` 验证 5 个点中 1 个为 0 时 MAPE 反映剩余 4 个有效点的平均百分比误差。`test_compute_metrics_all_zero_actual` 验证所有 actuals 为 0 时 MAPE 返回 `None`（non-None 值会被 Python 判为失败），notes 包含解释。

2. **compute_metrics 空数组**: actuals 或 predictions 为空时，返回 dict 中 MAE/RMSE/MAPE 均为 `None`（防止下游消费 `float` 时出错），不抛 `ValueError`。

3. **delta 符号约定**: `mae_delta = weather_mae - baseline_mae`，负值表示 weather 优于 baseline（越低越好）。`mae_delta_pct = delta / baseline_mae * 100`。所有 test 断言使用 math.isclose 而非 == 避免浮点精度问题。

4. **delta 除零**: baseline_mae 为 0 时（例如 identical arrays 场景），`mae_delta_pct` 返回 `None` 而非抛 `ZeroDivisionError`。`test_delta_no_division_by_zero` 覆盖。

5. **weather degraded 场景的 notes 非空**: `build_weather_quality_report` 在 `weather_features_available=False` 时 notes 至少包含一条说明原因的条目。`test_weather_degraded_with_source_degraded` 断言 `len(notes) >= 1`。

6. **write_reports 目录创建**: 当 `output_dir` 不存在时，`write_reports` 用 `os.makedirs(output_dir, exist_ok=True)` 创建。`test_write_reports_creates_directory` 断言目录被创建。当 `output_dir` 已存在时，覆盖写入不报错。

7. **write_reports 写入编码**: JSON 文件使用 `utf-8` 编码 + `ensure_ascii=False` 保留中文字符；Markdown 文件使用 `utf-8` 编码。测试断言文件可读且解码正确。

8. **run_validation 数据加载失败不抛异常**: 即使 ShandongDataLoader 找不到文件或数据列为空，`run_validation` 返回 `{"status": "error", "error": "..."}` 而非向上抛异常。`test_run_validation_data_load_failure` 通过 monkeypatch load_data 抛 `FileNotFoundError` 验证。

9. **run_validation 降级路径仍包含 baseline 实验**: 即使 weather 完全不可用，`experiments.baseline_tier3` 仍然存在且 metrics 非 null。`test_run_validation_degraded_path` 通过 monkeypatch `resolve_weather_source` 返回 `("degraded", None)` + monkeypatch `run_ablation_experiment` 返回含 baseline 的 dict 验证。

10. **报告 schema 字段严格匹配**: 测试断言精确的键集合，不允许多余或缺失字段。使用 `assert set(d.keys()) == expected_keys`，如果 design 后续添加新字段，此测试改为 `assert expected_keys.issubset(d.keys())`——但首版用严格相等确保 schema 稳定。

11. **fake DataFrame 列名一致**: `_fake_weather_hourly` 的列名（`temp_jinan`、`ghi_jinan`、`wind_speed_jinan`、`temp_qingdao`、`ghi_qingdao`）与 `test_weather_features.py:28-38` 中的 `_fake_weather_hourly` 保持完全一致，避免测试间理解混淆。

12. **monkeypatch 隔离**: 使用 pytest 内置 `monkeypatch` fixture 而非 `unittest.mock.patch`，确保 mock 在每个测试结束后自动恢复，不影响后续测试。

## 非目标

- ❌ 不修改 `ellectric/scripts/validate_weather_tier4.py` 中的实现代码（测试只 import 和测试）。
- ❌ 不修改 `tests/test_weather_features.py` 和 `tests/test_time_resolution_15min.py`。
- ❌ 不测试 `argparse` 的 CLI 输出格式（task-01 已覆盖）。
- ❌ 不运行真实天气数据抓取或完整默认数据集。
- ❌ 不测试 `ShandongDataLoader`、`FeatureEngineer`、`XGBoostForecaster` 的内部逻辑（其自身测试已覆盖）。
- ❌ 不引入 `unittest.mock` 或 `pytest-mock` 以外的测试依赖（monkeypatch 已足够）。
- ❌ 不进行性能测试或端到端集成测试（task-07 覆盖全流程运行）。
- ❌ 不测试 `XGBoostForecaster.train_evaluate` 在实验中的实际模型训练（`run_ablation_experiment` 在生产代码中调用它，测试中 mock 掉实验器本身）。
- ❌ 不生成或维护测试 fixture 数据文件。
- ❌ 不添加 `conftest.py` 或全局 fixture。

## 参考

- `design.md:86-92` — Wave 4 测试覆盖需求：报告 schema 稳定、降级路径、显式 weather 质量指标、指标 delta。
- `design.md:100` — 新增测试文件 `tests/test_weather_tier4_validation.py`。
- `design.md:141-151` — `build_weather_quality_report` 函数签名和职责。
- `design.md:153-169` — `compute_metrics` 和 `write_reports` 函数签名。
- `design.md:182-226` — JSON 报告完整结构（`weather_quality` 10 字段，`experiments` 3 子键，`delta` 4 子键，`interpretation` 2 字段）。
- `design.md:244-245` — 风险 R-05 处理：MAPE 零值 mask 策略。
- `design.md:248-258` — 决策 D-001@v1（报告式）、D-002@v1（可选增强）、D-003@v1（脚本化）。
- `plan.md:28` — task-05 在 plan 中的描述。
- `plan.md:40` — AC-07 要求新增测试与现有 Weather Tier4 契约测试一起通过。
- `requirements.md:50-52` — FR-03 要求 sample_count 和 input_rows 的区别在测试中验证。
- `requirements.md:62-68` — FR-04 降级语义：`hard_threshold_applied=false` 和 `weather_features_available=false`。
- `requirements.md:74-80` — FR-05 报告结构：四个顶层字段。
- `tests/test_weather_features.py` — 现有 Weather Tier4 契约测试的辅助函数和 mock 风格参考（`_sample_load_df`、`_fake_weather_hourly`、`monkeypatch.setattr` 模式、`caplog` 使用）。
- `tests/test_time_resolution_15min.py` — 现有测试的 fixture 和断言风格参考（`tmp_path` 用法、`monkeypatch` 模式、FakeLoader 模式）。

## TDD 步骤

```text
1. [RED] 创建空测试文件 `tests/test_weather_tier4_validation.py`，运行预期测试命令 `pytest tests/test_weather_tier4_validation.py tests/test_weather_features.py` — 依赖全部失败（collect 0）但环境确认无报错。
2. [GREEN] 写入文件头（docstring + 标准 import）和 Group A compute_metrics 四个测试。实现 `compute_metrics` 并从 `validate_weather_tier4.py` import。运行 `pytest tests/test_weather_tier4_validation.py -k "compute_metrics"` — 全部通过。
3. [RED] 添加 Group B delta 四个测试。运行 `pytest -k "delta"` — 全部失败（函数未实现）。
4. [GREEN] 实现 delta 计算函数（可放在 `validate_weather_tier4.py` 或在测试中用局部函数辅助）。运行通过。
5. [RED] 添加 Group C report schema 八个测试。运行 `-k "report_schema or report_hard"` — 全部失败。
6. [GREEN] 实现 `build_weather_quality_report`、`run_ablation_experiment` 和 `write_reports`（若 task-02/03/04 已完成则无需实现）。运行通过。
7. [RED] 添加 Group D weather degraded 三个测试。运行 `-k "degraded"` — 全部失败。
8. [GREEN] 确保 `build_weather_quality_report` 和 `run_ablation_experiment` 对空 weather_columns 返回正确结构。运行通过。
9. [RED] 添加 Group E write_reports 五个测试。运行 `-k "write_reports"` — 全部失败。
10. [GREEN] 实现 `write_reports` 文件写入逻辑。运行通过。
11. [RED] 添加 Group F run_validation 三个集成测试。运行 `-k "run_validation"` — 全部失败（mock 依赖）。
12. [GREEN] 通过 monkeypatch 编排 `run_validation` 的各 mock 依赖后运行通过。
13. [REFACTOR] 检查测试可读性：确认辅助函数不暴露不必要细节，每组测试有清晰注释区隔，assertion 使用 math.isclose 处理浮点比较。
14. [FINAL] 运行完整命令 `pytest tests/test_weather_tier4_validation.py tests/test_weather_features.py` — 全部通过，新旧测试均绿。
```

## 验收标准

| ID | 标准 | 验证方式 | 关联需求/决策 |
|----|------|----------|---------------|
| AC-05-01 | `compute_metrics` 对已知输入返回正确 MAE/RMSE/MAPE | `test_compute_metrics_basic` 断言 math.isclose | FR-03 |
| AC-05-02 | actuals == predictions 时指标均为 0 | `test_compute_metrics_identical` 断言 | FR-03 |
| AC-05-03 | actuals 含 0 值时 MAPE 安全 mask 不抛异常 | `test_compute_metrics_zero_actual_mask` 断言 | FR-03 |
| AC-05-04 | 全部 actuals 为 0 时 MAPE 返回 None | `test_compute_metrics_all_zero_actual` 断言 `None` | FR-03 |
| AC-05-05 | delta 符号约定正确：weather 优于 baseline 为负值 | `test_delta_calculation_positive/negative` 断言 | FR-03, D-001@v1 |
| AC-05-06 | delta_pct 公式为 `(weather - baseline) / baseline * 100` | `test_delta_pct_from_baseline` 断言 | FR-03 |
| AC-05-07 | baseline_mae=0 时 delta_pct 返回 None 不抛异常 | `test_delta_no_division_by_zero` 断言 | FR-03, D-001@v1 |
| AC-05-08 | 报告 dict 包含 metadata/weather_quality/experiments/interpretation 四个顶层键 | `test_report_schema_top_level_keys` 断言 | FR-05 |
| AC-05-09 | weather_quality 包含全部 10 个必需子字段 | `test_report_schema_weather_quality_keys` 断言 | FR-02, FR-05 |
| AC-05-10 | experiments 包含 baseline_tier3/weather_tier4/delta 三个子键 | `test_report_schema_experiments_keys` 断言 | FR-03, FR-05 |
| AC-05-11 | hard_threshold_applied 值为 false（布尔型） | `test_report_hard_threshold_false` 断言 | FR-04, D-001@v1 |
| AC-05-12 | weather degraded 场景 features_available=false，columns 空列表，missing_rate 空 dict | `test_weather_degraded_report_structure` 断言 | FR-04, D-002@v1 |
| AC-05-13 | degraded 场景 notes 非空 | `test_weather_degraded_with_source_degraded` 断言 | FR-04, D-002@v1 |
| AC-05-14 | write_reports 创建 JSON 文件且内容与输入一致 | `test_write_reports_creates_json` + `_json_content` 断言 | FR-05, D-003@v1 |
| AC-05-15 | write_reports 创建 Markdown 文件含关键指标词 | `test_write_reports_creates_markdown` + `_includes_metrics` 断言 | FR-05, D-003@v1 |
| AC-05-16 | write_reports 自动创建不存在的输出目录 | `test_write_reports_creates_directory` 断言 | FR-05, D-003@v1 |
| AC-05-17 | run_validation 集成测试返回含 weather_quality/experiments/report_paths 的 dict | `test_run_validation_returns_dict` 断言 | FR-02, FR-03, FR-05, D-003@v1 |
| AC-05-18 | run_validation 数据加载失败返回 status="error" 不抛异常 | `test_run_validation_data_load_failure` 断言 | FR-04 |
| AC-05-19 | run_validation degraded 路径仍包含 baseline_tier3 实验 | `test_run_validation_degraded_path` 断言 | FR-04, D-002@v1 |
| AC-05-20 | 全新旧测试一起运行全部通过：`pytest tests/test_weather_tier4_validation.py tests/test_weather_features.py` | 命令退出码 0 | FR-02, FR-03, FR-04, FR-05 |
| AC-05-21 | 测试不依赖真实网络（无 `requests` 或 `urllib` 真实调用） | ndg 检查无真实 HTTP 调用路径 | D-002@v1, D-003@v1 |
| AC-05-22 | 不修改 `ellectric/pipeline/`、`ellectric/fetch/`、`tests/test_weather_features.py`、`tests/test_time_resolution_15min.py` | diff 检查 | FR-02, FR-03, FR-04, FR-05 |
