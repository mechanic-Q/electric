---
id: task-07
title: LangChain Tools
priority: P1
estimated_hours: 2
depends_on: [task-04]
blocks: [task-08]
allowed_paths:
  - ellectric/llm/tools.py
---

# task-07: LangChain Tools

## 修改文件
- **新增**: `ellectric/llm/tools.py`

## 实现要求
1. 创建 `ellectric/llm/tools.py`，定义 3 个 `@tool` 函数，每个函数内部通过 `httpx.Client` POST 调用本机 FastAPI（参阅 design.md §7.5）
2. API base URL 从环境变量 `ELLECTRIC_API_URL` 读取，默认为 `http://localhost:8000`
3. 3 个 tool 分别对应 3 个 FastAPI 路由（来自 design.md §7.3）：
   - `query_forecast` → `POST /predict`
   - `run_simulation` → `POST /simulate`
   - `run_backtest` → `POST /backtest`
4. 每个 tool 必须：
   - 使用共享的 `httpx.Client(timeout=30)`（模块级单例，避免每次调用创建新连接）
   - 捕获 `httpx.HTTPError` / `httpx.RequestError` / `httpx.TimeoutException` 等异常
   - 错误时返回格式 `"API 服务不可用: {简要错误信息}"`（中文）
   - 正常时返回 JSON 格式化字符串（`json.dumps(resp.json(), indent=2, ensure_ascii=False)`）
   - docstring 全中文，说明功能、参数含义、返回值格式
5. 文件头部：模块 docstring 说明用途 + logging 初始化

## 接口定义（pseudocode）

```python
# ellectric/llm/tools.py

"""LangChain @tool 函数 —— 通过 HTTP 调用 Ellectric FastAPI 后端。

供 LangChain agent 使用的工具，每个工具以结构化 JSON
与 API 通信，处理网络错误并返回中文描述结果。

Tools for LangChain agents to interact with the Ellectric REST API.
"""

import json
import logging
import os

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_API_BASE = os.environ.get("ELLECTRIC_API_URL", "http://localhost:8000")
_CLIENT = httpx.Client(timeout=30.0)  # 模块级共享客户端


@tool
def query_forecast(model_type: str, horizon: int = 24) -> str:
    """查询负荷或电价预测结果。

    调用 Ellectric `/predict` API 获取未来 N 小时的预测值。

    Args:
        model_type: 预测类型 — 'load'（负荷预测）或 'price'（电价预测）
        horizon: 预测小时数，默认 24 小时。范围建议 1-168

    Returns:
        JSON 字符串，包含 timestamps 和 predictions 数组，
        以及 metrics（MAE, RMSE, MAPE）。
        如果 API 不可用，返回错误描述。

    Example:
        >>> result = query_forecast(model_type="load", horizon=48)
        >>> # result 包含未来 48 小时的负荷预测 JSON
    """
    try:
        resp = _CLIENT.post(
            f"{_API_BASE}/predict",
            json={"model_type": model_type, "horizon": horizon},
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except httpx.TimeoutException:
        return f"API 服务不可用: 请求超时 ({_API_BASE}/predict)"
    except httpx.HTTPStatusError as e:
        return f"API 服务不可用: HTTP {e.response.status_code} — {e.response.text[:200]}"
    except (httpx.RequestError, httpx.HTTPError) as e:
        return f"API 服务不可用: {type(e).__name__} — {e}"


@tool
def run_simulation(scenario: str = "default", days: int = 7) -> str:
    """运行电力市场仿真。

    调用 Ellectric `/simulate` API 在中国省间现货市场环境
    中运行指定天数的多智能体仿真。

    Args:
        scenario: 仿真场景 — 'default'（默认配置）,
            'summer_peak'（夏季高峰）、或 'wind_high'（高风电占比）
        days: 仿真天数，默认 7 天。范围建议 1-30

    Returns:
        JSON 字符串，包含 clearing_prices（出清价格序列）、
        dispatch（机组调度明细）、agent_profits（智能体利润）、
        以及 output_dir（结果文件路径）。
        如果 API 不可用，返回错误描述。

    Example:
        >>> result = run_simulation(scenario="summer_peak", days=14)
        >>> # result 包含 14 天夏季高峰仿真的出清结果 JSON
    """
    try:
        resp = _CLIENT.post(
            f"{_API_BASE}/simulate",
            json={"config": scenario, "days": days},
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except httpx.TimeoutException:
        return f"API 服务不可用: 请求超时 ({_API_BASE}/simulate)"
    except httpx.HTTPStatusError as e:
        return f"API 服务不可用: HTTP {e.response.status_code} — {e.response.text[:200]}"
    except (httpx.RequestError, httpx.HTTPError) as e:
        return f"API 服务不可用: {type(e).__name__} — {e}"


@tool
def run_backtest(start_date: str, end_date: str, strategy: str = "oracle") -> str:
    """运行历史交易回测。

    调用 Ellectric `/backtest` API 在指定时间范围内
    回放交易策略，计算累计 P&L 和多策略对比。

    Args:
        start_date: 回测起始日期，格式 YYYY-MM-DD
        end_date: 回测结束日期，格式 YYYY-MM-DD
        strategy: 策略名称，可选值 —
            'baseline_persistence'（持续性基线）、
            'baseline_mean'（均值基线）、
            'oracle'（先知策略）、
            'ppo'（PPO 强化学习）、
            'sac'（SAC 强化学习）、
            'td3'（TD3 强化学习）

    Returns:
        JSON 字符串，包含 cumulative_pnl（累计盈亏序列）、
        sharpe_ratio（夏普比率）、comparison（多策略关键指标对比）。
        如果 API 不可用，返回错误描述。

    Example:
        >>> result = run_backtest(
        ...     start_date="2022-08-01",
        ...     end_date="2022-08-31",
        ...     strategy="ppo"
        ... )
        >>> # result 包含 2022 年 8 月的 PPO 回测结果 JSON
    """
    try:
        resp = _CLIENT.post(
            f"{_API_BASE}/backtest",
            json={
                "start_date": start_date,
                "end_date": end_date,
                "strategy": strategy,
            },
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except httpx.TimeoutException:
        return f"API 服务不可用: 请求超时 ({_API_BASE}/backtest)"
    except httpx.HTTPStatusError as e:
        return f"API 服务不可用: HTTP {e.response.status_code} — {e.response.text[:200]}"
    except (httpx.RequestError, httpx.HTTPError) as e:
        return f"API 服务不可用: {type(e).__name__} — {e}"
```

