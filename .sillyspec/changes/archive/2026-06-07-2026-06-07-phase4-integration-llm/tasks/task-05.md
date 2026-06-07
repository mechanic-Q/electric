---
id: task-05
title: CLI 命令工具
priority: P0
estimated_hours: 2
depends_on: [task-03]
blocks: [task-06, task-10]
allowed_paths:
  - ellectric/cli/__init__.py
  - ellectric/cli/main.py
---

# task-05: CLI 命令工具

## 修改文件
- **新增**: `ellectric/cli/__init__.py`
- **新增**: `ellectric/cli/main.py`

## 实现要求
1. 创建 `ellectric/cli/__init__.py` 包标记文件
2. 实现 `ellectric/cli/main.py`，使用 **typer** 构建 `el-cli` 命令行工具，包含 4 个子命令：

### 2.1 `forecast` 命令
```
el-cli forecast <MODEL> <HORIZON>
```
- `MODEL`: `Literal["load", "price"]` (typer 参数，自动校验)
- `HORIZON`: `int`，正整数，默认 24
- 行为：构建 `ForecastRequest(model_type=MODEL, horizon=HORIZON)` → 调用 `run_forecast(req)` → 格式化输出
- 默认输出格式：表格显示时间戳 + 预测值 + 指标 (MAE/RMSE/MAPE)
- `--json` flag: 输出 `ForecastResponse` 的 JSON 字符串

### 2.2 `simulate` 命令
```
el-cli simulate <SCENARIO> [--days N]
```
- `SCENARIO`: `Literal["default", "summer_peak", "wind_high"]`
- `--days`: `int`，默认 7，范围 1-365
- 行为：构建 `SimulateRequest(config=SCENARIO, days=days)` → 调用 `run_simulate(req)` → 格式化输出
- 默认输出格式：表格显示小时级出清价格 + 代理利润汇总
- `--json` flag: 输出 `SimulateResponse` 的 JSON 字符串

### 2.3 `backtest` 命令
```
el-cli backtest <START> <END> <STRATEGY> [--model-path PATH]
```
- `START`: `str`，YYYY-MM-DD 格式日期字符串
- `END`: `str`，YYYY-MM-DD 格式日期字符串
- `STRATEGY`: `Literal["baseline_persistence", "baseline_mean", "oracle", "ppo", "sac", "td3"]`
- `--model-path`: `Optional[str]`，RL 策略需要模型文件路径
- 行为：解析日期为 `date` 对象 → 构建 `BacktestRequest` → 调用 `run_backtest(req)` → 格式化输出
- 默认输出格式：表格显示累计 P&L + Sharpe Ratio + 策略对比
- `--json` flag: 输出 `BacktestResponse` 的 JSON 字符串

### 2.4 `explain` 命令
```
el-cli explain <MODEL> <SAMPLE> [--max-display N]
```
- `MODEL`: `Literal["xgboost", "lear"]`
- `SAMPLE`: `int`，样本索引，最小 0
- `--max-display`: `int`，默认 10，范围 1-50
- 行为：构建 `ExplainRequest(model_type=MODEL, sample_index=SAMPLE, max_display=max_display)` → 调用 `run_explain(req)` → 格式化输出
- 默认输出格式：表格显示特征名称 + 重要性 + 排名
- `--json` flag: 输出 `ExplainResponse` 的 JSON 字符串

### 2.5 全局选项
- `--json`: 每个子命令支持此 flag，存在时输出 JSON 而非表格
- `--help`: typer 自动生成帮助信息

### 2.6 app 对象
```python
import typer

app = typer.Typer(name="el-cli", help="Ellectric CLI — AI+电力交易平台命令行工具")
```

3. **输出格式**：
   - 默认使用 `rich` 的 `Table` 组件渲染表格。如果 `rich` 不可用，降级为纯文本 `print`（不添加新依赖；Phase 4 requirements-phase4.txt 不包含 rich）
   - 用 `try: from rich.table import Table` 优雅降级，fallback 到 `tabulate()` 辅助函数（手写纯文本表格，如 `f"{'时间':<20} {'预测':<10}"`）
   - JSON 模式使用 `response.model_dump_json(indent=2)` (Pydantic v2)

