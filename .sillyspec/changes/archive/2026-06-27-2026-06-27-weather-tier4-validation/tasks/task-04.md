---
author: lmr
created_at: 2026-06-28 01:11:57
id: task-04
title: 实现 JSON 和 Markdown 报告输出（覆盖：FR-01, FR-05, D-001@v1, D-003@v1）
priority: P0
estimated_hours: 1.5
depends_on: [task-01, task-02, task-03]
blocks: [task-05, task-07]
requirement_ids: [FR-01, FR-05]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths:
  - ellectric/scripts/validate_weather_tier4.py
  - ellectric/reports/weather_tier4/weather_tier4_validation.json
  - ellectric/reports/weather_tier4/weather_tier4_validation.md
---

# task-04: 实现 JSON 和 Markdown 报告输出（覆盖：FR-01, FR-05, D-001@v1, D-003@v1）

## 修改文件

| 操作 | 文件路径 |
|------|----------|
| 修改 | `ellectric/scripts/validate_weather_tier4.py` |
| 生成 | `ellectric/reports/weather_tier4/weather_tier4_validation.json` |
| 生成 | `ellectric/reports/weather_tier4/weather_tier4_validation.md` |

修改前一任务 task-03 中的 `validate_weather_tier4.py`，新增 `write_reports()` 函数并在 `run_validation()` 中调用它。生成的报告文件是脚本运行后的输出产物，不作为源码检入。

## 覆盖来源

- **FR-01**（可复现验证脚本入口）: `run_validation()` 调用 `write_reports(result, output_dir)`，输出标准化 JSON 和 Markdown 报告。
- **FR-05**（报告格式稳定）: JSON 报告包含 `metadata`、`weather_quality`、`experiments`、`interpretation` 四个顶层字段。Markdown 报告包含标题、metadata、weather quality 说明、实验对比表格、delta、report-only 解释、notes。
- **D-001@v1**（报告式验证优先于硬阈值验收）: `interpretation` 中设置 `hard_threshold_applied=false`，指标不设硬性提升要求。
- **D-003@v1**（采用可复现脚本 + 报告产物）: 脚本化输出 JSON（机器可读）和 Markdown（人类可读）双报告。

## 实现要求

1. 新增 `write_reports(result, output_dir)` 函数，接收 `run_validation()` 构建的完整 result dict 和输出目录，写入两个文件并返回路径 dict `{"json": str, "markdown": str}`。

2. **JSON 报告** — 严格遵循 `design.md:182-226` 定义的 schema：
   - `metadata`: `generated_at`（ISO 8601 带 Z 后缀）、`data_source`、`data_version`、`time_config`（`freq`、`points_per_day`）、`start`、`end`。
   - `weather_quality`: 直接使用 task-02 构建的 weather_quality dict，不做结构转换。
   - `experiments`: `baseline_tier3` 和 `weather_tier4` 各含 `feature_count`、`input_rows`、`sample_count`、`metrics`（`mae`、`rmse`、`mape`）；`delta` 含 `mae_delta`、`rmse_delta`、`mape_delta`、`mae_delta_pct`。
   - `interpretation`: `hard_threshold_applied` 固定为 `false`；`summary` 为一段简要英文/中文解释文案，说明 Weather Tier4 是可选增强层、指标含义、结论（如 "Weather features did not show significant MAE improvement in this run."）。
   - 使用 `json.dumps(result, ensure_ascii=False, indent=2, default=_json_serializer)` 序列化，`_json_serializer` 处理：`numpy.floating` → `float`、`numpy.integer` → `int`、`numpy.ndarray` → `list`、`pandas.Timestamp` → ISO 格式字符串、`Path` → `str`、`datetime` → ISO 格式字符串；未知类型抛 `TypeError`。
   - 文件写入 UTF-8 编码，不含 BOM，换行符 `\n`。

