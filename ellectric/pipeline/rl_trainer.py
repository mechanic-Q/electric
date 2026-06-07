"""
强化学习训练框架 — PPO/TD3/SAC 适配器与工厂
==========================================

基于 stable-baselines3 的统一强化学习训练接口。
通过 BaseRLAgent 抽象基类统一不同 RL 算法的训练、预测、保存和评估。

Reinforcement learning training framework with PPO/TD3/SAC adapters.
Provides a unified interface via BaseRLAgent ABC for training, prediction,
model persistence, and evaluation across different RL algorithms.

使用方式:
    >>> from ellectric.pipeline.rl_trainer import RLAgentFactory
    >>> agent = RLAgentFactory.create("ppo", env)
    >>> result = agent.train(total_timesteps=10000)
    >>> action = agent.predict(observation)
    >>> agent.save("models/ppo_agent.zip")
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Union

import gymnasium as gym
import numpy as np
from stable_baselines3 import PPO, SAC, TD3
from stable_baselines3.common.base_class import BaseAlgorithm

logger = logging.getLogger(__name__)


class BaseRLAgent(ABC):
    """
    强化学习智能体抽象基类。

    所有 RL 算法（PPO、TD3、SAC）通过此接口统一暴露，
    允许用户在不感知底层实现差异的情况下使用。

    Abstract base class for RL agents.
    Unifies PPO, TD3, and SAC behind a single interface.
    """

    @abstractmethod
    def train(
        self,
        total_timesteps: int,
        callback: Optional[Callable] = None,
    ) -> dict:
        """
        训练智能体。

        Args:
            total_timesteps: 总训练步数
            callback: 训练回调函数

        Returns:
            包含训练信息的字典（total_timesteps, final_reward 等）
        """
        ...

    @abstractmethod
    def predict(
        self,
        observation: Union[dict, np.ndarray],
        deterministic: bool = True,
    ) -> np.ndarray:
        """
        根据观测输出动作。

        Args:
            observation: 环境观测
            deterministic: 是否确定性预测

        Returns:
            动作向量
        """
        ...

    @abstractmethod
    def save(self, path: str) -> None:
        """保存模型到文件。"""
        ...

    @abstractmethod
    def load(self, path: str, env: Optional[gym.Env] = None) -> None:
        """从文件加载模型。"""
        ...

    @abstractmethod
    def evaluate(
        self,
        env: gym.Env,
        n_episodes: int = 100,
    ) -> dict:
        """
        在环境中评估智能体性能。

        Args:
            env: 评估环境
            n_episodes: 评估回合数

        Returns:
            包含评估指标（mean_reward, std_reward, episode_rewards）的字典
        """
        ...


class _SB3Adapter(BaseRLAgent):
    """
    stable-baselines3 模型适配器 — 内部类。

    将 sb3 的 PPO/TD3/SAC 模型包装在 BaseRLAgent 接口之后。
    不应该是用户直接实例化；通过 RLAgentFactory.create() 创建。

    Internal adapter wrapping sb3 PPO/TD3/SAC behind BaseRLAgent interface.
    Not for direct instantiation; use RLAgentFactory.create().
    """

    def __init__(
        self,
        algo: str,
        model: BaseAlgorithm,
        env: Optional[gym.Env] = None,
    ):
        self._algo = algo
        self._model = model
        self._env = env
        self._trained = False

    def train(
        self,
        total_timesteps: int,
        callback: Optional[Callable] = None,
    ) -> dict:
        """
        训练智能体。

        Args:
            total_timesteps: 总训练步数
            callback: 训练回调函数

        Returns:
            dict: total_timesteps, final_reward
        """
        logger.info(
            "开始训练 %s，total_timesteps=%d", self._algo.upper(), total_timesteps
        )
        self._model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            reset_num_timesteps=False,
        )
        self._trained = True

        final_reward = self._compute_final_reward()
        result = {
            "total_timesteps": total_timesteps,
            "final_reward": final_reward,
            "algo": self._algo,
        }
        logger.info(
            "%s 训练完成，final_reward=%.4f", self._algo.upper(), final_reward
        )
        return result

    def predict(
        self,
        observation: Union[dict, np.ndarray],
        deterministic: bool = True,
    ) -> np.ndarray:
        """
        根据观测输出动作。

        Args:
            observation: 环境观测
            deterministic: 是否确定性预测

        Returns:
            动作向量

        Raises:
            RuntimeError: 模型未训练
        """
        if not self._trained:
            raise RuntimeError("模型未训练，请先调用 train()")
        action, _ = self._model.predict(observation, deterministic=deterministic)
        return action

    def save(self, path: str) -> None:
        """保存模型到文件。自动创建父目录。"""
        save_dir = os.path.dirname(path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        self._model.save(path)
        logger.info("模型已保存到 %s", path)

    def load(self, path: str, env: Optional[gym.Env] = None) -> None:
        """
        从文件加载模型。

        Args:
            path: 模型文件路径
            env: 环境实例（可选）

        Raises:
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"模型文件不存在: {path}")

        algo_cls = RLAgentFactory.ALGORITHMS[self._algo]
        self._model = algo_cls.load(path, env=env or self._env)
        self._trained = True
        logger.info("模型已从 %s 加载", path)

    def evaluate(
        self,
        env: gym.Env,
        n_episodes: int = 100,
    ) -> dict:
        """
        在环境中评估智能体性能。

        运行 n_episodes 个完整回合，收集每回合奖励。

        Args:
            env: 评估环境
            n_episodes: 评估回合数

        Returns:
            dict: mean_reward, std_reward, episode_rewards

        Raises:
            RuntimeError: 模型未训练
        """
        if not self._trained:
            raise RuntimeError("模型未训练，请先调用 train()")

        episode_rewards: list[float] = []

        for ep in range(n_episodes):
            obs, _ = env.reset()
            done = False
            total_reward = 0.0

            while not done:
                action, _ = self._model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, _ = env.step(action)
                total_reward += reward
                done = terminated or truncated

            episode_rewards.append(total_reward)

            if (ep + 1) % 20 == 0:
                logger.info("评估进度 %d/%d, 平均奖励 %.4f", ep + 1, n_episodes, np.mean(episode_rewards[-20:]))

        rewards_arr = np.array(episode_rewards, dtype=np.float64)
        result = {
            "mean_reward": float(rewards_arr.mean()),
            "std_reward": float(rewards_arr.std()),
            "episode_rewards": episode_rewards,
        }
        logger.info(
            "评估完成: mean_reward=%.4f, std_reward=%.4f (n=%d)",
            result["mean_reward"],
            result["std_reward"],
            n_episodes,
        )
        return result

    def _compute_final_reward(self) -> float:
        """训练完成后，用当前策略在环境中跑一个回合估算最终奖励。"""
        if self._env is None:
            return 0.0
        env_snapshot = (
            getattr(self._env, '_current_step', None),
            getattr(self._env, '_cash', None),
        )
        try:
            obs, info = self._env.reset()
            done = False
            total = 0.0
            while not done:
                action, _ = self._model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, _ = self._env.step(action)
                total += reward
                done = terminated or truncated
            return float(total)
        except Exception as e:
            logger.warning("计算 final_reward 失败: %s", e)
            return 0.0
        finally:
            self._env.reset()


