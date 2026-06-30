---
id: task-02
title: 新增 `tests/test_train_rl_full_dataset.py` 骨架 + fake `BaseRLAgent` adapter 夹具
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: []
blocks: [task-07, task-08, task-09, task-13]
requirement_ids: [FR-07]
decision_ids: [D-007@v1]
allowed_paths:
  - tests/test_train_rl_full_dataset.py
  - tests/conftest.py
goal: >
  建立测试文件 + fake BaseRLAgent adapter pytest fixture，保证后续 task 用 monkeypatch 注入 fake，不在 CI 触发真实 sb3 .learn()。
implementation:
  - 新建 tests/test_train_rl_full_dataset.py，frontmatter docstring 注明 D-007@v1
  - 定义 FakeRLAgent 类实现 BaseRLAgent 全部抽象方法 (train/predict/save/load/evaluate)：train 立即返回 dict，predict 返回 zeros 96 维 action，save 写入空文件，load no-op，evaluate 返回 {mean_reward:0.0,std_reward:0.0,episode_rewards:[]}
  - pytest fixture `fake_agent_factory`：monkeypatch `ellectric.pipeline.rl_trainer.RLAgentFactory.create` 与 `RLAgentFactory.load` 返回 FakeRLAgent
  - pytest fixture `tiny_shandong_df`：构造 200 行 15min 假数据 (timestamp/load_mw/rt_price/da_price/wind_actual_mw/solar_actual_mw/is_holiday/is_weekend)
  - 一个 placeholder 测试 `test_module_importable`：from ellectric.scripts import train_rl_full_dataset
acceptance:
  - pytest tests/test_train_rl_full_dataset.py -q 通过且 ≥1 测试运行
  - FakeRLAgent 通过 `isinstance(fake, BaseRLAgent)` 检查
  - 测试运行过程中没有出现 sb3.PPO/SAC/TD3 实例化日志
verify:
  - pytest tests/test_train_rl_full_dataset.py -q
constraints:
  - 不依赖网络、不依赖真实 weather cache
  - 不导入 stable_baselines3 (除 BaseRLAgent 类继承)
  - fixture 数据量保持小（< 256 行）避免 CI 慢
