---
author: lmr
created_at: 2026-06-28 01:11:57
id: task-01
title: 新增 Weather Tier4 验证脚本骨架与 CLI 参数（覆盖：FR-01, FR-06, D-003@v1）
priority: P0
estimated_hours: 1
depends_on: []
blocks: [task-02, task-03, task-04, task-05, task-07]
requirement_ids: [FR-01, FR-06]
decision_ids: [D-003@v1]
allowed_paths:
  - ellectric/scripts/validate_weather_tier4.py
---

# task-01: 新增 Weather Tier4 验证脚本骨架与 CLI 参数（覆盖：FR-01, FR-06, D-003@v1）

## 修改文件

| 操作 | 文件路径 |
|------|----------|
| 新增 | `ellectric/scripts/validate_weather_tier4.py` |

只新增一个文件。不修改任何已有文件。

## 覆盖来源

- **FR-01**（可复现验证入口）: 新增 CLI 脚本作为唯一验证入口，`--help` 可用，`main()` → `run_validation()` 可正常调用。
- **FR-06**（保持 API 兼容性）: 脚本只 import/调用已有公共 API，不修改 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster`、`ShandongDataLoader` 的任何签名或默认行为。
- **D-003@v1**（方案B: 可复现脚本 + 报告产物）: 脚本骨架是后续任务填充具体验证逻辑的容器。`run_validation()` 返回 dict 和输出路径的消息已预留，但不在本任务实现质量检查或实验逻辑。

## 实现要求

1. 创建 `ellectric/scripts/validate_weather_tier4.py`，包含模块级 docstring、标准库/第三方导入、logger、argparse 解析、`main()` 和 `run_validation()` 桩函数。
2. `main()` 用 argparse 定义以下 CLI 参数，然后调用 `run_validation(...)`：
   - `--output-dir`: 报告输出目录，默认 `"ellectric/reports/weather_tier4"`
   - `--start`: 可选起始日期字符串，默认 `None`
   - `--end`: 可选结束日期字符串，默认 `None`
   - `--weather-cache`: 可选 weather cache parquet 路径，默认 `None`
   - `--no-fetch`: store_true，默认 `False`；禁止 cache miss 时自动抓取天气
3. `main()` 在 `run_validation()` 返回后打印报告已写入的路径（当返回 dict 包含 `report_paths` 时），以 `print(f"报告已写入: {path}")` 格式逐行输出。
4. `run_validation(start, end, output_dir, weather_cache, fetch_if_missing)` 是完整的函数签名，但本任务只写 **桩函数** —— 函数体只需一条 `logger.info(...)` 记录入参，并 `return {"status": "stub", "report_paths": []}`。weather quality、ablation experiment、report formatting 等实现在后续任务补充。
5. 脚本结尾通过 `if __name__ == "__main__": main()` 提供直接执行入口。
6. 脚本内 import 使用项目内现有路径：`sys.path.insert(0, '.')` 或等效的包导入方式（参考 `verify_time_resolution.py` 的 `sys.path.insert(0, '.')` 风格）。
7. 日志级别设为 `INFO`，logger name 为脚本模块名。

## 接口定义

### CLI

```shell
python ellectric/scripts/validate_weather_tier4.py \
  --output-dir ellectric/reports/weather_tier4 \
  --start 2024-01-01 \
  --end 2026-01-14 \
  --weather-cache /path/to/cache.parquet \
  --no-fetch
```

### Python 函数签名

```python
def run_validation(
    start: str | None = None,
    end: str | None = None,
    output_dir: str | Path = "ellectric/reports/weather_tier4",
    weather_cache: str | Path | None = None,
    fetch_if_missing: bool = True,
) -> dict:
    """验证骨架（本任务只植入桩逻辑）。
    
    后续任务将在此函数内补充:
    - 调用 ShandongDataLoader 加载数据
    - 调用 prepare_features 生成 feature DataFrame
    - 调用 XGBoostForecaster.train_evaluate 进行实验
    
    Returns:
        包含至少 status 和 report_paths 的字典。
    """
```

### 预期的 `--help` 输出

```
usage: validate_weather_tier4.py [-h] [--output-dir OUTPUT_DIR] [--start START]
                                 [--end END] [--weather-cache WEATHER_CACHE]
                                 [--no-fetch]

Weather Tier4 特征验证脚本 — 数据质量检查 + Baseline vs Tier4 对比实验

options:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        报告输出目录 (default: ellectric/reports/weather_tier4)
  --start START         起始日期 (YYYY-MM-DD)，默认使用 loader 默认范围
  --end END             结束日期 (YYYY-MM-DD)，默认使用 loader 默认范围
  --weather-cache WEATHER_CACHE
                        weather cache parquet 路径，默认走 FeatureEngineer 默认 cache
  --no-fetch            cache 缺失时不自动抓取天气数据，用于离线复现
