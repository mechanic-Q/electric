---
author: lmr
created_at: 2026-06-07 23:55:29
id: task-10
title: LLM 集成到 CLI (ask 命令)
priority: P1
estimated_hours: 1
depends_on: [task-05, task-09]
blocks: []
allowed_paths:
  - ellectric/cli/main.py
---

# task-10: LLM 集成到 CLI (ask 命令)

## 修改文件
- **修改**: `ellectric/cli/main.py`（追加 `ask` 命令，无import改动）

## 实现要求

在 `ellectric/cli/main.py` 的 `app` 上新增一个 `ask` 子命令：

```python
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
```

### 关键约束

1. **lazy import** — `from ellectric.llm.agent import ask_agent` 必须在函数体内部执行。不在模块顶部 import。原因：LLM 依赖（langchain, httpx）可能未安装，lazy import 确保 `el-cli forecast`, `el-cli simulate`, `el-cli backtest`, `el-cli explain` 不依赖 LLM 模块。

2. **Exception 分两层**：
   - `RuntimeError` — 已知可预测错误（如 DEEPSEEK_API_KEY 未设置），打印友好中文错误 + 配置提示 + `exit(1)`
   - `Exception` — 其他未知错误（API 超时、网络错误、LLM 响应解析失败），打印错误消息 + `exit(1)`

3. **stdout vs stderr**:
   - 正常回答 → stdout（可 pipe/重定向）
   - 错误消息 → stderr（不污染管道输出）

4. **exit code**:
   - 成功 → 0
   - LLM 调用失败 → 1

### 不需要的功能

- 不需要 `--json` flag（ask 命令输出是自然语言文本，非结构化数据）
- 不需要 `--model` 或 `--temperature` 等 LLM 参数（由 agent.py 内部配置）

## 接口定义

```python
# 追加到 ellectric/cli/main.py 末尾（explan 命令之后、if __name__ 块之前）

# 注意：文件顶部无需新增 import — ask_agent 是 lazy import

# ── sys 已在文件顶部 import（用于 stderr） ──

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
```

## 边界处理（必填，≥5）

| # | 场景 | 处理方式 |
|---|------|---------|
| E-01 | `DEEPSEEK_API_KEY` 未设置 | `agent.py` 内部构造函数检测环境变量缺失，抛出 `RuntimeError("DEEPSEEK_API_KEY 未设置")` → CLI 层 `except RuntimeError` 捕获，stderr 打印 `"错误: DEEPSEEK_API_KEY 未设置"` + `"提示: 请设置 DEEPSEEK_API_KEY 环境变量"` → `raise typer.Exit(1)` |
| E-02 | DeepSeek API 返回 HTTP 4xx/5xx | `agent.py` 内部 `httpx.HTTPStatusError` 捕获并重新抛出（封装为 `RuntimeError` 或自定义异常子类 Exception） → CLI `except Exception` 捕获 → stderr 打印错误消息 → `raise typer.Exit(1)` |
| E-03 | LLM 依赖（langchain/httpx）未安装 | `import ellectric.llm.agent` 抛出 `ModuleNotFoundError`（非 `RuntimeError`） → `except Exception` 捕获 → stderr 打印 `"错误: LLM 依赖未安装，请运行 pip install -r ellectric/requirements-phase4.txt"` → `raise typer.Exit(1)` |
| E-04 | question 为空字符串 | typer 的 `Argument(...)` 非 optional，typer 自动校验 `""` 不为空；如果用户不传参数，typer 打印帮助信息并 exit 2 |
| E-05 | network timeout / connection refused | `httpx.TimeoutException` / `httpx.RequestError` 在 agent.py 内部被转换为通用 `Exception` → CLI `except Exception` 捕获 → stderr 打印错误 → `raise typer.Exit(1)` |
| E-06 | agent.py 的 `ask_agent()` 返回异常（非字符串或为 None） | `agent.py` 内部 `.get("output", "")` 已处理空值（task-08）；若 `ask_agent()` 返回 `None` 或非字符串，CLI 用 `print(answer)` 正常输出（Python 默认 str 转换不会崩溃） |
| E-07 | typer 的 Argument 声明为非 optional（不带 default），用户未传参 | typer 自动报错并显示用法帮助，exit 2。CLI 不需要专门处理 |

