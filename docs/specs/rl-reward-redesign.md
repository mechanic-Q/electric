# RL Agent Reward Redesign: Speculator Spread Model

## Problem Statement

As a developer learning AI + electricity trading, I trained RL agents (PPO/SAC/TD3) on the Shandong 15min dataset expecting them to learn profitable trading. But every strategy — including the Oracle (perfect foresight) — produces negative total P&L. The RL agents (-139M to -197M) perform worse than naive baselines. I cannot tell whether the bug is in the training, the data, or the environment, and I have no path to positive returns.

## Solution

Redesign the trading environment so that the agent acts as a **pure speculator** exploiting price spreads, rather than a load-forecasting bidder penalized for any deviation. The agent takes directional positions (long/short) and profits when the realized price moves relative to a rolling baseline — exactly the structure a speculator needs. Add reward scaling so SB3 algorithms can converge.

## User Stories

1. As a learner, I want the Oracle (perfect foresight) strategy to show positive total P&L, so that I have a meaningful theoretical upper bound to compare against.
2. As a learner, I want at least one RL agent to achieve positive total P&L on the test window, so that I can see RL actually learns a profitable policy.
3. As a learner, I want RL agents to beat the simple trend baseline, so that I know the learning adds value beyond a trivial heuristic.
4. As a learner, I want the win rate to exceed 50%, so that the agent is right more often than not on directional bets.
5. As a learner, I want reward values in the O(10-100) range during training, so that PPO/SAC/TD3 gradients remain stable.
6. As a learner, I want the action space to represent long/short/flat positions, so that the agent can express directional views rather than just bid volumes.
7. As a learner, I want baseline strategies (trend, flat, oracle) that match the speculator model, so that comparisons are apples-to-apples.
8. As a learner, I want the P&L plot legend and description to reflect the speculator spread model, so that the visualization is honest about what is being measured.
9. As a learner, I want unit tests verifying the reward can be positive, so that regressions to the broken `-|bid-load|*price` formula are caught.
10. As a learner, I want unit tests verifying the action space bounds are `[-1, 1]`, so that accidental reverts to `[0, 1]` are caught.
11. As a learner, I want a quick validation mode (PPO 20k steps) so that I can sanity-check the reward signal before committing to a 3-4 hour full training run.
12. As a learner, I want training reports to record which reward function and price proxy were used, so that results are reproducible.
13. As a learner, I want the speculator baseline price to use a 7-day rolling mean, so that the reference point reflects recent market conditions rather than a single snapshot.
14. As a learner, I want the training hyperparameters tuned for the new reward landscape (lower learning rate, larger replay buffer), so that training is more likely to converge.
15. As a learner, I want the full training pipeline (PPO+SAC+TD3, 200k steps each) to run end-to-end and produce a comparison report, so that I can pick the best algorithm.

## Implementation Decisions

### Market role: pure speculator
The agent is a price-taker speculator with no physical assets. It takes directional positions on electricity price movements relative to a rolling baseline. This contrasts with the previous model where the agent bid generation volumes and was penalized for deviation from actual load.

### Reward formula: spread-based P&L
Replace the deviation-penalty formula with a spread model:
```
position_mw = action * max_capacity        # action ∈ [-1, 1]
baseline_price = 7-day rolling mean of price_da
pnl_hourly = position_mw * (price - baseline_price) / 1000
reward = sum(pnl_hourly) * reward_scale
```
A long position (action > 0) profits when `price > baseline`. A short position (action < 0) profits when `price < baseline`. The formula is symmetric and allows both positive and negative rewards.

### Reward scaling
Divide the raw P&L sum by `(max_capacity * price_std / 1000)` so that an Oracle-level step reward lands in the O(10-100) range instead of millions. This prevents SB3 value-function approximation from breaking down on large reward magnitudes.

### Action space: directional positions
Change `Box(0, 1, (96,))` to `Box(-1, 1, (96,))`. Each of the 96 dimensions is an independent 15-min directional position: -1 = max short, 0 = flat, +1 = max long.

### Baseline price computation
`_compute_baseline_price` returns the mean of the previous 7 days (672 steps) of `price_da`. For the first 7 days where history is insufficient, fall back to the mean of the current 96-step window.

### Baseline strategies redesigned
- `baseline_persistence` → `baseline_trend`: price-momentum signal from recent 24h percentage change, scaled to [-1, 1].
- `baseline_mean` → `baseline_flat`: always zero (no exposure).
- `oracle`: perfect foresight, returns +1 when future price > baseline, -1 otherwise.

### Training hyperparameters
- PPO: `learning_rate=3e-5, n_steps=2048, batch_size=128`
- SAC: `learning_rate=1e-4, buffer_size=100000`
- TD3: `learning_rate=1e-4, buffer_size=100000`
- Total timesteps per algo: 200,000 (up from 50,000)

