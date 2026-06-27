---
author: lmr
created_at: 2026-06-28 01:11:57
id: task-07
title: 运行验证脚本、项目测试和检查命令（覆盖：FR-01, FR-02, FR-03, FR-04, FR-05, FR-06）
priority: P0
estimated_hours: 1
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06]
decision_ids: [D-001@v1, D-002@v1, D-003@v1]
allowed_paths:
  - ellectric/reports/weather_tier4/weather_tier4_validation.json
  - ellectric/reports/weather_tier4/weather_tier4_validation.md
---

## 修改文件

本任务不修改任何源文件。仅运行命令、生成报告产物、记录结果。

## 覆盖来源

| 来源 | 覆盖内容 |
|---|---|
| FR-01 | 验证脚本 CLI 帮助可见、可运行、输出报告路径 |
| FR-02 | `weather_quality` 字段完整性（JSON + Markdown） |
| FR-03 | baseline vs Tier4 指标存在且 delta 计算正确 |
| FR-04 | `hard_threshold_applied=false`；degraded 分支不崩溃 |
| FR-05 | 四个顶层字段 `metadata`/`weather_quality`/`experiments`/`interpretation` 齐全 |
| FR-06 | 现有测试全部通过（`test_weather_features.py` + `test_time_resolution_15min.py`） |

## 实现要求

1. 运行 `python ellectric/scripts/validate_weather_tier4.py --help` 确认 CLI 参数可用。
2. 以默认参数运行脚本（或 `--no-fetch` + `--start 2024-01-01 --end 2024-01-14` 缩小范围节省时间）。
3. 若默认数据文件不存在，记录为环境 blocker，不跳过；脚本应报明确错误。
4. 运行 `python -m pytest tests/test_weather_tier4_validation.py -v` 验证新测试。
5. 运行 `python -m pytest tests/ -v` 验证全部项目测试（含 `test_weather_features.py` 契约测试）。
6. 验证 `weather_tier4_validation.json` 包含设计文档约定的全部字段。
7. 验证 `weather_tier4_validation.md` 已生成且内容非空。
8. 不提交任何文件到 git。

## 接口定义

本任务消费以下入口：

```bash
# CLI 帮助
python ellectric/scripts/validate_weather_tier4.py --help

# 默认运行（全量数据，可能耗时 5-15min）
python ellectric/scripts/validate_weather_tier4.py

# 安全小范围运行（禁用网络抓取，2 周数据窗口）
python ellectric/scripts/validate_weather_tier4.py \
  --no-fetch \
  --start 2024-01-01 \
  --end 2024-01-14

# 测试命令（新测试）
python -m pytest tests/test_weather_tier4_validation.py -v

# 测试命令（全部项目测试）
python -m pytest tests/ -v
```

已知无 `pyproject.toml`/`setup.cfg`/`pytest.ini`/`Makefile`，`pytest` 通过 `python -m pytest` 调用。依赖未安装时先执行 `pip install -r ellectric/requirements.txt`。

## 边界处理

- 默认山东 CSV 不存在：脚本应报 `FileNotFoundError` 或 `RuntimeError`，测试验证降级路径，本任务记录为环境 blocker，不强行伪造数据。
- Open-Meteo 网络不可用：`--no-fetch` 跳过抓取；无 cache 时 `weather_features_available=false`、报告 degraded，不崩溃。
- 没有 GPU：XGBoost 在 CPU 上运行，全量 71520 行 15min 数据约 5-15min。小范围 `--start/--end` 可缩减到 <2min。
- 测试失败（skip 而非 fail）：若默认数据不存在，`test_weather_tier4_validation.py` 中集成测试应 `pytest.skip`；单元级别不依赖真实数据。
- JSON 字段缺失：验收时逐字段检查平面路径（见验收标准表），不符合则标记未通过。
- Markdown 报告路径未生成：脚本应保证 `output_dir` 存在，不存在时 `os.makedirs`。
- 依赖未安装：`pip install -r ellectric/requirements.txt` 后重试，记录缺少哪些包。

## 非目标

- 不修改项目配置、测试配置或 CI 配置。
- 不调整脚本参数、测试逻辑或报告 schema。
- 不解决测试失败的根本原因（任务 01-06 应已解决）。
- 不 commit。
- 不生成 SVG/PNG/PDF 图表。
- 不运行 LSTM、RL 训练或 ASSUME 仿真。

## 参考

- 设计文档：`design.md:94-103` 文件变更清单
- 脚本入口定义：`design.md:107-124` CLI 参数
- JSON 报告结构：`design.md:181-226`
- 验收标准：`plan.md:34-42` 全部 AC
- 现有契约测试：`tests/test_weather_features.py`
- 本变更新增测试：`tests/test_weather_tier4_validation.py`