3. **Markdown 报告** — 按以下章节结构渲染：
   - 标题：`# Weather Tier4 Validation Report` + 副标题（generated_at、data_source）。
   - `## Metadata` — 以键值列表形式展示 generated_at、data_source、data_version、time_config、start、end。
   - `## Weather Quality` — 展示 weather_source、weather_features_available、weather_column_count、weather_columns 列表（Markdown 列表或行内逗号分隔）、overall_missing_rate 百分比格式（如 "2.3%"）、time_range、timezone、coverage ratio 百分比格式、notes 列表（每项一条 `- ...`）。
   - `## Experiment Comparison` — 两张表格：第一张 baseline_tier3 vs weather_tier4 指标对比表（表头：Metric / Baseline Tier3 / Weather Tier4 / Delta / Delta %）；行：MAE、RMSE、MAPE。第二张实验配置对比表（表头：Config / Baseline Tier3 / Weather Tier4）；行：Feature Count、Input Rows、Sample Count。
   - `## Delta` — 文字段落，列出各指标的绝对差值和百分比差值。若无改善则说明 "No significant improvement observed in this run"。
   - `## Interpretation` — 明确说明 `hard_threshold_applied = false`，解释 Weather Tier4 是可选增强特征层，本次验证仅做报告，不设精度提升硬门槛。包含 summary 文本。
   - `## Notes` — 从 result 中提取所有 notes，每条 `- note` 一行。若没有 notes 则写 "None."。
   - 数值格式化：MAE/RMSE 保留 4 位小数，MAPE 保留 2 位小数（百分比），delta_pct 保留 2 位小数。
   - 文件写入 UTF-8 编码。

4. 修改 `run_validation()`：在 task-02 和 task-03 完成 result dict 的组装后，在返回之前调用 `write_reports(result, output_dir)`。将返回的 paths dict 存入 `result["report_paths"]`。`result["status"]` 保持 `"ok"`。

5. `output_dir` 由 `main()` 传入的 `--output-dir` 决定。若目录不存在则自动创建（`os.makedirs(output_dir, exist_ok=True)`）。

6. 文件命名固定：
   - JSON: `weather_tier4_validation.json`
   - Markdown: `weather_tier4_validation.md`

## 接口定义

```python
def write_reports(
    result: dict,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write JSON and Markdown reports to output_dir.

    Args:
        result: Complete validation result dict with keys:
            metadata, weather_quality, experiments, interpretation.
        output_dir: Directory to write reports into. Created if missing.

    Returns:
        Dict with keys 'json' and 'markdown' mapping to absolute report paths.

    Raises:
        OSError: If output_dir creation or file write fails.
    """
```

## 边界处理

1. **output_dir 不存在**: `write_reports` 必须创建目录（`os.makedirs`），而不是假设调用方已创建。目录创建失败时抛 OSError。
2. **空 result dict**: `write_reports` 在 JSON 中写出空结构（顶层键值但子键为空或 None），Markdown 中若某节数据缺失则写 `"N/A"`。metadata 中的 `generated_at` 始终用当前时间填充，不依赖 result 提供。
3. **numpy 浮点数序列化**: 所有 metrics 值（mae、rmse、mape、delta 值）可能为 numpy.float64。`_json_serializer` 必须处理 `np.floating`、`np.integer`、`np.ndarray`、`np.bool_`。未被识别的 numpy 类型也应兜底转 `str` 而非抛异常（安全降级）。
4. **pandas.Timestamp 或 datetime 序列化**: `_json_serializer` 将 `pd.Timestamp` 和 `datetime.datetime` 转为 ISO 字符串（`tz=None` 时追加 `Z` 后缀表示 UTC）。`pd.NaT` 转为 `null`。
5. **pathlib.Path 序列化**: `_json_serializer` 将 `Path` 对象转为 `str`。`PosixPath` 或 `WindowsPath` 均处理。
6. **Markdown 特殊字符**: 指标值和 notes 中的文本包含 Markdown 特殊字符（`|`、`*`、`_`、`[` 等）时，表格单元格内做转义或替换（`|` → `\|`）。
7. **weather_quality 为 None 或缺失**: 当 result 无 `weather_quality` 键或值为 None 时，Markdown 的 Weather Quality 节输出 "Not available."，JSON 中保留该字段为 null。notes 合并时检查 None。
8. **experiments 缺失子键**: baseline_tier3 或 weather_tier4 可能缺失（降级场景）。Markdown 表格缺失行写 "—"，JSON 中该字段为 None。delta 计算结果需检查两个实验都存在。
9. **文件写入失败**: 任一文件写入失败（磁盘满、权限不足）时，`write_reports` 写文件前使用 `tempfile.NamedTemporaryFile` 在目标目录写入再 `os.rename`，避免写一半的损坏文件。返回 paths dict 时，写入失败的文件路径不包含在返回 dict 中，并记录 ERROR 日志。
10. **多字节字符**: JSON 使用 `ensure_ascii=False` 保留中文字符。Markdown 文件直接以 UTF-8 写入。不做额外转义。
11. **超大 result dict 截断**: 不做截断。当前验证不超过 100KB 报告，无需流式写入。未来扩展时考虑分块写入。

