
---
schema_version: 1
doc_type: module-card
module_id: rl-trainer
---

# rl-trainer

## 定位

强化学习训练框架，提供 PPO、TD3、SAC 三种算法的统一接口。
基于 stable-baselines3，通过适配器模式包装为一致的 API。

## 契约摘要

- `BaseRLAgent(ABC)` — 抽象基类
  - `train(timesteps, callback) -> dict` — 训练
  - `predict(obs, deterministic) -> np.ndarray` — 推理
  - `save(path)`, `load(path)` — 持久化
  - `evaluate(env, episodes) -> dict` — 评估（返回 mean/std reward）
- `RLAgentFactory` — 工厂类
  - `create(algo, env, tensorboard_log, **kwargs) -> BaseRLAgent` — 创建智能体
  - `load(algo, path, env) -> BaseRLAgent` — 加载已有模型
  - `ALGORITHMS = {"ppo": PPO, "td3": TD3, "sac": SAC}`

## 关键逻辑

- sb3 模型通过 `_SB3Adapter` 适配到 `BaseRLAgent` 接口
- TensorBoard 日志自动记录 reward/loss/action distribution
- 模型保存为 sb3 原生 `.zip` 格式

## 注意事项

- 不支持算法的 algo 名 → ValueError
- predict() 前必须 train() → RuntimeError
- save() 目标路径不存在时自动创建目录

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
