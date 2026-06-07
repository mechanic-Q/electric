"""
Phase 4 — CLI 命令行工具
=========================

基于 typer 构建的 `el-cli` 命令行工具，提供 4 个子命令：
  - forecast:  负荷/电价预测
  - simulate:  电力市场仿真
  - backtest:  历史回测
  - explain:   SHAP 模型可解释性

用法:
    python -m ellectric.cli.main forecast load 24
    python -m ellectric.cli.main simulate summer_peak --days 7
    python -m ellectric.cli.main backtest 2022-08-01 2022-08-31 ppo --model-path model.zip
    python -m ellectric.cli.main explain xgboost 0 --json
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from typing import Any

import typer

from ellectric.service.schemas import (
    BacktestRequest,
    ExplainRequest,
    ForecastRequest,
    SimulateRequest,
)
from ellectric.service.handlers import (
    run_backtest,
    run_explain,
    run_forecast,
    run_simulate,
)

app = typer.Typer(name="el-cli", help="Ellectric CLI — AI+电力交易平台命令行工具")

# ── helpers ──


def _try_import_rich():
    """Try importing rich; return (None, None) on failure."""
    try:
        from rich.console import Console
        from rich.table import Table

        return Console, Table
    except ImportError:
        return None, None


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Plain-text table with fixed-width columns (fallback when rich unavailable)."""
    if not rows:
        return "(empty)"
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    sep = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    line = "-+-".join("-" * w for w in widths)
    body = "\n".join(
        " | ".join(c.ljust(w) for c, w in zip(row, widths)) for row in rows
    )
    return f"{sep}\n{line}\n{body}"