### Data proxy unchanged
`rt_price` continues to proxy `price_da` because 75% of `da_price` is null in the Shandong dataset. This is documented in the training report metadata.

### Backtester info dict backward compatibility
The `info` dict retains the keys `bid_mw`, `cleared_volume`, `clearing_price`, `actual_load`, `pnl_hourly` so the backtester's replay loop and metrics computation work without changes. `bid_mw` now holds the signed position in MW. A new `baseline_price` key is added for traceability.

## Testing Decisions

### What makes a good test here
Tests should verify **external behavior** (reward can be positive, action bounds are correct, baseline strategies produce valid outputs) rather than implementation details (which numpy function was used). The highest-value tests are those that would have caught the original bug: a reward formula that can never be positive.

### Seam 1: Update existing integration test
`tests/test_train_rl_full_dataset.py::test_make_env_action_space` currently only asserts `_max_capacity is not None`. Update it to assert the action space bounds are `[-1, 1]`. This catches accidental reverts to the old `[0, 1]` bid-volume space.

### Seam 2: New unit test file
`tests/test_trading_env_reward.py` with 5 tests using the existing `tiny_shandong_df` fixture:
1. `test_action_space_is_directional` — `action_space.low == -1`, `action_space.high == 1`
2. `test_reward_can_be_positive` — construct an action aligned with price-vs-baseline direction, assert reward > 0
3. `test_reward_scaling_normalizes` — assert step reward magnitude is O(10-100), not millions
4. `test_oracle_strategy_directional` — oracle returns values in {-1, +1}
5. `test_flat_strategy_zero` — `baseline_mean` returns all zeros

### Prior art
`tests/test_train_rl_full_dataset.py` already uses a `tiny_shandong_df` fixture and `_FakeEnv` pattern. The new tests follow the same fixture style but exercise the real `ElectricityMarketEnv` rather than a mock, because the reward formula is the unit under test.

## Out of Scope

- **Day-ahead vs real-time price spread trading**: the dataset lacks sufficient non-null `da_price` to model true virtual bidding. `rt_price` proxies both.
- **Transaction costs / carry costs**: no per-step fee for holding positions. The speculator model is frictionless.
- **Position limits / risk constraints**: no per-step or per-episode cap on aggregate exposure beyond the action space bounds.
- **Multi-market or multi-node trading**: single province (Shandong), single price signal.
- **Action space dimensionality reduction**: keeping 96-dim continuous actions. If 200k steps is insufficient, dimensionality reduction is a follow-up.
- **Reward shaping beyond scaling**: no potential-based shaping, curiosity bonuses, or hierarchical rewards.
- **Alternative baseline prices**: 7-day rolling mean only. EMA, median, or forecast-based baselines are follow-ups if the 7-day mean proves too noisy.
- **WebUI / Copilot changes**: the showcase deployment reads offline reports only; no live RL execution is in scope.

## Further Notes

### Data validation supporting the design
Shandong 15min price data analysis (71432 non-null rows):
- Mean = 294.7 yuan/MWh, std = 205.1, range [-100, 1482.7]
- 15.9% negative prices (renewable-heavy market characteristic)
- `mean(price - 7d_rolling_mean) = -0.4` — slightly negative, meaning "always long" is a losing strategy. The agent must learn directional prediction.
- Price-change autocorrelation: lag-1 = 0.217, lag-96 = 0.190, lag-672 = 0.168 — meaningful but weak predictability.
- Oracle theoretical max over 10,080 test steps ≈ 170M yuan.
- Simple trend strategy over 10,080 test steps ≈ +7.5M yuan (validates the reward is learnable).

### Already-implemented changes (retroactive)
This spec captures work that was partly implemented during the grill phase before the spec was written:
- `trading_env.py`: reward formula, action space, `_compute_baseline_price`
- `backtester.py`: trend/flat/oracle baseline strategies, plot description and legend
- `train_rl_full_dataset.py`: timesteps 50k → 200k, per-algo hyperparameters

The remaining work (reward scaling, test updates, validation, full training, code review) is tracked via tickets.

### Worktree and merge policy
All changes live on the `rl-reward-redesign` branch in worktree `~/projects/Electric-rl-reward`. Merge to `master` only after the full test suite passes and the success criteria are met.

### Success criteria (summary)
| Metric | Old (broken) | Target |
|--------|--------------|--------|
| Oracle total P&L | -4.25 | > 0 (theoretical ~170M) |
| Best RL strategy | -139M | > 0 |
| RL vs trend baseline | RL worse | RL better |
| Win rate | 0.151 (noise floor) | > 0.50 |
