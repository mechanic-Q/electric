---
id: task-06
title: 实现 `make_env` 工厂 + reward_fn="profit_only"
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-04, task-05]
blocks: [task-07, task-08]
requirement_ids: [FR-03]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  统一构造 ElectricityMarketEnv，确保所有算法的训练/回测 env 配置一致：profit_only 奖励、初始 cash=0、max_capacity 来自当前 load_df.load_mw.max()。
implementation:
  - 函数签名 `make_env(load_df, price_df, load_forecaster=None, price_forecaster=None) -> ElectricityMarketEnv`
  - 内部计算 `max_capacity = float(load_df["load_mw"].max())`
  - 调用 `ElectricityMarketEnv(load_df, price_df, load_forecaster, price_forecaster, initial_cash=0.0, max_capacity=max_capacity, reward_fn="profit_only")`
  - 返回 env，不调 reset
acceptance:
  - test_make_env_reward_fn：env._reward_fn 对应 RewardRegistry.get("profit_only")
  - test_make_env_action_space_96d：env.action_space.shape == (96,) （由 TimeConfig 决定）
  - test_make_env_obs_dict_keys：env.observation_space 含 5 个 Dict key
verify:
  - pytest tests/test_train_rl_full_dataset.py -q -k make_env
constraints:
  - 不修改 ElectricityMarketEnv 内部状态
  - 不复用 env 实例（每次调用 make_env 返回新实例避免状态污染）
  - max_capacity 必须 > 0；load_df 为空时抛 ValueError
