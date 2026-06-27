---
author: lmr
created_at: 2026-06-28 01:11:57
id: task-03
title: 实现 baseline_tier3 vs weather_tier4 对比实验与指标 delta（覆盖：FR-03, FR-04, D-001@v1, D-003@v1）
priority: P0
estimated_hours: 2
depends_on: [task-01, task-02]
blocks: [task-04, task-05, task-07]
requirement_ids: [FR-03, FR-04]
decision_ids: [D-001@v1, D-003@v1]
allowed_paths:
  - ellectric/scripts/validate_weather_tier4.py
---

# task-03: 实现 baseline_tier3 vs weather_tier4 对比实验与指标 delta（覆盖：FR-03, FR-04, D-001@v1, D-003@v1）

## 修改文件

| 操作 | 文件路径 |
|------|----------|
| 修改 | `ellectric/scripts/validate_weather_tier4.py` |

修改 task-02 的 `run_validation()`，在 weather 质量报告生成后追加 ablation 实验流程。只改此一个文件。

## 覆盖来源

- **FR-03**（可复现 baseline vs Tier4 指标对比）: 同一数据、同一切分、同一 XGBoostForecaster 配置下执行两次 `train_evaluate`，计算并输出 baseline 和 weather 两组指标及 delta。
- **FR-04**（降级与报告式验证）: weather 不可用时不阻断实验，baseline 结果正常输出，weather 结果标记 degraded 并记录原因；不设硬性精度提升阈值。
- **D-001@v1**（报告式验证优先于硬阈值验收）: 指标只报告、不判 PASS/FAIL；`hard_threshold_applied` 始终为 false。
- **D-003@v1**（方案B: 可复现脚本 + 报告产物）: 脚本内完成实验、计算指标、返回机器可读结构，后续 task-04 写入报告文件。

## 实现要求

1. 在 `run_validation()` 的 weather 质量报告生成之后、返回值组装之前，插入 ablation 实验流程：调用 `run_ablation_experiment(load_df, weather_cache=weather_cache, fetch_if_missing=fetch_if_missing)`，将其返回 dict 存入 `result["experiments"]`。

2. 新增 `compute_metrics(actuals, predictions)` 函数。接收两个一维 numpy 数组，返回包含以下键的 dict：
   - `mae`: mean_absolute_error（float，用 sklearn.metrics）
   - `rmse`: sqrt(mean_squared_error)（float，用 sklearn.metrics）
   - `mape`: 平均绝对百分比误差（float，百分比形式，非小数）。对 actuals 中值为 0 的点做 mask 排除，避免除零。若所有点均被 mask 掉（全零 actuals），则 `mape` 为 `None`，同时往调用方结果 dict 的 `notes` 追加一条 `"MAPE: all actual values were zero, MAPE set to None"`。
   - 返回 dict 不包含 `sample_count` 或 `input_rows`——这些由 `run_ablation_experiment` 在实验 dict 中记录。

3. 新增 `run_ablation_experiment(load_df, weather_cache=None, fetch_if_missing=True)` 函数。职责：对同一 `load_df` 生成两套特征、各自训练评估、收集指标并计算 delta。

