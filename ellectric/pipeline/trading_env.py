"""
电力市场交易环境 — Gymnasium 强化学习环境
==========================================

提供基于强化学习的电力交易 Gymnasium 环境。
智能体观察负荷/电价预测，提交 24 小时投标计划，
环境模拟市场出清并基于交易绩效计算奖励。

Electricity market trading environment for reinforcement learning.
The agent observes load/price forecasts, submits 24-hour bid schedules,
and the environment simulates market clearing with reward computation.

关键设计:
- 观测空间: Dict with 5 keys (load/price forecasts, time features, history, account)
- 动作空间: Box(0, 1, (24,)) — 归一化投标量
- 出清逻辑: 价格接受者，cleared = min(bid, actual_load)
- 奖励: 3 种内置函数 (profit_only, risk_adjusted, volume_penalty)
"""

import logging
from typing import Any, Callable, Optional, Protocol, Union

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium.spaces import Box, Dict

logger = logging.getLogger(__name__)


class RewardFunction(Protocol):
    """
    奖励函数协议 — 所有奖励函数必须实现此接口。

    Args:
        cleared_volume: 各小时出清量 (MW), shape (n_hours,)
        clearing_price: 各小时出清价格 ($/MWh), shape (n_hours,)
        pnl_hourly:     各小时盈亏, shape (n_hours,)
        info:           额外信息字典

    Returns:
        标量奖励值
    """

    def __call__(
        self,
        cleared_volume: np.ndarray,
        clearing_price: np.ndarray,
        pnl_hourly: np.ndarray,
        info: dict,
    ) -> float: ...


class RewardRegistry:
    """
    奖励函数注册表 — 注册和查询奖励函数。

    使用方式:
        >>> RewardRegistry.register_builtin()
        >>> fn = RewardRegistry.get("profit_only")
        >>> reward = fn(cleared, price, pnl, info)
        >>> RewardRegistry.list()
        ['profit_only', 'risk_adjusted', 'volume_penalty']
    """

    _registry: dict[str, "RewardFunction"] = {}

    @staticmethod
    def register(name: str, fn: "RewardFunction") -> None:
        """
        注册奖励函数。

        Args:
            name: 函数名称（用于查询）
            fn:   奖励函数实现
        """
        RewardRegistry._registry[name] = fn

    @staticmethod
    def get(name: str) -> "RewardFunction":
        """
        获取已注册的奖励函数。

        Args:
            name: 函数名称

        Returns:
            奖励函数

        Raises:
            KeyError: 名称不存在
        """
        if name not in RewardRegistry._registry:
            raise KeyError(f"Unknown reward: {name}")
        return RewardRegistry._registry[name]

    @staticmethod
    def list() -> list[str]:
        """返回所有已注册奖励函数名称列表。"""
        return list(RewardRegistry._registry.keys())

    @staticmethod
    def register_builtin() -> None:
        """
        注册 3 种内置奖励函数:
        - profit_only: 仅考虑总盈亏
        - risk_adjusted: 盈亏 - 风险惩罚 × 标准差
        - volume_penalty: 盈亏 - 过量投标惩罚
        """

        def _profit_only(
            cleared_volume: np.ndarray,
            clearing_price: np.ndarray,
            pnl_hourly: np.ndarray,
            info: dict,
        ) -> float:
            return float(pnl_hourly.sum())

        def _risk_adjusted(
            cleared_volume: np.ndarray,
            clearing_price: np.ndarray,
            pnl_hourly: np.ndarray,
            info: dict,
        ) -> float:
            risk_penalty = 1.0
            return float(pnl_hourly.sum() - risk_penalty * (pnl_hourly.std() + 1e-8))

        def _volume_penalty(
            cleared_volume: np.ndarray,
            clearing_price: np.ndarray,
            pnl_hourly: np.ndarray,
            info: dict,
        ) -> float:
            penalty = 0.5
            target_volume = 0.5
            mean_bid = info.get("mean_bid", 0.0)
            vol_penalty = penalty * max(0.0, mean_bid - target_volume) * 100.0
            return float(pnl_hourly.sum() - vol_penalty)

        RewardRegistry.register("profit_only", _profit_only)
        RewardRegistry.register("risk_adjusted", _risk_adjusted)
        RewardRegistry.register("volume_penalty", _volume_penalty)