4. **异常处理**：
   - 每个命令用 try/except 包裹 handler 调用
   - 捕获 `Exception` → 打印 `[ERROR] {message}` 到 stderr → `raise typer.Exit(code=1)`
   - typer 参数校验失败自动由 typer 处理并打印帮助

5. **命名约定**：
   - 命令函数名与 CLI 命令名一致：`def forecast(...)` → `el-cli forecast`
   - 参数名 snake_case，CLI 暴露 kebab-case（typer 自动转换 `model_path` → `--model-path`）

## 接口定义

```python
# ellectric/cli/main.py
import typer
from datetime import date
from ellectric.service.schemas import (
    ForecastRequest, SimulateRequest, BacktestRequest, ExplainRequest
)
from ellectric.service.handlers import (
    run_forecast, run_simulate, run_backtest, run_explain
)

app = typer.Typer(name="el-cli")

@app.command()
def forecast(
    model: str = typer.Argument(help="预测模型: load|price"),
    horizon: int = typer.Argument(24, help="预测时长 (小时)"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
): ...

@app.command()
def simulate(
    scenario: str = typer.Argument(help="场景: default|summer_peak|wind_high"),
    days: int = typer.Option(7, help="仿真天数"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
): ...

@app.command()
def backtest(
    start: str = typer.Argument(help="开始日期 YYYY-MM-DD"),
    end: str = typer.Argument(help="结束日期 YYYY-MM-DD"),
    strategy: str = typer.Argument(help="策略: baseline_persistence|baseline_mean|oracle|ppo|sac|td3"),
    model_path: Optional[str] = typer.Option(None, help="RL 模型文件路径"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
): ...

@app.command()
def explain(
    model: str = typer.Argument(help="模型: xgboost|lear"),
    sample: int = typer.Argument(help="样本索引 (>=0)"),
    max_display: int = typer.Option(10, help="显示特征数 (1-50)"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
): ...

if __name__ == "__main__":
    app()
```

## 边界处理（必填）

- 如果 `horizon <= 0`，typer 未提供内置 positive int 校验，在函数内手动验证 → `typer.BadParameter("HORIZON 必须为正整数")` 
- 如果 `days` 不在 1-365 范围，打印 `[ERROR] days 必须在 1-365 范围内` → `raise typer.Exit(1)`
- 如果 `sample < 0`，打印 `[ERROR] sample 必须 >= 0` → `raise typer.Exit(1)`
- 如果 `max_display` 不在 1-50 范围，打印 `[ERROR] max_display 必须在 1-50 范围内` → `raise typer.Exit(1)`
- 如果日期字符串格式无效 (`YYYY-MM-DD`)，`date.fromisoformat()` 抛出 `ValueError` → 捕获后打印 `[ERROR] 日期格式无效: {value}，期望 YYYY-MM-DD` → `raise typer.Exit(1)`
- 如果 handler 抛出任何异常，打印 `[ERROR] {type(e).__name__}: {e}` 到 stderr → `raise typer.Exit(code=1)`
- 如果 `rich` 未安装，fallback 到纯文本表格（用固定列宽 `ljust`/`rjust` 对齐）
- 如果 `--model-path` 用于非 RL 策略 (`baseline_*` / `oracle`)，忽略参数（不报错，仅不使用）
- `json_output=True` 时不打印任何表格头/边框，仅纯 JSON 到 stdout
- `schema_response.model_dump_json()` 失败时，捕获异常并打印 `[ERROR] 序列化失败: {e}` → `raise typer.Exit(1)`

## 非目标（本任务不做的事）