## 非目标

- ❌ 不修改 JSON schema 结构（严格遵循 design.md 定义）。
- ❌ 不生成 HTML、CSV 或其他格式的报告文件。
- ❌ 不在报告中包含模型持久化路径或检查点信息。
- ❌ 不修改 Markdown 报告的章节顺序或结构（顺序固定：title → metadata → weather quality → experiment comparison → delta → interpretation → notes）。
- ❌ 不修改 ShandongDataLoader、FeatureEngineer、XGBoostForecaster、WeatherFetcher 的任何代码。
- ❌ 不将报告产物加入 git 跟踪或 .gitignore。
- ❌ 不发送报告到任何远程服务或 API。
- ❌ 不在 `write_reports` 中做任何指标计算或数据分析（纯格式化输出）。

## 参考

- `design.md:97-103` — 文件变更清单，reports 目录为生成产物。
- `design.md:164-177` — `write_reports` 函数的签名和职责说明。
- `design.md:182-226` — JSON 报告 schema 完整定义（4 个顶层键及子键结构）。
- `design.md:221-225` — `interpretation` 字段含 `hard_threshold_applied=false`。
- `design.md:55-58` — 报告写入 `ellectric/reports/weather_tier4/` 目录。
- `plan.md:27` — task-04 覆盖 FR-01、FR-05、D-001@v1、D-003@v1。
- `plan.md:35-40` — AC-02 到 AC-06 验收标准。
- `plan.md:51-53` — task-04 的验收关联。
- `decisions.md:8-19` — D-001@v1 报告式验证语义（不设硬阈值）。
- `decisions.md:34-42` — D-003@v1 双报告格式要求（JSON + Markdown）。
- `requirements.md:72-82` — FR-05 报告格式稳定要求。
- `requirements.md:62-69` — FR-04 report-only 验收语义。
- `numpy` doc: `numpy/floating`、`numpy/integer`、`numpy/bool_` 类型在 JSON serialization 中的处理方法。
- `python json` module: `default` callable 用法。

## TDD 步骤

1. [RED] 编写单测调用 `write_reports({"metadata": {"generated_at": "2026-06-28T00:00:00Z", "data_source": "shandong"}, "weather_quality": {}, "experiments": {}, "interpretation": {}}, tmp_path)`，断言返回 dict 包含 `json` 和 `markdown` 键，对应的文件路径存在且为 `.json` 和 `.md` 后缀。

2. [GREEN] 实现 `write_reports` 基本框架：创建 output_dir（`os.makedirs(exist_ok=True)`），构造两个文件路径，调用 `write_json(result, json_path)` 和 `write_markdown(result, md_path)` 私有函数。返回 path dict。

3. [RED] 运行完整 result dict 写入测试：用 design.md schema 定义的完整四层结构调用 `write_reports`，读取生成的 JSON 文件，断言顶层键为 `metadata`、`weather_quality`、`experiments`、`interpretation` 且子键结构正确。

4. [GREEN] 实现 JSON 写入：使用 `json.dumps(..., ensure_ascii=False, indent=2, default=_json_serializer)`。实现 `_json_serializer` 处理 numpy、pandas、Path、datetime 类型。用 `open(json_path, "w", encoding="utf-8")` 写入。

5. [RED] 编写 Markdown 各章节内容测试：构造包含 weather_quality notes 和 experiments delta 的 result dict，调用 `write_reports`，读取 Markdown 文件，断言存在标题（`#`）、Metadata 表、Weather Quality 列表、Experiment Comparison 表格、Delta 段落、Interpretation 段落、Notes 列表。

6. [GREEN] 实现 Markdown 渲染：按实现要求第 3 条的 7 个章节逐一实现 render 函数。数值格式化用 Python format spec（`{:.4f}`、`{:.2%}`）。表格用标准 Markdown 管道表格语法。notes 列表用 `- ` 前缀。

7. [RED] 边界测试：numpy 浮点数输入（`np.float64(0.1234)`、`np.float32(0.5)`）、缺失 weather_quality、experiments 空子键。断言 JSON 序列化不抛异常且值类型正确（float 而非 numpy scalar）。断言 Markdown 缺失章节输出 "N/A"。

8. [GREEN] 在 `_json_serializer` 中依次检查 type 并转换：`np.floating` → `float`、`np.integer` → `int`、`np.bool_` → `bool`、`np.ndarray` → `list`、`pd.Timestamp` / `datetime` → ISO str、`pd.NaT` → `None`、`Path` → `str`；末尾兜底 `return str(obj)` 避免未知 numpy 子类抛异常。