## TDD 步骤

```
1. [pre-check] 确认 ellectric/scripts/validate_weather_tier4.py 存在、可 import
2. [run-help]  python ellectric/scripts/validate_weather_tier4.py --help → 输出含参数说明
3. [run-safe]   python ellectric/scripts/validate_weather_tier4.py --no-fetch --start 2024-01-01 --end 2024-01-14
                 → 若数据缺失则报明确错误（环境 blocker），若数据存在则生成报告
4. [check-json]  验证 weather_tier4_validation.json 存在 + 字段完整性（对照验收标准表）
5. [check-md]    验证 weather_tier4_validation.md 存在 + 非空
6. [test-new]    python -m pytest tests/test_weather_tier4_validation.py -v → 全部通过
7. [test-all]    python -m pytest tests/ -v → 全部通过（含 test_weather_features.py 契约测试）
8. [summary]     记录所有结果：通过/失败/跳过，失败时记录原因
```

## 验收标准

| # | 检查项 | 命令/方法 | 预期结果 | 实测 |
|---|---|---|---|---|
| AC-01 | CLI help 可见 | `python ellectric/scripts/validate_weather_tier4.py --help` | 输出包含 `--output-dir`、`--start`、`--end`、`--weather-cache`、`--no-fetch` | |
| AC-02 | 脚本以默认参数可运行 | `python ellectric/scripts/validate_weather_tier4.py --no-fetch`（数据存在时） | exit code 0，打印报告路径 | |
| AC-03 | JSON 报告存在 | `ls ellectric/reports/weather_tier4/weather_tier4_validation.json` | 文件存在 | |
| AC-04 | Markdown 报告存在 | `ls ellectric/reports/weather_tier4/weather_tier4_validation.md` | 文件存在 | |
| AC-05 | JSON 包含 metadata | `python -c "import json; d=json.load(open('ellectric/reports/weather_tier4/weather_tier4_validation.json')); print('metadata' in d)"` | `True` | |
| AC-06 | JSON 包含 weather_quality | 同上，检查 `weather_quality` 键 | `True` | |
| AC-07 | JSON 包含 experiments | 同上，检查 `experiments` 键 | `True` | |
| AC-08 | JSON 包含 interpretation | 同上，检查 `interpretation` 键 | `True` | |
| AC-09 | weather_source 字段 | `d['weather_quality']['weather_source']` | 值为 `cache`/`fetch`/`explicit`/`degraded` 之一 | |
| AC-10 | weather_features_available 布尔 | `d['weather_quality']['weather_features_available']` | `bool` 类型 | |
| AC-11 | weather_columns 列表 | `d['weather_quality']['weather_columns']` | `list`，非空时有列名 | |
| AC-12 | weather_column_count 整数 | `d['weather_quality']['weather_column_count']` | `int` | |
| AC-13 | missing_rate_by_column 字典 | `d['weather_quality']['missing_rate_by_column']` | `dict` | |
| AC-14 | overall_missing_rate 浮点数 | `d['weather_quality']['overall_missing_rate']` | `float` 或在 degraded 时为 `None` | |
| AC-15 | experiments 包含 baseline_tier3 | `d['experiments']['baseline_tier3']` | 存在 | |
| AC-16 | experiments 包含 weather_tier4 | `d['experiments']['weather_tier4']` | 存在（degraded 时可为 None） | |
| AC-17 | baseline_tier3 含 metrics | `d['experiments']['baseline_tier3']['metrics']` | 含 `mae`、`rmse`、`mape` | |
| AC-18 | delta 存在 | `d['experiments']['delta']` | 含 `mae_delta`、`rmse_delta`、`mape_delta`、`mae_delta_pct` | |
| AC-19 | hard_threshold_applied=false | `d['interpretation']['hard_threshold_applied']` | `false` | |
| AC-20 | 新测试全部通过 | `python -m pytest tests/test_weather_tier4_validation.py -v` | 全部 PASSED | |
| AC-21 | 全部项目测试全部通过 | `python -m pytest tests/ -v` | 全部 PASSED（无 FAILED） | |
| AC-22 | degraded 分支不崩溃 | 无 cache + `--no-fetch` + 数据存在 | exit code 0，`weather_features_available=false` | |
| AC-23 | 数据缺失报明确错误 | 数据文件不存在时运行脚本 | 报 `FileNotFoundError` 或 `RuntimeError`，不静默使用空 df | |
| AC-24 | 不修改源文件 | `git diff --stat` | 仅 `reports/` 下有文件变化（派生产物） | |
