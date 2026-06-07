"""
LangChain 工具函数 —— 通过 HTTP 调用 Ellectric FastAPI 后端。

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
        scenario: 仿真场景 — 'default'（默认配置）、
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
