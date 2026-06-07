"""
回测引擎 — 历史数据回放与多策略对比
==================================

在历史负荷和电价数据上回放交易策略，
支持基线策略（持续法、均值法、oracle）和 RL 智能体，
提供多策略对比分析和累计 P&L 可视化。

Backtesting engine for historical data replay and multi-strategy comparison.
Replays trading strategies on historical load and price data,
supports baseline strategies (persistence, mean, oracle) and RL agents,
with multi-strategy comparison and cumulative P&L visualization.
"""

import logging
import re
from typing import Any, Callable, Optional, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ellectric.pipeline.rl_trainer import BaseRLAgent
from ellectric.pipeline.trading_env import ElectricityMarketEnv

logger = logging.getLogger(__name__)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ════════════════════════════════════════════════════════════
# 基线策略
# ════════════════════════════════════════════════════════════


def baseline_persistence(env: ElectricityMarketEnv, t: int) -> np.ndarray:
    """
    持续法策略 — 用 24 小时前负荷作为投标。

    Uses load from 24 hours ago as the bid schedule (persistence forecast).

    Args:
        env: 交易环境实例
        t: 当前 24h 块的起始行索引

    Returns:
        归一化投标向量 (0~1), shape (24,), dtype float32
    """
    capacity = env._max_capacity
    if t >= 24:
        bid = env._load_data["load_mw"].iloc[t - 24 : t].values.astype(np.float64)
    else:
        bid = np.zeros(24, dtype=np.float64)
    return np.clip(bid / capacity, 0, 1).astype(np.float32)


def baseline_mean(env: ElectricityMarketEnv, t: int) -> np.ndarray:
    """
    均值策略 — 用过去 168 小时（7 天）均值作为全天投标。

    Uses the mean load over the past 168 hours (7 days) as a flat bid.

    Args:
        env: 交易环境实例
        t: 当前 24h 块的起始行索引

    Returns:
        归一化投标向量 (0~1), shape (24,), dtype float32
    """
    capacity = env._max_capacity
    if t >= 168:
        past = env._load_data["load_mw"].iloc[t - 168 : t].values
        mean_val = past.mean() / capacity
    else:
        mean_val = 0.0
    return np.full(24, mean_val, dtype=np.float32)


def oracle_strategy(env: ElectricityMarketEnv, t: int) -> np.ndarray:
    """
    Oracle 策略 — 用实际负荷作为投标（完美预见/理论上限）。

    Uses actual load as the bid (perfect foresight, theoretical upper bound).

    Args:
        env: 交易环境实例
        t: 当前 24h 块的起始行索引

    Returns:
        归一化投标向量 (0~1), shape (24,), dtype float32
    """
    capacity = env._max_capacity
    n = min(24, len(env._load_data) - t)
    bid = env._load_data["load_mw"].iloc[t : t + n].values.astype(np.float64)
    if n < 24:
        bid = np.pad(bid, (0, 24 - n), constant_values=0)
    return np.clip(bid / capacity, 0, 1).astype(np.float32)


_STRATEGY_MAP: dict[str, Callable] = {
    "baseline_persistence": baseline_persistence,
    "baseline_mean": baseline_mean,
    "oracle": oracle_strategy,
}

# 公开策略名列表，方便外部使用
SUPPORTED_STRATEGIES = list(_STRATEGY_MAP.keys())


# ════════════════════════════════════════════════════════════
# BacktestRunner
# ════════════════════════════════════════════════════════════


