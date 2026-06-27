
---
schema_version: 1
doc_type: module-card
module_id: trading-env
---

# trading-env

## 定位

自建 gymnasium.Env 电力市场交易环境。将预测结果（负荷+电价）转化为交易决策的观察/动作/奖励闭环。
不依赖 ASSUME 框架，最大化学习透明度。

## 契约摘要

- `ElectricityMarketEnv(gym.Env)` — 核心环境类
  - `observation_space: gym.spaces.Dict` — 5 个 key: load_forecast_24h, price_forecast_24h, time_features, price_history_168h, account_state
  - `action_space: gym.spaces.Box(0, 1, (TimeConfig.points_per_day,))` — 24h 归一化投标量，15min 默认 96 点
  - `reset(seed, options) -> (obs, info)` — 重置环境
  - `step(action) -> (obs, reward, terminated, truncated, info)` — 推进 24 小时时间跨度
  - `_get_prediction() -> (np.ndarray, np.ndarray)` — 获取 24h 预测，shape 为 `TimeConfig.points_per_day`
- `RewardRegistry` — 奖励函数注册表
  - `register(name, fn)`, `get(name)`, `list()`, `register_builtin()`
  - 内置: profit_only, risk_adjusted, volume_penalty
- 出清逻辑: 价格接受者, cleared = min(bid, actual_load)

## 关键逻辑

- 消费 `XGBoostForecaster` 和 `LEARForecaster` 的 `predict()` 输出
- 使用 `FeatureEngineer` 生成时间特征
- 奖励函数通过 `RewardFunction(Protocol)` 接口可插拔

## 注意事项

- 不修改传入 DataFrame（内部做 copy）
- step() 前必须 reset()
- 动作空间自动 clip 到 [0, 1]

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
