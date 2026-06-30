---
id: task-07
title: 实现 `train_one` + checkpoint 保存 + 单算法异常隔离
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-02, task-06]
blocks: [task-09, task-10]
requirement_ids: [FR-03]
decision_ids: [D-003@v1, D-005@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  对单个算法执行 RLAgentFactory.create + agent.train + agent.save，try/except 整段以保证单算法失败不阻断其它算法。
implementation:
  - 函数签名 `train_one(algo, env, *, timesteps, seed, log_dir, ckpt_path) -> dict`
  - 创建 log_dir 父目录 + ckpt_path 父目录
  - try 内：`agent = RLAgentFactory.create(algo, env, tensorboard_log=log_dir, seed=seed)`，记 t0=time.monotonic，`agent.train(total_timesteps=timesteps)`，`agent.save(ckpt_path)`，记 duration，组 dict status="ok"
  - except Exception as e：捕获返回 {status:"error", error:str(e), checkpoint_path:None, tb_log_path:log_dir, final_reward:None, duration_s:None}
  - 成功 dict：{status:"ok", algo, final_reward:float(result["final_reward"]), duration_s, checkpoint_path:ckpt_path, tb_log_path:log_dir, error:None}
acceptance:
  - test_train_one_success_with_fake：fake_agent_factory 注入下返回 status=="ok" + checkpoint_path 写入
  - test_train_one_failure_swallowed：fake_agent_factory 注入抛 RuntimeError 时返回 status=="error"，外层未重抛
  - test_train_one_creates_dirs：log_dir 和 ckpt_path 父目录被 mkdir
verify:
  - pytest tests/test_train_rl_full_dataset.py -q -k train_one
constraints:
  - 不重抛任何 sb3 异常
  - 单算法异常必须 logger.error 但脚本不退出
  - 不直接 import stable_baselines3（通过 RLAgentFactory 间接使用）