# ── 注册内置奖励函数 ─────────────────────────────────────────
RewardRegistry.register_builtin()


class ElectricityMarketEnv(gym.Env):
    """
    电力市场交易强化学习环境。

    观测空间 (Dict):
        load_forecast_24h:  未来 24 小时负荷预测          (24,)
        price_forecast_24h: 未来 24 小时电价预测          (24,)
        time_features:      时间特征 (hour_sin/cos, dow_sin/cos)  (4,)
        price_history_168h: 过去 168 小时电价历史         (168,)
        account_state:      账户状态 [cash, progress]      (2,)

    动作空间 (Box):
        Box(0, 1, (24,)) — 归一化投标量
        实际投标量 (MW) = action * max_capacity

    出清逻辑:
        价格接受者模型: cleared = min(bid_mw, actual_load)
        P&L = -(bid_mw - actual_load) × price / 1000

    使用方式:
        >>> from ellectric.pipeline.trading_env import ElectricityMarketEnv
        >>> env = ElectricityMarketEnv(load_data, price_data, lf, pf)
        >>> obs, info = env.reset()
        >>> obs, reward, terminated, truncated, info = env.step(np.zeros(24))
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        load_data: pd.DataFrame,
        price_data: pd.DataFrame,
        load_forecaster: Any = None,
        price_forecaster: Any = None,
        initial_cash: float = 0.0,
        max_capacity: float = 1000.0,
        reward_fn: Union[str, "RewardFunction", Callable] = "profit_only",
        feature_engineer: Any = None,
    ):
        """
        Args:
            load_data:       负荷数据 (至少 48 行, 含 load_mw 列)
            price_data:      价格数据 (至少 48 行, 含 price_da 列)
            load_forecaster: XGBoostForecaster 实例
            price_forecaster: LEARForecaster 实例
            initial_cash:    初始现金
            max_capacity:    最大出力容量 (MW)
            reward_fn:       奖励函数名称或可调用对象
            feature_engineer: FeatureEngineer 实例 (可选)
        """
        super().__init__()

        # ── 数据校验 ──────────────────────────────────────────
        if len(load_data) < 48:
            raise ValueError(
                f"load_data 至少需要 48 行（实际 {len(load_data)} 行）"
            )
        if len(price_data) < 48:
            raise ValueError(
                f"price_data 至少需要 48 行（实际 {len(price_data)} 行）"
            )
        if "load_mw" not in load_data.columns:
            raise ValueError("load_data 必须包含 'load_mw' 列")
        if "price_da" not in price_data.columns:
            raise ValueError("price_data 必须包含 'price_da' 列")
        if "timestamp" not in load_data.columns:
            raise ValueError("load_data 必须包含 'timestamp' 列")
        if "timestamp" not in price_data.columns:
            raise ValueError("price_data 必须包含 'timestamp' 列")

        # ── 副本化，绝不修改调用方数据 ──────────────────────
        self._load_data = load_data.copy()
        self._price_data = price_data.copy()
        self._load_forecaster = load_forecaster
        self._price_forecaster = price_forecaster
        self._initial_cash = initial_cash
        self._max_capacity = max_capacity
        self._feature_engineer = feature_engineer

        # ── 奖励函数 ──────────────────────────────────────────
        if isinstance(reward_fn, str):
            self._reward_fn = RewardRegistry.get(reward_fn)
        else:
            self._reward_fn = reward_fn

        # ── 空间定义 ──────────────────────────────────────────
        self.observation_space = Dict(
            {
                "load_forecast_24h": Box(
                    0.0, np.inf, shape=(24,), dtype=np.float32
                ),
                "price_forecast_24h": Box(
                    0.0, np.inf, shape=(24,), dtype=np.float32
                ),
                "time_features": Box(
                    -1.0, 1.0, shape=(4,), dtype=np.float32
                ),
                "price_history_168h": Box(
                    0.0, np.inf, shape=(168,), dtype=np.float32
                ),
                "account_state": Box(
                    -np.inf, np.inf, shape=(2,), dtype=np.float32
                ),
            }
        )
        self.action_space = Box(0.0, 1.0, shape=(24,), dtype=np.float32)

        # ── 内部状态 ──────────────────────────────────────────
        self._current_step = 0
        self._cash = 0.0
        self._reset_called = False

    # ════════════════════════════════════════════════════════════
    # Gymnasium 核心接口
    # ════════════════════════════════════════════════════════════

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[dict, dict]:
        """重置环境到初始状态。

        Returns:
            (observation, info) 元组
        """
        super().reset(seed=seed)
        self._current_step = 0
        self._cash = self._initial_cash
        self._reset_called = True
        obs = self._build_observation()
        return obs, {"step": self._current_step, "cash": self._cash}

    def step(self, action: np.ndarray) -> tuple[dict, float, bool, bool, dict]:
        """执行一个 step 的电力交易。

        处理流程:
        1. 裁剪动作到 [0, 1] 范围
        2. 获取实际负荷和价格数据
        3. 计算出清量和盈亏
        4. 计算奖励
        5. 构建下一个观测

        Args:
            action: 24 维归一化投标向量

        Returns:
            (observation, reward, terminated, truncated, info)

        Raises:
            RuntimeError: 未调用 reset() 直接 step
        """
        if not self._reset_called:
            raise RuntimeError("call reset() first")

        # ── 动作裁剪 ──────────────────────────────────────────
        action = np.asarray(action, dtype=np.float32).ravel()
        if action.shape[0] != 24:
            raise ValueError(
                f"action 必须为 24 维（实际 {action.shape[0]}）"
            )
        if np.any((action < 0) | (action > 1)):
            logger.warning(
                f"Action 越界 [{action.min():.3f}, {action.max():.3f}]，已裁剪到 [0, 1]"
            )
        action = np.clip(action, 0.0, 1.0)

        # ── 获取实际数据 ──────────────────────────────────────
        start = self._current_step
        end = min(start + 24, len(self._load_data))
        n_hours = end - start

        actual_load = self._load_data["load_mw"].iloc[start:end].values.astype(np.float64)
        price = self._price_data["price_da"].iloc[start:end].values.astype(np.float64)

        # ── 出清与盈亏 ────────────────────────────────────────
        bid_mw = action[:n_hours] * self._max_capacity
        cleared = np.minimum(bid_mw, actual_load)
        pnl_hourly = -np.abs(bid_mw - actual_load) * price / 1000.0

        step_pnl = float(pnl_hourly.sum())
        self._cash += step_pnl
        self._current_step = end

        # ── 构建 info ─────────────────────────────────────────
        info: dict[str, Any] = {
            "step": self._current_step,
            "cash": self._cash,
            "total_pnl": step_pnl,
            "cleared_volume": cleared.copy(),
            "clearing_price": price.copy(),
            "pnl_hourly": pnl_hourly.copy(),
            "mean_bid": float(action[:n_hours].mean()),
            "bid_mw": bid_mw.copy(),
            "actual_load": actual_load.copy(),
        }

        # ── 奖励 ──────────────────────────────────────────────
        reward = self._compute_reward(cleared, price, pnl_hourly, info)

        # ── 终止判断 ──────────────────────────────────────────
        terminated = self._current_step >= len(self._load_data)
        truncated = False

        # ── 下一个观测 ────────────────────────────────────────
        obs = self._build_observation()

        return obs, float(reward), terminated, truncated, info

    # ════════════════════════════════════════════════════════════
    # 内部方法
    # ════════════════════════════════════════════════════════════

    def _build_observation(self) -> dict:
        """构建当前观测字典（5 个 key）。"""
        load_pred, price_pred = self._get_prediction()

        # ── 时间特征 — sin/cos 编码 ─────────────────────────
        current_time = self._get_current_timestamp()
        hour = current_time.hour
        day_of_week = current_time.dayofweek
        time_features = np.array(
            [
                np.sin(2 * np.pi * hour / 24),
                np.cos(2 * np.pi * hour / 24),
                np.sin(2 * np.pi * day_of_week / 7),
                np.cos(2 * np.pi * day_of_week / 7),
            ],
            dtype=np.float32,
        )

        # ── 价格历史 (过去 168 小时) ─────────────────────────
        if self._current_step >= 168:
            price_history = (
                self._price_data["price_da"]
                .iloc[self._current_step - 168 : self._current_step]
                .values.astype(np.float32)
            )
        else:
            available = self._price_data["price_da"].iloc[: self._current_step].values.astype(np.float32)
            if len(available) == 0:
                price_history = np.zeros(168, dtype=np.float32)
            else:
                price_history = np.pad(available, (168 - len(available), 0), mode="edge")

        # ── 账户状态 ──────────────────────────────────────────
        total_steps = max(len(self._load_data), 1)
        progress = min(self._current_step / total_steps, 1.0)
        account_state = np.array(
            [self._cash, progress], dtype=np.float32
        )

        return {
            "load_forecast_24h": load_pred,
            "price_forecast_24h": price_pred,
            "time_features": time_features,
            "price_history_168h": price_history,
            "account_state": account_state,
        }

    def _get_prediction(self) -> tuple[np.ndarray, np.ndarray]:
        """获取未来 24 小时负荷和电价预测。

        优先级:
        1. 训练好的 forecaster 模型
        2. 持续法（取最近 24 小时实际值）
        3. 零向量

        Returns:
            (load_forecast_24h, price_forecast_24h), 均为 (24,) float32
        """
        load_pred = self._predict_with_model(
            self._load_forecaster, self._load_data, "load_mw"
        )
        price_pred = self._predict_with_model(
            self._price_forecaster, self._price_data, "price_da"
        )

        if load_pred is None:
            load_pred = self._persistence_forecast(self._load_data, "load_mw")
        if price_pred is None:
            price_pred = self._persistence_forecast(self._price_data, "price_da")

        return load_pred.astype(np.float32), price_pred.astype(np.float32)

    def _predict_with_model(
        self,
        forecaster: Any,
        data: pd.DataFrame,
        target_col: str,
    ) -> Optional[np.ndarray]:
        """使用训练好的模型预测，失败返回 None。"""
        if forecaster is None:
            return None
        if not hasattr(forecaster, "_model") or forecaster._model is None:
            return None
        if not hasattr(forecaster, "_feature_cols") or forecaster._feature_cols is None:
            return None

        try:
            feature_cols = forecaster._feature_cols
            feat_df = self._build_feature_frame(feature_cols, data, target_col)
            if feat_df is None:
                return None
            pred = forecaster.predict(feat_df)
            if pred is not None and len(pred) >= 24:
                return np.array(pred[:24], dtype=np.float32)
        except Exception as e:
            logger.warning(f"{target_col} 模型预测失败: {e}")

        return None

    def _build_feature_frame(
        self,
        feature_cols: list[str],
        data: pd.DataFrame,
        target_col: str,
    ) -> Optional[pd.DataFrame]:
        """为未来 24 小时构建预测特征 DataFrame。"""
        start = self._current_step
        n_hours = 24

        # ── 构建时间戳 ────────────────────────────────────────
        current_ts = self._get_current_timestamp()
        times = pd.date_range(
            start=current_ts,
            periods=n_hours,
            freq="h",
        )

        df = pd.DataFrame({"timestamp": times})
        df[target_col] = np.nan

        # ── 日历特征 ──────────────────────────────────────────
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["month"] = df["timestamp"].dt.month
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        # ── 循环编码 ──────────────────────────────────────────
        if "hour_sin" in feature_cols:
            df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        if "hour_cos" in feature_cols:
            df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

        # ── 24 小时滞后 ───────────────────────────────────────
        lag_24h_name = "lag_24h" if "lag_24h" in feature_cols else None
        if lag_24h_name is None:
            lag_24h_name = (
                "lag_24h_price"
                if "lag_24h_price" in feature_cols
                else None
            )
        if lag_24h_name and start >= 24:
            df[lag_24h_name] = (
                data[target_col]
                .iloc[start - 24 : start]
                .values[:n_hours]
            )
        elif lag_24h_name:
            df[lag_24h_name] = 0.0

        # ── 168 小时滞后 ──────────────────────────────────────
        lag_168h_name = "lag_168h" if "lag_168h" in feature_cols else None
        if lag_168h_name is None:
            lag_168h_name = (
                "lag_168h_price"
                if "lag_168h_price" in feature_cols
                else None
            )
        if lag_168h_name and start >= 168:
            df[lag_168h_name] = data[target_col].iloc[start - 168 : start - 168 + n_hours].values
        elif lag_168h_name:
            df[lag_168h_name] = 0.0

        # ── 滚动统计 ──────────────────────────────────────────
        if start >= 24:
            hist_window = data[target_col].iloc[max(0, start - 24) : start]
            if "rolling_mean_24h" in feature_cols:
                df["rolling_mean_24h"] = float(hist_window.mean())
            if "rolling_std_24h" in feature_cols:
                df["rolling_std_24h"] = float(hist_window.std())
        else:
            if "rolling_mean_24h" in feature_cols:
                df["rolling_mean_24h"] = 0.0
            if "rolling_std_24h" in feature_cols:
                df["rolling_std_24h"] = 0.0

        # ── LEAR 负荷滞后 (用于电价预测) ─────────────────────
        if "lag_24h_load" in feature_cols and start >= 24:
            df["lag_24h_load"] = (
                self._load_data["load_mw"]
                .iloc[start - 24 : start]
                .values[:n_hours]
            )
        elif "lag_24h_load" in feature_cols:
            df["lag_24h_load"] = 0.0

        if "lag_24h_wind" in feature_cols and start >= 24:
            wind_vals = data["wind_mw"].iloc[start - 24 : start].values if "wind_mw" in data.columns else np.zeros(n_hours)
            df["lag_24h_wind"] = wind_vals
        elif "lag_24h_wind" in feature_cols:
            wind_vals = data["wind_mw"].iloc[:start].values if "wind_mw" in data.columns and start > 0 else np.zeros(n_hours)
            df["lag_24h_wind"] = np.pad(wind_vals, (n_hours - len(wind_vals), 0), mode="edge")
        if "lag_24h_solar" in feature_cols and start >= 24:
            solar_vals = data["solar_mw"].iloc[start - 24 : start].values if "solar_mw" in data.columns else np.zeros(n_hours)
            df["lag_24h_solar"] = solar_vals
        elif "lag_24h_solar" in feature_cols:
            solar_vals = data["solar_mw"].iloc[:start].values if "solar_mw" in data.columns and start > 0 else np.zeros(n_hours)
            df["lag_24h_solar"] = np.pad(solar_vals, (n_hours - len(solar_vals), 0), mode="edge")

        # ── 价格趋势 (LEAR tier3) ────────────────────────────
        if "price_trend_7d" in feature_cols and start >= 168:
            df["price_trend_7d"] = float(
                data[target_col].iloc[start - 168 : start].mean()
            )
        elif "price_trend_7d" in feature_cols:
            df["price_trend_7d"] = 0.0

        # ── 假期特征 (FeatureEngineer tier2) ─────────────────
        if "is_holiday" in feature_cols:
            df["is_holiday"] = 0

        # ── 只返回需要列，按正确顺序 ─────────────────────────
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            logger.warning(f"特征列缺失: {missing}，跳过模型预测")
            return None

        return df[feature_cols]

    def _persistence_forecast(
        self, data: pd.DataFrame, target_col: str
    ) -> np.ndarray:
        """持续法预测：用最近 24 小时实际值作为预测。"""
        start = self._current_step
        if start >= 24:
            return (
                data[target_col]
                .iloc[start - 24 : start]
                .values.astype(np.float32)
            )
        return np.zeros(24, dtype=np.float32)

    def _compute_reward(
        self,
        cleared: np.ndarray,
        price: np.ndarray,
        pnl: np.ndarray,
        info: dict,
    ) -> float:
        """调用注册的奖励函数计算奖励。"""
        return self._reward_fn(cleared, price, pnl, info)

    def _get_current_timestamp(self) -> pd.Timestamp:
        """获取当前 step 对应的时间戳。"""
        idx = min(self._current_step, len(self._load_data) - 1)
        if "timestamp" in self._load_data.columns:
            return pd.Timestamp(self._load_data["timestamp"].iloc[idx])
        return pd.Timestamp.now()
