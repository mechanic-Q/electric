---
author: lmr
created_at: 2026-06-29 01:39:00
---

# Decisions

## D-001@v1: 价格列代理使用 rt_price 重命名为 price_da

- type: architecture
- status: accepted
- source: user
- question: 山东 15min 数据 `da_price` 仅每小时 1 点（25% 覆盖），`rt_price` 99.9% 完整；trading_env / backtester 固定要求 `price_da` 列。如何选择？
- answer: 用 `rt_price` 重命名为 `price_da`，作为出清价代理。
- normalized_requirement: `build_datasets()` 必须在 `price_df` 中以 `price_da = rt_price.rename(...)` 提供 96 点逐点独立价格信号；不修改 ShandongDataLoader 原始列名；语义记录到报告 `metadata.price_proxy="rt_price->price_da"`。
- impacts: [Wave 1, design-Wave-1, FR-数据装配, R-04, training_report.metadata]
- evidence: 用户回答轮次 1 选 B；`ellectric/pipeline/shandong_loader.py:262-267` 记录 da_price 75% null。
- priority: P0

## D-002@v1: 三算法统一使用 profit_only 奖励函数

- type: architecture
- status: accepted
- source: user
- question: RewardRegistry 提供 profit_only / risk_adjusted / volume_penalty 三选项；本轮如何使用？
- answer: 三算法全部用 `profit_only`，保证算法间可比性。
- normalized_requirement: `make_env()` 必须固定 `reward_fn="profit_only"`；不接受按算法切换奖励；`metadata.reward_fn` 字段记录该选择。
- impacts: [Wave 3, Wave 4, training_report.metadata]
- evidence: 用户回答轮次 2 选 A；`ellectric/pipeline/trading_env.py:113-144` 含 profit_only/risk_adjusted/volume_penalty 三注册项。
- priority: P0

## D-003@v1: 单算法失败仅记录 error 跳过该算法回测

- type: boundary
- status: accepted
- source: user
- question: PPO/SAC/TD3 之一训练失败时如何处理？
- answer: 仅在 `training_report.training[<algo>].status="error"` 记录异常，跳过该算法回测，其他算法照常；不抛出，不重试。
- normalized_requirement: `train_one()` 必须用 `try/except Exception` 隔离每个算法；外层循环不重抛；回测段只对 `status=="ok"` 的算法调用 `runner.replay(agent, ...)`。
- impacts: [Wave 4, Wave 5, R-02, training_report.training]
- evidence: 用户回答轮次 3 选 A。
- priority: P0

## D-004@v1: 实现方案 = 单 CLI 脚本无新 pipeline 模块

- type: architecture
- status: accepted
- source: user
- question: 训练 runner 是否抽象为 pipeline 模块？
- answer: 选方案 A，单脚本 `ellectric/scripts/train_rl_full_dataset.py`，不新建 `pipeline/full_dataset_trainer.py`。
- normalized_requirement: 不修改 `trading_env / rl_trainer / backtester / features / shandong_loader / forecaster / price_forecaster` 的公开 API；训练循环作为 scripts 函数存在；不引入 notebook。
- impacts: [文件变更清单, 兼容策略, 非目标]
- evidence: 用户回答 Step 8 选方案 A。
- priority: P1

## D-005@v1: 训练预算 50k steps + 三基线对比

- type: boundary
- status: accepted
- source: user
- question: 训练步数与对比口径？
- answer: 每算法 50k steps；与 `BacktestRunner` 已有 persistence/mean/oracle 三基线对比；端到端 60-120 分钟可接受。
- normalized_requirement: CLI 默认 `--timesteps 50000`；回测 6 条线（3 RL + 3 baseline）；`metadata.timesteps_per_algo=50000`。
- impacts: [Wave 4, Wave 5, R-01, R-06, training_report.metadata]
- evidence: 用户回答 Step 6 轮次 2 选 B。
- priority: P1

## D-006@v1: 数据切分 + Tier1-4（启用 weather）

- type: boundary
- status: accepted
- source: user
- question: 训练/回测时段与特征层？
- answer: 训练 2024-01-01~2025-09-30，回测 2025-10-01~2026-01-14；启用 Tier1-4 含 weather。
- normalized_requirement: CLI 默认窗口固定为该切分；`--tier tier4` 默认；weather cache 缺失时静默降级到 Tier3 并记录 `weather_source`。
- impacts: [Wave 1, Wave 2, R-03, training_report.metadata]
- evidence: 用户回答 Step 6 轮次 3 选 B。
- priority: P1

## D-007@v1: 单元测试用 fake adapter，不真调 sb3 .learn()

- type: definition
- priority: P1
- status: accepted
- source: design-grill
- question: design 早期写 "100 steps smoke"；sb3 PPO 默认 `n_steps=2048`、SAC/TD3 默认 `learning_starts=100`，极小 timesteps 行为不可靠，且 CI 不应阻塞。
- answer: tests 注入 fake `BaseRLAgent` adapter（实现 train/predict/save/load/evaluate 即可），脚本逻辑与报告 schema 走 fake；真训练仅在本地或可选 Action。
- normalized_requirement: `tests/test_train_rl_full_dataset.py` 不得在测试中调真实 `RLAgentFactory.create(...).train(...)`；必须 monkeypatch `RLAgentFactory.create` 返回 fake；`--dry-run` 路径独立测试。
- impacts: [tasks-tests, R-06, R-09]
- evidence: design.md R-06/R-09；`stable_baselines3.ppo.ppo.PPO` 默认 `n_steps=2048`。

## D-008@v1: report.metadata 同时记录 train/test 两个 max_capacity

- type: consistency
- priority: P2
- status: accepted
- source: design-grill
- question: training env max_capacity 来自 train_load，BacktestRunner.replay 内部用 test_load.load_mw.max() 覆盖；二者不一致是否要 align？
- answer: 不 align — RL agent 输出归一化 [0,1] 动作，max_capacity 仅作 scale；但 report.metadata 必须同时记录 `train_max_capacity` 与 `test_max_capacity` 供审阅。
- normalized_requirement: training_report.json metadata 至少含 `train_max_capacity_mw` 与 `test_max_capacity_mw` 两个字段。
- impacts: [Wave 6, R-08, training_report.metadata]
- evidence: design.md R-08；`ellectric/pipeline/backtester.py:213` `env._max_capacity = load["load_mw"].max()` 覆盖。