## 非目标（本任务不做的事）

- 不修改 `agent.py`、`tools.py`、`chat.py` — LLM 逻辑层面的修改在 task-08/09 中完成
- 不修改 `schemas.py` 或 `handlers.py` — CLI 只消费 LLM 输出，不涉及 service layer
- 不修改 task-05 已有的 4 个命令实现
- 不添加 `--json` flag（自然语言问答无可预期的 JSON 格式输出）
- 不实现交互式多轮对话（`chat.py` 提供）；本任务仅单次 `el-cli ask "问题"`
- 不在函数外 import `ellectric.llm.agent` 的任何符号（必须 lazy import）
- 不再追加 `sys` import（task-05 的实现已有 `import sys` 或可追加）

## TDD 步骤

1. **检查前置**: 确认 `ellectric/cli/main.py` 存在且包含 `if __name__ == "__main__":` 区块 → `grep '__name__' ellectric/cli/main.py`
2. **追加代码**: 在 `explain` 命令函数后、`if __name__` 前插入 `ask` 命令代码块
3. **验证 help**: `python ellectric/cli/main.py ask --help` 显示 `question` 参数和 `用自然语言查询电力交易助手` 文档字符串
4. **验证 import**: `python -c "import ellectric.cli.main; app=ellectric.cli.main.app; cmds=[c.name for c in app.registered_commands]; assert 'ask' in cmds; print('OK')"` 输出 `OK`
5. **验证 lazy import 不影响其他命令**: `python ellectric/cli/main.py forecast --help` 正常输出（即使 LLM 依赖未安装）
6. **验证无 key 报错**: `unset DEEPSEEK_API_KEY; python ellectric/cli/main.py ask "预测负荷"` 输出应为 `"错误: DEEPSEEK_API_KEY 未设置"` + `"提示: 请设置 DEEPSEEK_API_KEY 环境变量"`，exit code 1
7. **验证 API key 存在**: `DEEPSEEK_API_KEY=sk-test python ellectric/cli/main.py ask "你好"` — 预期 agent.py 内的 API 调用失败（假 key），CLI 层 `except Exception` 捕获并 stderr 输出错误 + exit 1（不应崩溃 / bare Exception）
8. **验证空参数**: `python ellectric/cli/main.py ask`（不带 argument） — typer 报错并显示用法，exit 2

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `python ellectric/cli/main.py ask --help` | 输出包含 `question` 参数和 `用自然语言查询电力交易助手` docstring |
| AC-02 | `python -c "import ellectric.cli.main; cmds=[c.name for c in ellectric.cli.main.app.registered_commands]; assert 'ask' in cmds"` | `ask` 命令已注册到 typer app（5 个命令：forecast/simulate/backtest/explain/ask） |
| AC-03 | `python ellectric/cli/main.py forecast load 24`（LLM 依赖未安装） | 正常输出（不报错，`ask` 命令的 lazy import 不污染其他命令） |
| AC-04 | `python ellectric/cli/main.py simulate --help`（LLM 依赖未安装） | 正常显示帮助（证明模块顶部无 LLM import） |
| AC-05 | `DEEPSEEK_API_KEY="" python ellectric/cli/main.py ask "test"`（或 unset） | stderr 包含 `DEEPSEEK_API_KEY 未设置` 和 `请设置 DEEPSEEK_API_KEY`，exit code 1 |
| AC-06 | `python ellectric/cli/main.py ask`（无参数） | typer 打印 `Error: Missing argument 'QUESTION'`，exit code 2 |
| AC-07 | `grep 'from ellectric.llm' ellectric/cli/main.py` | 匹配行出现在 `def ask(` 函数体内（lazy import），不在文件顶部 |
| AC-08 | `python -c "import ellectric.cli.main" 2>&1; echo EXIT: $?" | 不检查 deepseek 依赖是否安装；只要 typer 能注册命令，import 即成功输出 `EXIT: 0` |
| AC-09 | `DEEPSEEK_API_KEY=sk-invalid-key python ellectric/cli/main.py ask "hello"` | CLI 不崩溃，stderr 输出错误消息（如 `"错误: 401 Client Error..."`），exit code 1 |