## 边界处理（必填，≥5）

| # | 场景 | 处理方式 |
|---|------|---------|
| E-01 | FastAPI 服务未启动（ConnectionError） | `httpx.RequestError` 捕获，返回 `"API 服务不可用: ConnectError — …"` |
| E-02 | API 响应超时（慢仿真/大回测） | `httpx.TimeoutException` 捕获，返回 `"API 服务不可用: 请求超时 (/backtest)"` |
| E-03 | API 返回非 200（参数非法等） | `httpx.HTTPStatusError` 捕获，返回 `"API 服务不可用: HTTP 422 — …"`（截断 body 到 200 字符） |
| E-04 | `ELLECTRIC_API_URL` 未设置 | `os.environ.get()` 默认值 `http://localhost:8000` |
| E-05 | API 返回 body 中无 `status` 字段（schema 不一致） | `json.dumps()` 直接序列化原始响应，不做字段校验；由 LLM 自行判断内容 |
| E-06 | `json.dumps()` 含 NaN/Inf（pandas 数据） | `allow_nan=True`（httpx 默认）已处理；若 API 返回不规范 JSON，`resp.json()` 抛出 ValueError 不被当前 try 捕获 → 属于 caller 处理范围（agent.py 调用方捕获） |

## 非目标（本任务不做的事）

- 不修改 `api/server.py`（FastAPI 路由已由 task-04 实现）
- 不修改 `service/handlers.py` 或 `service/schemas.py`
- 不创建 `agent.py` 或 `chat.py`（task-08 / task-09 负责）
- 不在 tools.py 中加入 RAG（chromadb）或 embedding 功能
- 不处理 API 返回的 NaN/Inf 值（由 `json.dumps()` 默认 `allow_nan=True` 处理）
- 不用 `asyncio` / `httpx.AsyncClient`（LangChain 的 `@tool` 默认同步调用）
- 不添加重试逻辑或指数退避（MVP 级别，单次请求即可）

## TDD 步骤

1. **创建目录**: 确认 `ellectric/llm/` 目录存在（由 task-01 之后的 setup 保证；如果不存在则创建 `ellectric/llm/__init__.py`）
2. **实现 tools.py**: 写入 3 个 `@tool` 函数 + 共用的 `_CLIENT` 和 `_API_BASE`
3. **单元测试 - import**: `python -c "from ellectric.llm.tools import query_forecast, run_simulation, run_backtest"` 无报错
4. **单元测试 - tool 类型**: `python -c "from ellectric.llm.tools import query_forecast; assert callable(query_forecast); print(type(query_forecast))"` 输出 `<class 'langchain_core.tools.StructuredTool'>`
5. **集成测试 - API 未启动**: 设置 `ELLECTRIC_API_URL=http://localhost:19999`，运行 `query_forecast("load", 24)`，验证返回 `"API 服务不可用: …"`
6. **集成测试 - API 启动**: 启动 uvicorn（task-04），运行 3 个 tool 函数，验证返回合法 JSON 字符串

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `cat ellectric/llm/tools.py \| head -5` | 文件以模块 docstring（三引号）开头 |
| AC-02 | `python -c "from ellectric.llm.tools import query_forecast, run_simulation, run_backtest"` | 无 ImportError，3 个对象均为 `langchain_core.tools.StructuredTool` |
| AC-03 | `python -c "from ellectric.llm.tools import _API_BASE; print(_API_BASE)"` | 输出 `http://localhost:8000`（默认值） |
| AC-04 | `ELLECTRIC_API_URL=http://localhost:19999 python -c "from ellectric.llm.tools import query_forecast; print(query_forecast.invoke({'model_type':'load','horizon':24}))"` | 输出以 `"API 服务不可用:"` 开头 |
| AC-05 | uvicorn 启动后，`python -c "from ellectric.llm.tools import query_forecast; r=query_forecast.invoke({'model_type':'load','horizon':24}); print(r[:50])"` | 输出以 `{` 开头（合法 JSON）且不含 `"API 服务不可用"` |
| AC-06 | `grep -c '@tool' ellectric/llm/tools.py` | 返回 `3`（恰好 3 个 tool） |
| AC-07 | `python -c "from ellectric.llm.tools import query_forecast; print(query_forecast.description)"` | 输出中文描述，提及 'load' 和 'price' |
| AC-08 | `git diff --stat ellectric/pipeline/` | 无变更（pipeline 零改动验证） |