- 不实现 `el-cli ask` 命令（task-10 做）
- 不添加 `rich` 到 requirements-phase4.txt（MVP 用纯文本 fallback；如果满足 Phase 4 用户愿意加依赖则后续单独加）
- 不实现交互式对话 UI（LLM chat 在 task-09）
- 不实现进度条或动画（仿真/回测为同步执行，handler 返回即输出）
- 不实现子命令组（`el-cli simulate start` 等）——ROADMAP 写的 `simulate start` 简化为 `el-cli simulate`，因为每个命令仅一个动作
- 不实现 `--output` 文件保存 flag（stdout 输出即可，需要文件时用 shell 重定向）
- 不修改 `ellectric/pipeline/` 下任何文件
- 不修改 `ellectric/service/schemas.py` 或 `ellectric/service/handlers.py`（仅 import）
- 不创建 `pyproject.toml` 控制台脚本入口点——使用 `python -m ellectric.cli.main` 或 `PYTHONPATH=. python ellectric/cli/main.py` 运行

## TDD 步骤
1. **检查**: 确认 `ellectric/service/handlers.py` 存在且 4 个 handler 函数可 import → `python -c "from ellectric.service.handlers import run_forecast, run_simulate, run_backtest, run_explain; print('handlers OK')"`
2. **创建**: 写入 `ellectric/cli/__init__.py` (空包标记) + `ellectric/cli/main.py`（4 命令骨架，含 docstring + 参数校验 + try/except 异常包装，handler 调用先 stub 为 `print("TODO")`）
3. **连接 handlers**: 将 handler import 和调用写实，确保构造正确的 Pydantic 请求对象传给 handler
4. **格式化输出**: 实现 `format_output()` 辅助函数——`rich` Table 或纯文本 fallback，根据响应类型动态生成列
5. **验证语法**: `python -c "import ellectric.cli.main; print('CLI import OK')"` 不报错
6. **验证 help**: `python ellectric/cli/main.py --help` 显示 4 个命令
7. **验证各命令 help**: 逐命令跑 `--help` 确认参数说明正确
8. **集成测试**: `python -m ellectric.cli.main forecast load 24` 不报 `ImportError`（允许 handler 返回 NOTIMPLEMENTED，但 CLI 层必须跑通）

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `python ellectric/cli/main.py --help` | 输出包含 `el-cli` 名称和 4 个子命令 (forecast/simulate/backtest/explain) |
| AC-02 | `python ellectric/cli/main.py forecast --help` | 输出包含 `MODEL` 参数帮助和 `--json` flag |
| AC-03 | `python ellectric/cli/main.py simulate --help` | 输出包含 `SCENARIO` 和 `--days` 参数说明 |
| AC-04 | `python ellectric/cli/main.py backtest --help` | 输出包含 `START` `END` `STRATEGY` 参数和 `--model-path` 选项 |
| AC-05 | `python ellectric/cli/main.py explain --help` | 输出包含 `MODEL` `SAMPLE` 和 `--max-display` 选项 |
| AC-06 | `python ellectric/cli/main.py forecast invalid_model 24` | typer 提示 `invalid_model` 不是合法值（Literal 校验自动），exit 非 0 |
| AC-07 | `python ellectric/cli/main.py forecast load -5` | CLI 打印 `[ERROR] HORIZON 必须为正整数` 到 stderr，exit 1 |
| AC-08 | `python ellectric/cli/main.py simulate default --days 400` | CLI 打印 `[ERROR] days 必须在 1-365 范围内`，exit 1 |
| AC-09 | `python ellectric/cli/main.py backtest not-a-date 2022-08-31 oracle` | CLI 打印 `[ERROR] 日期格式无效: not-a-date`，exit 1 |
| AC-10 | `python ellectric/cli/main.py explain xgboost 0` | 不报 ImportError，handler 调用执行（handler 内部可抛 NotImplementedError 但 CLI 层正常包装并输出 stderr） |
| AC-11 | `python ellectric/cli/main.py forecast load 24 --json` | stdout 仅 JSON 字符串，无表格边框/头，exit 0 |
| AC-12 | `python -c "from ellectric.cli.main import app; assert app.info.name == 'el-cli'; print('OK')"` | 输出 `OK` |