```

## 边界处理

1. **参数为空**: `--start`/`--end`/`--weather-cache` 允许不传，默认 `None`；`run_validation` 对 `None` 不做特殊处理（后续任务决定含义）。
2. **目录不存在**: `--output-dir` 指定路径如果不存在，`run_validation` 桩阶段不创建目录（后续任务创建）。桩函数只记录日志，不做磁盘写入。
3. **非 string 类型**: `pathlib.Path` 在 `run_validation` 桩内部被接受，`main()` 传递的 `args.output_dir` 是 str，`run_validation` 签名接受 `str | Path`。
4. **`--no-fetch` 默认假**: `store_true` 参数，默认 `False`。`main()` 传给 `run_validation` 时取反为 `fetch_if_missing=not args.no_fetch`。
5. **异常安全**: 桩函数不 try-except。后续任务各自处理异常。本任务确保脚本被直接调用时 `main()` 不会意外退出（桩函数返回空 dict 也不会触发报告打印分支）。
6. **sys.path 污染**: 只在 `if __name__ == "__main__"` 块内做 `sys.path.insert(0, '.')`，避免模块导入时改路径。
7. **入口保护**: `main()` 只被 `if __name__ == "__main__":` 调用；`run_validation` 可被外部 import 调用。

## 非目标

- ❌ 不实现 weather 数据质量检查（task-02）。
- ❌ 不实现 ablation 实验（task-03）。
- ❌ 不实现 JSON/Markdown 报告写入（task-04）。
- ❌ 不修改 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster`、`ShandongDataLoader`。
- ❌ 不添加测试用例（task-05）。
- ❌ 不更新模块文档（task-06）。
- ❌ 不运行完整验证（task-07）。
- ❌ 不创建报告输出目录（task-04 负责）。
- ❌ 不引入 `pandas`、`ShandongDataLoader`、`FeatureEngineer` 或 `XGBoostForecaster` 之外的额外依赖——桩阶段只依赖标准库 + logger，import 这些模块仅作 import 验证（不调用实际构造）。

## 参考

- `design.md:97-99` — 文件变更清单中 validate_weather_tier4.py 为新增。
- `design.md:107-124` — CLI 接口定义：5 个参数、预期 `--help` 输出、调用示例。
- `design.md:126-137` — `run_validation` 的函数签名和职责说明。
- `plan.md:49-51` — task-01 覆盖 FR-01、FR-06、D-003@v1。
- `plan.md:34` — AC-01 要求脚本可运行。
- `verify_time_resolution.py` — 现有验证脚本的风格参考（shebang `#!/usr/bin/env python3`, `sys.path.insert(0, '.')`, logger 配置, argparse 用法）。
- `features.py:215-302` — `add_tier4_weather_features` 签名（`weather_cache_path` 和 `fetch_if_missing` 参数名与脚本 CLI 对齐）。

## TDD 步骤

```text
1.  [RED] 创建空文件 `validate_weather_tier4.py`，运行 `python -c "import py_compile; py_compile.compile('ellectric/scripts/validate_weather_tier4.py', doraise=True)"` 确认语法通过。
2.  [GREEN] 写入模块 docstring + 标准库 import + logger 定义 + argparse 入口 + `main()` 桩 + `run_validation()` 桩。编译通过。
3.  [RED] 运行 `python ellectric/scripts/validate_weather_tier4.py --help` — 确认输出包含 5 个参数和默认值说明。
4.  [GREEN] 调整 argparse 定义直到 `--help` 输出匹配预期的 help 文本。
5.  [RED] 运行 `python ellectric/scripts/validate_weather_tier4.py` — 确认 INFO 日志打印入参，无报错退出码 0。
6.  [GREEN] 调整桩实现直到上述命令正常退出并打印 logger 信息。
7.  [RED] Python import 测试: `python -c "from ellectric.scripts.validate_weather_tier4 import run_validation; result = run_validation(); assert result == {'status': 'stub', 'report_paths': []}"` — 确认返回结构正确。
8.  [GREEN] 修复 import 路径或返回值直到断言通过。
9.  [REFACTOR] 确认 `sys.path.insert(0, '.')` 只在 `if __name__ == "__main__"` 块内出现，import 路径不污染。
```

## 验收标准

| ID | 标准 | 验证方式 | 关联需求/决策 |
|----|------|----------|---------------|
| AC-01-01 | `python ellectric/scripts/validate_weather_tier4.py --help` 输出包含 --output-dir / --start / --end / --weather-cache / --no-fetch | 运行 `--help` | FR-01 |
| AC-01-02 | 不带参数运行脚本退出码 0，INFO 日志记录入参 | 运行脚本 + 检查日志 | FR-01 |
| AC-01-03 | `run_validation()` 可通过 `from ellectric.scripts.validate_weather_tier4 import run_validation` 导入并调用返回 dict | Python import 测试 | FR-01 |
| AC-01-04 | 返回 dict 包含 status="stub" 和 report_paths=[] | 断言返回值 | FR-01 |
| AC-01-05 | `main()` 中 `run_validation()` 入参映射正确：`start=args.start`, `end=args.end`, `output_dir=args.output_dir`, `weather_cache=args.weather_cache`, `fetch_if_missing=not args.no_fetch` | 阅读代码确认 | D-003@v1 |
| AC-01-06 | `--no-fetch` 默认为 False（即 fetch_if_missing=True） | argparse 默认值检查 | D-003@v1 |
| AC-01-07 | 未修改 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster` 的代码 | diff 检查 | FR-06 |
| AC-01-08 | 未修改 `ellectric/pipeline/` 下任何文件 | diff 检查 | FR-06 |
| AC-01-09 | `sys.path.insert(0, '.')` 仅在 `if __name__ == "__main__"` 块内出现 | 代码审查 | D-003@v1 |