9. [RED] 原子写入测试：在只读目录上调用 `write_reports`，断言不产生部分文件，日志记录 ERROR。

10. [GREEN] 实现在只读目录场景下捕获 OSError 并记录日志。使用 `tempfile.NamedTemporaryFile(dir=output_dir, delete=False)` 结合 `os.rename` 实现原子写入。标记已写入的文件路径在返回 dict 中。

11. [RED] 集成确认：`python -c "from ellectric.scripts.validate_weather_tier4 import run_validation; r = run_validation(); assert 'report_paths' in r; assert r['report_paths']['json'].endswith('.json'); assert r['report_paths']['markdown'].endswith('.md')"` — 确认 run_validation 返回的 report_paths 正确。

12. [GREEN] 在 `run_validation()` 末尾、return 之前插入 `write_reports(result, output_dir)`，将 paths 存入 `result["report_paths"]`。确认 status 保持 "ok"。

13. [REFACTOR] 将 JSON 和 Markdown 写入拆分为 `_write_json_report(result, path)` 和 `_write_markdown_report(result, path)` 两个私有函数，`write_reports` 只做编排。提取 Markdown 各章节的 render 函数以提高可测性。

## 验收标准

| ID | 标准 | 验证方式 | 关联需求/决策 |
|----|------|----------|---------------|
| AC-04-01 | `write_reports` 返回 dict 包含 `json` 和 `markdown` 键，路径为绝对路径且扩展名正确 | 单测断言返回值和文件存在性 | FR-05 |
| AC-04-02 | JSON 文件包含 `metadata`、`weather_quality`、`experiments`、`interpretation` 四个顶层键 | 反序列化后断言 keys | FR-05 |
| AC-04-03 | JSON `metadata` 包含 `generated_at`（ISO 格式）、`data_source`、`data_version`、`time_config`、`start`、`end` | 断言子键存在性和类型 | FR-05 |
| AC-04-04 | JSON `experiments` 包含 `baseline_tier3`、`weather_tier4`、`delta`，每个含 metrics 和配置字段 | 断言子键结构 | FR-05 |
| AC-04-05 | JSON `interpretation.hard_threshold_applied` 为 `false` | 断言布尔值 | D-001@v1 |
| AC-04-06 | JSON 序列化 numpy 值后为原生 Python 类型（float/int，非 numpy scalar） | 反序列化后检查 type | FR-05 |
| AC-04-07 | JSON 序列化 pd.Timestamp、Path、datetime 后为字符串 | 断言类型为 str | FR-05 |
| AC-04-08 | JSON 编码为 UTF-8，`ensure_ascii=False`，文件不含 BOM | 读取文件头字节检查 | FR-05 |
| AC-04-09 | Markdown 文件包含 `# Weather Tier4 Validation Report` 标题 | grep 标题行 | FR-05 |
| AC-04-10 | Markdown 包含 `## Metadata`、`## Weather Quality`、`## Experiment Comparison`、`## Delta`、`## Interpretation`、`## Notes` 六个章节 | grep 各章节标题 | FR-05 |
| AC-04-11 | Markdown Experiment Comparison 包含两张 Markdown 管道表格 | 检查 `|---|---` 模式出现 2 次 | FR-05 |
| AC-04-12 | Markdown 中 hard_threshold_applied 为 false 语义明确表述 | grep `false` 或 `无硬阈值` | D-001@v1 |
| AC-04-13 | output_dir 不存在时，write_reports 自动创建 | 传入不存在的 `tmp_path / "new_dir"` 并断言创建成功 | FR-05 |
| AC-04-14 | 文件写入为原子操作（用 tempfile + rename） | 检查源码中 `NamedTemporaryFile` + `rename` 的使用 | FR-05 |
| AC-04-15 | 写入失败时不产生残留文件，记录 ERROR 日志 | 模拟只读目录 + 检查日志 | FR-05 |
| AC-04-16 | 完整 result dict 走通 `run_validation()` 到 `write_reports()` 流程，report_paths 正确 | 端到端运行 + 断言 | FR-01, D-003@v1 |
| AC-04-17 | 未修改 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster` 的任何代码 | diff 检查 | FR-01 |
| AC-04-18 | 生成报告文件为脚本产物，不检入 git（由 `.gitignore` 覆盖或从 allowed_paths 语义排除） | 确认文件列表不含生成报告 | D-003@v1 |