4. `run_ablation_experiment` 内部流程：
   a. 用 `prepare_features(load_df, tiers=["tier1", "tier2", "tier3"])` 生成 baseline 特征。记录 baseline 的 `feature_count`（特征列数，不含 timestamp/load_mw）和 `input_rows`（= len(load_df)）。
   b. 去掉 timestamp 和 load_mw 列得到 X_baseline，取目标 y = load_df["load_mw"]。调用 `XGBoostForecaster().train_evaluate(X_baseline, y)` 得到 baseline 结果。记录 `sample_count` = len(result["actuals"]）。
   c. 调用 `compute_metrics(baseline["actuals"], baseline["predictions"])` 得到 baseline 指标。
   d. 用 `prepare_features(load_df, tiers=["tier1", "tier2", "tier3", "tier4"], weather_cache_path=weather_cache, fetch_if_missing=fetch_if_missing)` 生成 weather 特征。
   e. **检查 feature DataFrame 中是否含有 Tier4 weather 列**：对比 Tier3 特征列集合与当前 DataFrame 列集合，差值即为 weather 列。如果差集为空（即无新增 weather 列），则 weather 实验被视为 degraded，metrics 设为 `None`，feature_count 仍正常记录，sample_count 和 input_rows 仍记录，notes 追加 `"No weather columns found in feature_df; weather experiment degraded"`。
   f. 如果 weather 列存在，则正常执行 `XGBoostForecaster().train_evaluate(X_weather, y)`（使用**同一默认配置**——不手动传入 `n_estimators`/`max_depth`/`learning_rate`，完全走 `XGBoostForecaster()` 默认值），然后 `compute_metrics(...)` 得到 weather 指标。
   g. 计算 delta 字典：对 `metrics` 中的 mae/rmse/mape 三个键，分别计算 `mae_delta = weather_mae - baseline_mae`（正数表示 weather 更差，负数表示 weather 更好），`rmse_delta` 同理，`mape_delta` 同理。额外计算 `mae_delta_pct = (mae_delta / baseline_mae) * 100`（float，百分比形式）。如果 weather metrics 为 None（degraded），则所有 delta 值均为 `None`。
   h. 返回结构见接口定义。

5. `run_validation()` 在 ablation 实验后，增加 `interpretation` 字典。包含：
   - `hard_threshold_applied`: `false`（布尔 false，非字符串）。
   - `summary`: 简洁的总结文本，指示实验完成状态（含 weather 可用性、baseline 和 weather 的 MAE）。

6. 两个 `XGBoostForecaster.train_evaluate` 调用使用完全相同的模型默认参数（n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42）和相同的 n_splits=5 / gap=TimeConfig.points_per_day。

## 接口定义

```python
def compute_metrics(
    actuals: np.ndarray,
    predictions: np.ndarray,
) -> dict[str, float | None]:
    """计算 MAE / RMSE / MAPE。

    Args:
        actuals: 真实值数组（来自 train_evaluate 返回的 actuals）
        predictions: 预测值数组（来自 train_evaluate 返回的 predictions）

    Returns:
        {"mae": float, "rmse": float, "mape": float | None}
        MAPE 为百分比值（如 3.5 表示 3.5%），全零 actuals 时为 None。
    """


def run_ablation_experiment(
    load_df: pd.DataFrame,
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    """运行 baseline Tier1-3 vs weather Tier1-4 对比实验。

    Args:
        load_df: 含 timestamp 和 load_mw 列的原始负荷 DataFrame
        weather_cache: weather cache parquet 路径（传递给 prepare_features）
        fetch_if_missing: cache 缺失时是否自动抓取

    Returns:
        {
            "baseline_tier3": {
                "feature_count": int,
                "input_rows": int,
                "sample_count": int,
                "metrics": {"mae": float, "rmse": float, "mape": float | None}
            },
            "weather_tier4": {
                "feature_count": int,
                "input_rows": int,
                "sample_count": int,
                "metrics": {"mae": float | None, "rmse": float | None, "mape": float | None}
            },
            "delta": {
                "mae_delta": float | None,
                "rmse_delta": float | None,
                "mape_delta": float | None,
                "mae_delta_pct": float | None
            },
            "notes": list[str]
        }
    """
```

### 返回值结构（JSON 表示）

```json
{
  "baseline_tier3": {
    "feature_count": 11,
    "input_rows": 71520,
    "sample_count": 49728,
    "metrics": {"mae": 1250.0, "rmse": 1850.0, "mape": 2.8}
  },
  "weather_tier4": {
    "feature_count": 23,
    "input_rows": 71520,
    "sample_count": 49728,
    "metrics": {"mae": 1180.0, "rmse": 1720.0, "mape": 2.6}
  },
  "delta": {
    "mae_delta": -70.0,
    "rmse_delta": -130.0,
    "mape_delta": -0.2,
    "mae_delta_pct": -5.6
  },
  "notes": []
}
```

Delta 符号约定：
- `mae_delta = weather_tier4.metrics.mae - baseline_tier3.metrics.mae`
- 负数 delta = weather 更优（指标值下降）
- 正数 delta = baseline 更优（指标值上升）
- `mae_delta_pct` = `(mae_delta / baseline_tier3.metrics.mae) * 100`

### 与 task-02 的衔接

`run_validation()` 在 task-02 基础上追加以下流程：

```text
run_validation:
  1. 加载数据（task-02）
  2. 解析 weather 来源（task-02）
  3. 构建 weather 质量报告 → result["weather_quality"]（task-02）
  --- 以下为 task-03 新增 ---
  4. run_ablation_experiment(load_df, weather_cache, fetch_if_missing) → result["experiments"]
  5. 构建 interpretation → result["interpretation"]
  6. return result  # report_paths 仍为空（task-04 处理报告写入）
```

## 边界处理

1. **weather 列完全不可用**: `prepare_features` 返回的 DataFrame 列集合与 Tier3 列集合差集为空。`run_ablation_experiment` 仍走完 `train_evaluate` 调用并记录 baseline 和 degraded weather 结果；weather `metrics` 所有值为 `None`；`delta` 所有值为 `None`；`notes` 包含 `"No weather columns found in feature_df; weather experiment degraded"`。

2. **XGBoostForecaster.train_evaluate 失败**: 如果 baseline 训练失败（如特征 DataFrame 为空、y 全为 NaN 等），`run_ablation_experiment` 捕获 Exception，设置 baseline 和 weather 所有 metrics 为 `None`，notes 追加错误信息。不重新抛异常——`run_validation` 中的实验异常不应阻断 JSON/Markdown 报告生成（task-04）。

3. **MAPE 全零 actuals**: `compute_metrics` 中对 actuals == 0 的点做 mask。如果 mask 后剩余样本数为 0，mape 设为 `None`，不抛异常。

4. **sample_count 可能不一致**: baseline 和 weather 两次 `train_evaluate` 的 sample_count 可能略有差异（TimeSeriesSplit 中最后 fold 的测试集大小取决于 gap 和 split 后的剩余行数，特征行数差异会导致最后一个 fold 的行数不同）。两者各自记录自己的 sample_count，不强制相等。

5. **两个 forecaster 实例独立**: baseline 和 weather 使用不同的 `XGBoostForecaster()` 实例，互不干扰。修改其中一个的 `predict()` 不会影响另一个。

6. **weather_cache 和 fetch_if_missing 只传给 weather 特征的 prepare_features**: baseline 特征生成不需要 weather，不传 cache/fetch 参数。

7. **`hard_threshold_applied` 为 false**: `interpretation` 中硬编码 `"hard_threshold_applied": false`，不依赖任何运行时条件。符合 D-001@v1。

8. **input_rows 取 len(load_df)**: 即原始数据行数，不是 dropna 后的行数。`sample_count` 才是实际参与评估的行数。

9. **forecaster 默认配置一致性**: 两个 `train_evaluate` 调用使用 `XGBoostForecaster()`（无参数）的默认值，以保证对比公平。不应手动传入参数值——默认值在 `forecaster.py:267-270` 定义为 n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42。

## 非目标

- ❌ 不实现质量报告（task-02）。
- ❌ 不实现 JSON/Markdown 报告写入（task-04）。
- ❌ 不添加验证脚本的自动化测试（task-05）。
- ❌ 不更新模块文档（task-06）。
- ❌ 不修改 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster`、`ShandongDataLoader` 的任何代码。
- ❌ 不新增第三方依赖（`sklearn.metrics.mean_absolute_error`、`sklearn.metrics.mean_squared_error` 已在现有依赖中）。
- ❌ 不做多模型对比（如 XGBoost vs LinearRegression）或超参数调优——只比较 Tier3 vs Tier4 特征集。
- ❌ 不做特征重要性分析或 SHAP。
- ❌ 不做 P&L 计算或仿真（那是 Phase 1 的端到端基线模块，不在此验证脚本重复）。
- ❌ 不持久化训练好的模型（save_model 不被调用）。

## 参考

- `design.md:74-82` — Wave 3 方案描述：同一数据、同一 XGBoostForecaster 配置、同一 TimeSeriesSplit 语义。
- `design.md:78-79` — sample_count 和 input_rows 的语义定义。
- `design.md:82` — "脚本在其基础上计算 MAE、RMSE、MAPE，不需要修改 forecaster"。
- `design.md:153-155` — `run_ablation_experiment` 函数签名。
- `design.md:164-169` — `compute_metrics` 函数签名和职责。
- `design.md:182-226` — JSON 报告结构中 experiments 和 delta 字段 schema（202-220 行）。
- `design.md:230-232` — 不修改 XGBoostForecaster 的兼容策略。
- `design.md:244` — 风险 R-03：weather 未提升精度不被视为失败。
- `design.md:248-249` — 决策 D-001@v1：报告式验证优先于硬阈值验收。
- `forecaster.py:290-388` — `train_evaluate` 的返回结构（predictions, actuals, metrics: {mae}）。
- `forecaster.py:265-285` — `XGBoostForecaster.__init__` 默认参数值。
- `features.py:326-371` — `prepare_features` 的 tiers 参数接受列表；当 tier4 在列表中时，前置 tier 若未传入则自动添加。
- `features.py:310-323` — `get_feature_columns("tier3")` 返回列集合，用于判定新增 weather 列。
- `plan.md:26` — task-03 覆盖 FR-03、FR-04、D-001@v1、D-003@v1。
- `plan.md:37` — AC-04 要求 experiments 记录 baseline 和 weather 的 MAE/RMSE/MAPE/feature_count/input_rows/sample_count/delta。
- `plan.md:38` — AC-05 要求 degraded 场景不失败。
- `plan.md:39` — AC-06 要求 hard_threshold_applied=false。

## TDD 步骤

```text
1. [RED] 运行脚本 `python ellectric/scripts/validate_weather_tier4.py`，确认 task-02 验收标准 AC-02-01~AC-02-16 保持通过。确认返回 dict 包含 weather_quality 等字段。

2. [RED] 编写 Python 单测验证 compute_metrics 基本功能：输入已知 actuals=[100,200,300], predictions=[110,190,310]，手动计算 MAE=10, RMSE=sqrt((100+100+100)/3)=10, MAPE=(10/100+10/200+10/300)/3*100=((10+5+3.33)/3)=6.11%。断言返回值精度匹配。

3. [GREEN] 实现 compute_metrics：sklearn.metrics.mean_absolute_error 和 mean_squared_error 计算 MAE/RMSE；手动实现 MAPE（mask 零值，逐点计算绝对百分比误差后取均值 *100）。全零 actuals 时 mape 为 None。

4. [RED] 编写 Python 单测验证 compute_metrics 边界：全零 actuals 返回 mape=None；actuals 含一个零值被 mask 掉，其余正常计算；predictions 全等于 actuals 时所有指标为 0。

5. [GREEN] 处理 MAPE 零值 mask 逻辑，确保全 mask 时返回 None，部分 mask 时正常计算。

6. [RED] 编写 Python 单测验证 run_ablation_experiment 返回结构：三个顶层键 baseline_tier3/weather_tier4/delta，各自子字段完整。使用 controller fixture 或 mock 的 load_df（至少含 20000 行数据以支持 TimeSeriesSplit n_splits=5 + gap=96）。mock prepare_features 返回适当特征列。

7. [GREEN] 实现 run_ablation_experiment：调用 prepare_features 两次、XGBoostForecaster 两次、compute_metrics 两次、计算 delta，组装返回 dict。部署 mock 友好的代码结构——将 prepare_features 和 XGBoostForecaster 作为可注入依赖或模块级别导入，方便单测替换。

8. [RED] 端到端运行脚本确认 run_validation 返回 dict 包含 "experiments" 和 "interpretation" 键：`python -c "from ellectric.scripts.validate_weather_tier4 import run_validation; r = run_validation(); assert 'experiments' in r; assert 'interpretation' in r; assert 'hard_threshold_applied' in r['interpretation']"`。

9. [GREEN] 调整 run_validation 内联逻辑直到端到端断言通过。

10. [RED] 编写单测验证 degraded 分支：mock prepare_features 在 tier4 调用时不返回额外 weather 列，确认 weather_tier4.metrics 所有值为 None，delta 所有值为 None，notes 包含 degraded 说明。

11. [GREEN] 在 run_ablation_experiment 中添加 weather 列判定逻辑，使用 prepare_features 返回的 DataFrame 列集合与 Tier3 列集合的差集判断 degraded 状态。

12. [REFACTOR] 提取 run_ablation_experiment 中特征生成和模型训练的重复代码为内部辅助函数（如 `_run_single_experiment(tiers, load_df, weather_cache, fetch_if_missing, label)`），保持高层函数清晰。确保两个实验共享完全相同的 XGBoostForecaster 默认配置（不传参数）。

13. [RED] 运行完整测试集：`python -m pytest tests/test_weather_tier4_validation.py -v`（task-05 创建此文件前暂时手动测试）。确认 baseline 和 weather 的 metrics 是 float 类型，delta 正负号正确。
```

## 验收标准

| ID | 标准 | 验证方式 | 关联需求/决策 |
|----|------|----------|---------------|
| AC-03-01 | `compute_metrics` 返回 dict 含 mae/rmse/mape，类型分别为 float/float/float-or-None | Python 单测 | FR-03 |
| AC-03-02 | MAPE 全零 actuals 时 mape=None，不抛异常 | Python 单测 | FR-03 |
| AC-03-03 | `run_ablation_experiment` 返回 dict 含 baseline_tier3/weather_tier4/delta/notes 四个顶层键 | Python 单测 | FR-03 |
| AC-03-04 | baseline_tier3 和 weather_tier4 各含 feature_count/input_rows/sample_count/metrics 四个子键 | Python 单测 | FR-03 |
| AC-03-05 | baseline 使用 Tier1+Tier2+Tier3 特征；weather 使用 Tier1+Tier2+Tier3+Tier4 特征 | 代码审查 + 单测 mock | FR-03 |
| AC-03-06 | delta 含 mae_delta/rmse_delta/mape_delta/mae_delta_pct 四个键；负值表示 weather 更优 | Python 单测验证符号 | FR-03 |
| AC-03-07 | sample_count = len(actuals)；input_rows = len(load_df) | Python 单测 | FR-03 |
| AC-03-08 | weather 列不可用时 weather_tier4.metrics 全为 None，delta 全为 None，notes 含 degraded 说明 | Python 单测 | FR-04, D-001@v1 |
| AC-03-09 | `interpretation.hard_threshold_applied` 为 `false`（布尔值） | 断言返回结构 | D-001@v1 |
| AC-03-10 | 两个 train_evaluate 使用相同 forecaster 默认参数（n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42） | 代码审查 | D-003@v1 |
| AC-03-11 | run_validation 返回 dict 含 experiments 和 interpretation 键 | 端到端运行脚本 | FR-03 |
| AC-03-12 | train_evaluate 异常时 run_ablation_experiment 捕获不抛，metrics 设为 None，notes 含错误说明 | Python 单测 mock 异常 | FR-04 |
| AC-03-13 | 未修改 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster` 代码 | diff 检查 | FR-03, D-003@v1 |
| AC-03-14 | 未修改 `ellectric/pipeline/` 下任何文件 | diff 检查 | FR-03, D-003@v1 |
