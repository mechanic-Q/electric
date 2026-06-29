---
author: lmr
created_at: 2026-06-29 01:44:36
---

# Proposal

## 动机

Phase 4 收尾 synthesis 把「完整 96 维 RL training on full dataset」列为持续改进项第 1。仓库内 `trading_env.py`（96 维 Box 动作 + Dict 观测）、`rl_trainer.py`（PPO/SAC/TD3 工厂）、`backtester.py`（multi-strategy 回测 + 三基线）、`features.py`（Tier1-4 含 weather）、`shandong_loader.py`（745 天 15min 全量数据）全部到位，但没有一次完整跑过。本变更补齐这次完整跑过，并把过程和结果以 JSON+Markdown 报告形式落盘，沿用 `weather-tier4-validation` 已建立的报告范式。

## 关键问题

1. **缺端到端跑过的证据**：notebook 09-10 是片段演示，demo_ppo.zip 只有 5k steps，没有 PPO/SAC/TD3 在山东全量数据上的统一对比记录。
2. **缺可复现 CLI 入口**：现状下要复现需要 notebook 顺手跑，无法 `python -m ... --algos ppo,sac,td3` 一键复现。
3. **缺与基线统一对比的归档**：BacktestRunner 有 oracle/persistence/mean 三基线，但没有归档式报告把 RL 与基线放在同一指标表里。

## 变更范围

- 新增 `ellectric/scripts/train_rl_full_dataset.py` 单 CLI 入口（数据/特征/三算法训练/三算法+三基线回测/JSON+MD 报告/Plotly 累计 P&L html）。
- 新增对应测试（用 fake adapter，不真调 sb3 `.learn()`）。
- 更新 README/ROADMAP Phase 4 持续改进项打勾、`docs/Ellectric/modules/rl-trainer.md` 补 full-dataset 入口章节。
- 更新 `.gitignore` 忽略产物（模型、tb_logs、报告 html）。

## 不在范围内（显式清单）

- 不修改 `trading_env.py / rl_trainer.py / backtester.py / features.py / shandong_loader.py / forecaster.py / price_forecaster.py` 的公开 API。
- 不抽象新 pipeline 模块（如 `full_dataset_trainer.py`）。
- 不新增 notebook。
- 不做超参数搜索、不追求策略质量阈值、不设硬性精度门限。
- 不引入准实时调度、cron、daemon、queue。
- 不接真实交易、不接付费数据源、不做多省/多节点/多市场。
- 不修复 `forecaster.py` 已有的 `TimeSeriesSplit gap=24` 小时级假设（R-07，留作后续单独变更）。
- 不更新 LLM Wiki（archive 阶段统一写 closeout）。

## 成功标准（可验证）

1. 仓库新增 `ellectric/scripts/train_rl_full_dataset.py`，`python -m ellectric.scripts.train_rl_full_dataset --dry-run` 退出码 0 且不调任何 sb3 `.learn()`。
2. 默认 CLI 参数运行完成后产出 `ellectric/reports/rl_full_dataset/training_report.json`，含 4 顶层字段 metadata/training/backtest/interpretation 与全部必需子字段（见 design §6）。
3. `training_report.md` 与 JSON 字段一致，含 metadata 表、training per-algo 表、backtest metrics 表、interpretation 段。
4. `report.metadata.price_proxy == "rt_price->price_da"` 且 `report.metadata.reward_fn == "profit_only"`。
5. `report.metadata` 同时包含 `train_max_capacity_mw` 与 `test_max_capacity_mw`（D-008@v1）。
6. 单算法异常时 `report.training[<algo>].status == "error"` 且 error 字段含异常信息，其它算法继续（D-003@v1）。
7. `tests/test_train_rl_full_dataset.py` 全部通过；测试中无真实 `sb3.PPO/SAC/TD3.learn()` 调用（通过 monkeypatch fake adapter）。
8. 不运行新脚本时，旧 `notebooks/09_rl_trading_agent.ipynb` 与既有 demo 行为不变。
9. README / ROADMAP / rl-trainer.md 同步更新，没有出现"未跑过完整 96 维 RL"的旧表述。