class RLAgentFactory:
    """
    RL 智能体工厂 — 统一创建和加载各种算法的智能体。

    使用方式:
        >>> agent = RLAgentFactory.create("ppo", env)
        >>> agent = RLAgentFactory.load("sac", "models/sac_agent.zip", env)
    """

    ALGORITHMS: dict[str, type] = {
        "ppo": PPO,
        "td3": TD3,
        "sac": SAC,
    }

    @classmethod
    def create(
        cls,
        algo: str,
        env: gym.Env,
        tensorboard_log: str = "./tb_logs",
        policy_kwargs: Optional[dict] = None,
        verbose: int = 0,
        **kwargs: Any,
    ) -> BaseRLAgent:
        """
        创建并返回指定算法的 BaseRLAgent 实例。

        Args:
            algo: 算法名称 ("ppo", "td3", "sac")
            env: Gymnasium 环境实例
            tensorboard_log: TensorBoard 日志目录
            policy_kwargs: 策略网络参数字典
            verbose: 日志级别 (0=静默, 1=信息)

        Returns:
            BaseRLAgent 实例

        Raises:
            TypeError: env 未提供
            ValueError: 不支持的算法
        """
        if env is None:
            raise TypeError("env is required")

        algo = algo.lower()
        if algo not in cls.ALGORITHMS:
            raise ValueError(
                f"Unsupported algo: {algo}. Supported: {list(cls.ALGORITHMS.keys())}"
            )

        algo_cls = cls.ALGORITHMS[algo]
        from gymnasium.spaces import Dict as DictSpace
        policy = "MultiInputPolicy" if isinstance(env.observation_space, DictSpace) else "MlpPolicy"
        model_kwargs: dict[str, Any] = {
            "policy": policy,
            "env": env,
            "tensorboard_log": tensorboard_log,
            "verbose": verbose,
        }
        if policy_kwargs is not None:
            model_kwargs["policy_kwargs"] = policy_kwargs
        model_kwargs.update(kwargs)

        model = algo_cls(**model_kwargs)
        logger.info(
            "已创建 %s 智能体 (tensorboard_log=%s)", algo.upper(), tensorboard_log
        )

        return _SB3Adapter(algo=algo, model=model, env=env)

    @classmethod
    def load(
        cls,
        algo: str,
        path: str,
        env: Optional[gym.Env] = None,
    ) -> BaseRLAgent:
        """
        从文件加载已训练的模型。

        Args:
            algo: 算法名称 ("ppo", "td3", "sac")
            path: 模型文件路径 (.zip)
            env: 环境实例（可选）

        Returns:
            BaseRLAgent 实例

        Raises:
            ValueError: 不支持的算法
            FileNotFoundError: 文件不存在
        """
        algo = algo.lower()
        if algo not in cls.ALGORITHMS:
            raise ValueError(
                f"Unsupported algo: {algo}. Supported: {list(cls.ALGORITHMS.keys())}"
            )

        if not os.path.exists(path):
            raise FileNotFoundError(f"模型文件不存在: {path}")

        algo_cls = cls.ALGORITHMS[algo]
        model = algo_cls.load(path, env=env)
        logger.info("已加载 %s 模型: %s", algo.upper(), path)

        return _SB3Adapter(algo=algo, model=model, env=env)