class BacktestRunner:
    """
    回测运行器 — 在历史数据上回放交易策略并对比性能。

    Replays trading strategies on historical data and compares performance.

    Args:
        env_factory: 返回新的 ElectricityMarketEnv 实例的可调用对象
                     用于创建自定义环境（如需 forecasters）
        initial_cash: 初始现金

    Example:
        >>> from ellectric.pipeline.trading_env import ElectricityMarketEnv
        >>> from ellectric.pipeline.backtester import BacktestRunner
        >>> ef = lambda: ElectricityMarketEnv(load, price, None, None)
        >>> runner = BacktestRunner(ef)
        >>> df = runner.replay("oracle", load, price, "2022-01-01", "2022-01-07")
        >>> runner.compare({"oracle": df})
    """

    def __init__(
        self,
        env_factory: Callable[[], ElectricityMarketEnv],
        initial_cash: float = 0.0,
    ):
        self._env_factory = env_factory
        self._initial_cash = initial_cash

    def replay(
        self,
        model: Optional[Union[BaseRLAgent, str]],
        load_data: pd.DataFrame,
        price_data: pd.DataFrame,
        start: str,
        end: str,
        strategy_name: str = "rl",
    ) -> pd.DataFrame:
        """
        在历史数据上回放交易策略。

        Replays a trading strategy on historical data, recording hourly trades.

        Args:
            model: BaseRLAgent 实例 / 策略名字符串 / None
                   - BaseRLAgent: 使用 RL 模型 predict 产生动作
                   - str: 使用对应名称的基线策略函数
                   - None: 使用 strategy_name 查找策略
            load_data: 负荷数据（含 timestamp, load_mw 列）
            price_data: 价格数据（含 timestamp, price_da 列）
            start: 回放开始日期 "YYYY-MM-DD"
            end: 回放结束日期 "YYYY-MM-DD"
            strategy_name: 结果中标记的策略名称

        Returns:
            DataFrame 包含列:
                timestamp, bid_mw, cleared_mw, clearing_price,
                actual_load, pnl_hourly, pnl_cumulative, strategy

        Raises:
            ValueError: start/end 格式非法、无数据、数据无重叠、未知策略
            TypeError: model 参数类型不合法
        """
        # ── 格式校验 ──────────────────────────────────────
        if not _DATE_PATTERN.match(start):
            raise ValueError(f"start '{start}' 格式非法，应为 YYYY-MM-DD")
        if not _DATE_PATTERN.match(end):
            raise ValueError(f"end '{end}' 格式非法，应为 YYYY-MM-DD")
        if start >= end:
            raise ValueError(f"start ({start}) 必须早于 end ({end})")

        # ── 确定策略 ──────────────────────────────────────
        strat_fn, label = self._resolve_strategy(model, strategy_name)

        # ── 复制 + 过滤时间范围 ───────────────────────────
        load = load_data.copy()
        price = price_data.copy()
        load, price = self._align_data(load, price, start, end)

        if len(load) == 0:
            raise ValueError(f"负荷数据在 {start}~{end} 范围内无数据")
        if len(price) == 0:
            raise ValueError(f"价格数据在 {start}~{end} 范围内无数据")

        # 检查 timestamp 列存在
        if "timestamp" not in load.columns or "timestamp" not in price.columns:
            raise ValueError("数据缺少 'timestamp' 列")

        # ── 检查重叠 ──────────────────────────────────────
        self._check_overlap(load, price)

        # ── 缺失值处理 ──────────────────────────────────────
        load = load.bfill().ffill()
        price = price.bfill().ffill()

        # ── 创建环境 ──────────────────────────────────────
        env = self._env_factory()
        env._load_data = load.reset_index(drop=True)
        env._price_data = price.reset_index(drop=True)
        env._max_capacity = load["load_mw"].max()
        env._current_step = 0
        obs, _ = env.reset()

        # ── 逐 24h 块回放 ──────────────────────────────────
        records: list[dict[str, Any]] = []
        cumulative_pnl = 0.0

        while True:
            t = env._current_step

            if strat_fn is None and not isinstance(model, BaseRLAgent):
                raise ValueError("无法解析策略函数")
            if strat_fn is not None:
                action = strat_fn(env, t)
            else:
                action = model.predict(obs, deterministic=True)

            obs, _reward, terminated, truncated, info = env.step(action)

            n_hours = len(info["bid_mw"])
            timestamps = load["timestamp"].iloc[t : t + n_hours].values

            for i in range(n_hours):
                cumulative_pnl += info["pnl_hourly"][i]
                records.append(
                    {
                        "timestamp": timestamps[i],
                        "bid_mw": info["bid_mw"][i],
                        "cleared_mw": info["cleared_volume"][i],
                        "clearing_price": info["clearing_price"][i],
                        "actual_load": info["actual_load"][i],
                        "pnl_hourly": info["pnl_hourly"][i],
                        "pnl_cumulative": cumulative_pnl,
                        "strategy": label,
                    }
                )

            if terminated or truncated:
                break

        df = pd.DataFrame(records)
        logger.info("回放完成: %s, %s~%s, %d 条记录", label, start, end, len(df))
        return df

    def compare(self, results: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        多策略对比 — 计算各策略绩效指标。

        Computes performance metrics for each strategy.

        Args:
            results: {策略名称: trades_df}，其中 trades_df 必须包含
                     pnl_hourly 和 pnl_cumulative 列

        Returns:
            DataFrame 包含列: 策略, 总收益, 夏普比率, 胜率, 最大回撤, 交易次数
        """
        rows: list[dict[str, Any]] = []
        for name, df in results.items():
            pnl = df["pnl_hourly"].values
            cum = df["pnl_cumulative"].values

            total_return = float(pnl.sum())
            n = len(pnl)

            sharpe = 0.0
            if pnl.std() > 1e-10:
                sharpe = float(pnl.mean() / pnl.std() * np.sqrt(8760))

            win_rate = float((pnl > 0).mean())

            peak = np.maximum.accumulate(cum)
            drawdown = cum - peak
            max_dd = float(drawdown.min())

            rows.append(
                {
                    "策略": name,
                    "总收益": total_return,
                    "夏普比率": sharpe,
                    "胜率": win_rate,
                    "最大回撤": max_dd,
                    "交易次数": n,
                }
            )

        result_df = pd.DataFrame(rows)
        self._log_oracle_dominance(results)
        return result_df

    @staticmethod
    def plot_comparison(
        results: dict[str, pd.DataFrame],
        title: str = "策略对比",
    ) -> go.Figure:
        """
        多策略累计 P&L 叠加图。

        Overlays cumulative P&L curves for all strategies.

        Args:
            results: {策略名称: trades_df}（同 compare() 输入格式）
            title: 图表标题

        Returns:
            Plotly Figure 对象
        """
        fig = go.Figure()
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        for i, (name, df) in enumerate(results.items()):
            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["pnl_cumulative"],
                    mode="lines",
                    name=name,
                    line=dict(color=colors[i % len(colors)], width=2),
                )
            )

        fig.update_layout(
            title=dict(text=title, font=dict(size=18)),
            xaxis_title="时间",
            yaxis_title="累计 P&L ($)",
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )
        return fig

    # ── 内部方法 ──────────────────────────────────────────

    @staticmethod
    def _resolve_strategy(
        model: Optional[Union[BaseRLAgent, str]],
        strategy_name: str,
    ) -> tuple[Optional[Callable], str]:
        """解析策略函数和标签名。"""
        if isinstance(model, BaseRLAgent):
            return None, strategy_name

        key = strategy_name if model is None else model
        if not isinstance(key, str):
            raise TypeError(
                f"model 参数类型不合法: {type(model)}，"
                f"应为 BaseRLAgent / str / None"
            )

        if key == "rl":
            raise ValueError(
                "使用 RL 策略时必须提供 BaseRLAgent 实例作为 model 参数"
            )

        fn = _STRATEGY_MAP.get(key)
        if fn is None:
            raise ValueError(f"未知策略: '{key}'，可选: {list(_STRATEGY_MAP)} + 'rl'")
        return fn, key

    @staticmethod
    def _align_data(
        load: pd.DataFrame,
        price: pd.DataFrame,
        start: str,
        end: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """对齐负荷和价格数据到 [start, end) 时间范围。"""
        for df in [load, price]:
            ts_col = _find_timestamp_col(df)
            if ts_col != "timestamp":
                df.rename(columns={ts_col: "timestamp"}, inplace=True)

        for df in [load, price]:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        load = load[(load["timestamp"] >= start) & (load["timestamp"] < end)]
        price = price[(price["timestamp"] >= start) & (price["timestamp"] < end)]

        return load.reset_index(drop=True), price.reset_index(drop=True)

    @staticmethod
    def _check_overlap(load: pd.DataFrame, price: pd.DataFrame) -> None:
        """检查 load 和 price 数据在 timestamp 上是否有重叠。"""
        merged = pd.merge(
            load[["timestamp"]],
            price[["timestamp"]],
            on="timestamp",
            how="inner",
        )
        if len(merged) == 0:
            raise ValueError("负荷数据与价格数据在回测范围内无重叠")

    @staticmethod
    def _log_oracle_dominance(results: dict[str, pd.DataFrame]) -> None:
        """若 oracle 存在于结果中，检查其总收益是否低于其他策略，打 warning。"""
        if "oracle" not in results:
            return
        oracle_total = results["oracle"]["pnl_hourly"].sum()
        for name, df in results.items():
            if name == "oracle":
                continue
            other_total = df["pnl_hourly"].sum()
            if other_total > oracle_total + 1e-6:
                logger.warning(
                    "Oracle 总收益 (%.2f) 低于 %s (%.2f)，预期 oracle 应为最优",
                    oracle_total,
                    name,
                    other_total,
                )


def _find_timestamp_col(df: pd.DataFrame) -> str:
    """在 DataFrame 中查找时间列名。"""
    for col in ["timestamp", "datetime", "date", "time"]:
        if col in df.columns:
            return col
    return "timestamp"