def _print_json(data: Any) -> None:
    """Serialize data to JSON and print to stdout."""
    try:
        if hasattr(data, "model_dump_json"):
            sys.stdout.write(data.model_dump_json(indent=2) + "\n")
        else:
            json.dump(data, sys.stdout, indent=2, default=str)
            sys.stdout.write("\n")
    except Exception as e:
        print(f"[ERROR] 序列化失败: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


def _print_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise typer.Exit(code=1)


def _print_rich_table(headers: list[str], rows: list[list[str]]) -> None:
    Console, Table = _try_import_rich()  # type: ignore
    console = Console()
    table = Table(show_header=True, header_style="bold")
    for h in headers:
        table.add_column(h)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def _output_table_or_json(
    headers: list[str],
    rows: list[list[str]],
    json_output: bool,
    json_data: Any = None,
) -> None:
    if json_output:
        _print_json(json_data)
        return
    Console, _ = _try_import_rich()
    if Console:
        _print_rich_table(headers, rows)
    else:
        print(_format_table(headers, rows))


# ── subcommands ──


@app.command()
def forecast(
    model: str = typer.Argument(..., help="预测模型: load|price"),
    horizon: int = typer.Argument(24, help="预测时长 (小时)"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
):
    """负荷/电价预测"""
    if horizon <= 0:
        _print_error("HORIZON 必须为正整数")
    try:
        req = ForecastRequest(model_type=model, horizon=horizon)
        result = run_forecast(req)
    except Exception as e:
        _print_error(f"{type(e).__name__}: {e}")

    headers = ["时间", "预测值"]
    rows = [
        [ts.isoformat(), f"{pred:.2f}"]
        for ts, pred in zip(result.timestamps, result.predictions)
    ]

    if result.metrics and result.metrics.mae is not None:
        headers += ["MAE", "RMSE", "MAPE"]
        m = result.metrics
        rows = [
            r + [f"{m.mae:.2f}", f"{m.rmse:.2f}", f"{m.mape:.2f}"]
            for r in rows
        ]

    _output_table_or_json(headers, rows, json_output, result)


@app.command()
def simulate(
    scenario: str = typer.Argument(..., help="场景: default|summer_peak|wind_high"),
    days: int = typer.Option(7, help="仿真天数"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
):
    """运行市场仿真"""
    if days < 1 or days > 365:
        _print_error("days 必须在 1-365 范围内")
    try:
        req = SimulateRequest(config=scenario, days=days)
        result = run_simulate(req)
    except Exception as e:
        _print_error(f"{type(e).__name__}: {e}")

    if json_output:
        _print_json(result)
        return

    avg_price = (
        sum(result.clearing_prices) / len(result.clearing_prices)
        if result.clearing_prices
        else 0
    )
    summary_rows = [
        ["状态", result.status],
        ["平均出清价", f"{avg_price:.2f} CNY"],
    ]
    Console, _ = _try_import_rich()
    if Console:
        from rich.table import Table

        t = Table(show_header=False)
        t.add_column("指标")
        t.add_column("值")
        for r in summary_rows:
            t.add_row(*r)
        Console().print(t)
    else:
        print(_format_table(["指标", "值"], summary_rows))

    if result.agent_profits:
        profit_headers = ["代理", "利润 (元)"]
        profit_rows = [
            [agent, f"{profit:,.2f}"] for agent, profit in result.agent_profits.items()
        ]
        Console, _ = _try_import_rich()
        if Console:
            t2 = Table(show_header=True, header_style="bold")
            t2.add_column("代理")
            t2.add_column("利润 (元)")
            for r in profit_rows:
                t2.add_row(*r)
            Console().print(t2)
        else:
            print(_format_table(profit_headers, profit_rows))


@app.command()
def backtest(
    start: str = typer.Argument(..., help="开始日期 YYYY-MM-DD"),
    end: str = typer.Argument(..., help="结束日期 YYYY-MM-DD"),
    strategy: str = typer.Argument(
        ...,
        help="策略: baseline_persistence|baseline_mean|oracle|ppo|sac|td3",
    ),
    model_path: str = typer.Option(None, "--model-path", help="RL 模型文件路径"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
):
    """历史回测"""
    try:
        start_date = date.fromisoformat(start)
    except ValueError:
        _print_error(f"日期格式无效: {start}，期望 YYYY-MM-DD")
    try:
        end_date = date.fromisoformat(end)
    except ValueError:
        _print_error(f"日期格式无效: {end}，期望 YYYY-MM-DD")

    try:
        req = BacktestRequest(
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            model_path=model_path if model_path else None,
        )
        result = run_backtest(req)
    except Exception as e:
        _print_error(f"{type(e).__name__}: {e}")

    headers = ["指标", "值"]
    rows = [["状态", result.status]]
    if result.sharpe_ratio is not None:
        rows.append(["Sharpe Ratio", f"{result.sharpe_ratio:.4f}"])
    else:
        rows.append(["Sharpe Ratio", "N/A"])

    if result.comparison:
        for name, val in result.comparison.items():
            rows.append([f"策略: {name}", f"{val:,.2f}"])

    _output_table_or_json(headers, rows, json_output, result)


@app.command()
def explain(
    model: str = typer.Argument(..., help="模型: xgboost|lear"),
    sample: int = typer.Argument(..., help="样本索引 (>=0)"),
    max_display: int = typer.Option(10, "--max-display", help="显示特征数 (1-50)"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
):
    """模型可解释性"""
    if sample < 0:
        _print_error("sample 必须 >= 0")
    if max_display < 1 or max_display > 50:
        _print_error("max_display 必须在 1-50 范围内")
    try:
        req = ExplainRequest(
            model_type=model,
            sample_index=sample,
            max_display=max_display,
        )
        result = run_explain(req)
    except Exception as e:
        _print_error(f"{type(e).__name__}: {e}")

    headers = ["#", "特征", "重要性"]
    rows = [
        [str(fi.rank), fi.name, f"{fi.importance:.4f}"]
        for fi in result.feature_importance
    ]

    _output_table_or_json(headers, rows, json_output, result)


@app.command()
def ask(
    question: str = typer.Argument(..., help="自然语言问题"),
):
    """用自然语言查询电力交易助手"""
    try:
        from ellectric.llm.agent import ask_agent

        answer = ask_agent(question)
        print(answer)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        print("提示: 请设置 DEEPSEEK_API_KEY 环境变量", file=sys.stderr)
        raise typer.Exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
