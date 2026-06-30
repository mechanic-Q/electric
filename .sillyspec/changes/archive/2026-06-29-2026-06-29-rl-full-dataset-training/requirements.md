---
author: lmr
created_at: 2026-06-29 01:44:36
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 学习者 | 通过单 CLI 命令复现完整 96 维 RL 训练 + 回测，理解 PPO/SAC/TD3 与三基线对比 |
| 开发者 | 维护 train_rl_full_dataset 脚本与测试，未来在此基础上做超参/算法/特征扩展 |
| 未来 Agent | 读取本变更产物（报告 JSON + checkpoint）作为基线，继续后续 RL/特征改进 |

## 功能需求

### FR-01: ShandongDataLoader 全量加载 + rt_price→price_da 价格代理

覆盖决策：D-001@v1, D-006@v1

Given 仓库存在 `ellectric/data/shandong/山东_2024-2026_15min.csv`
When 调用 `build_datasets(train_start, train_end, test_start, test_end)`
Then 返回 (train_load, train_price, test_load, test_price) 四个 DataFrame；每个 price DataFrame 含 `timestamp` 与 `price_da` 列；`price_da` 值来自原始 `rt_price`；窗口默认 train=[2024-01-01,2025-09-30]、test=[2025-10-01,2026-01-14]

Given `rt_price` 含 0.1% null
When `build_datasets` 处理
Then 输出 `price_da` 不含 null；处理方法记录到日志

### FR-02: Tier1-4 特征工程 + weather cache 降级

覆盖决策：D-006@v1

Given 默认 weather cache 存在
When 调用 `build_features(load_df, tier="tier4", weather_cache_path=None)`
Then 返回 (feature_df, feature_cols, weather_source)；`weather_source ∈ {"cache","fetch","degraded"}`；feature_cols 包含 tier1-3 标准列 + 至少一个 weather 列

Given 默认 weather cache 缺失且 `fetch_if_missing=False`
When 调用 `build_features(load_df, tier="tier4", ...)`
Then weather_source 返回 `"degraded"`；feature_cols 退化为 tier1-3；不抛异常；脚本继续

Given `tier="tier3"`
When 调用 `build_features`
Then weather_source 返回 `"skipped"`；feature_cols 仅含 tier1-3；不触网

### FR-03: 三算法 50k steps 训练 + checkpoint + profit_only 奖励

覆盖决策：D-002@v1, D-003@v1, D-005@v1

Given 训练 env 已装配，algo ∈ {"ppo","sac","td3"}
When 调用 `train_one(algo, env, timesteps=50000, seed=42, log_dir, ckpt_path)`
Then 调用 `RLAgentFactory.create(algo, env, tensorboard_log=log_dir)` 与 `agent.train(total_timesteps=50000)`；env 的 `reward_fn` 为 `profit_only`；训练成功后 `agent.save(ckpt_path)`；返回 dict 含 `status="ok", final_reward, duration_s, checkpoint_path, tb_log_path`

Given `agent.train()` 抛出任意异常
When `train_one` 捕获
Then 返回 dict 含 `status="error", error=str(e), checkpoint_path=None`；不重抛；外层循环对其它算法继续

### FR-04: 6 条线统一回测 + metrics + Plotly 累计 P&L

覆盖决策：D-005@v1

Given `train_results` 含 ppo/sac/td3 训练结果（部分可能 status=error），test_load/test_price 已就绪
When 调用 `run_backtest(train_results, test_load, test_price, test_start, test_end, report_dir)`
Then 对每个 `s in SUPPORTED_STRATEGIES`（persistence/mean/oracle）调用 `BacktestRunner.replay(s, ...)`；对每个 `train_results[algo].status=="ok"` 的算法加载 checkpoint 并 `runner.replay(agent, ..., strategy_name=f"rl_{algo}")`；`runner.compare(results)` 返回 metrics DataFrame；`runner.plot_comparison(...)` 保存为 `report_dir/cumulative_pnl.html`；返回 dict 含 `metrics: list[dict]` 与 `cumulative_pnl_html_path: str`

### FR-05: JSON + Markdown 报告 4 顶层字段

覆盖决策：D-001@v1, D-002@v1, D-007@v1, D-008@v1

Given 训练与回测均完成
When 调用 `write_reports(report_dict, report_dir)`
Then 在 `report_dir` 下生成 `training_report.json` 与 `training_report.md`；JSON 含 4 顶层字段 `metadata / training / backtest / interpretation`；metadata 含 `generated_at, git_sha, time_config, seed, algos, timesteps_per_algo, train_range, test_range, tier, weather_source, reward_fn, price_proxy, train_max_capacity_mw, test_max_capacity_mw`；training 含每个 algo 的 `status, final_reward, duration_s, checkpoint_path, tb_log_path, error`；backtest 含 `metrics, cumulative_pnl_html_path`；interpretation 含 `hard_threshold_applied=false, summary`

Given 写入过程中遇到 IO 异常
When `write_reports` 内
Then 使用 `tmp + rename` 原子写入；失败时抛异常，main() 返回退出码 2

### FR-06: CLI 入口 + `--dry-run` 装配 smoke

覆盖决策：D-004@v1, D-007@v1

Given 用户执行 `python -m ellectric.scripts.train_rl_full_dataset --dry-run`
When 脚本运行
Then 执行 Wave 1-3（数据/特征/env 装配）；不调任何 `agent.train()` 与 `runner.replay()`；写入 `training_report.json` 的 metadata + interpretation 段（其它字段为空/null）；退出码 0

Given 用户执行 `python -m ellectric.scripts.train_rl_full_dataset --algos ppo`
When 脚本运行
Then 仅训练 PPO；其它算法在 training 字段中存在但 `status="skipped"`

Given 默认窗口 + tier4 + weather cache 缺失
When 脚本运行完成
Then `report.metadata.weather_source="degraded"`；training/backtest 仍按 tier1-3 继续

### FR-07: 测试不真调 sb3 .learn()

覆盖决策：D-007@v1

Given 测试套件 `tests/test_train_rl_full_dataset.py`
When 运行 `pytest tests/test_train_rl_full_dataset.py`
Then 所有测试通过；测试通过 monkeypatch 把 `RLAgentFactory.create` 替换为 fake adapter；测试中不出现真实 `PPO/SAC/TD3` 实例化或 `.learn()` 调用

测试用例至少覆盖：
- `build_datasets` 价格代理：检查 `price_da` 列存在且等于原始 `rt_price`
- `build_features` Tier4 cache 命中 / cache 缺失降级
- `make_env` 接受 train/test load+price，返回 Dict obs + Box(96) action env
- `train_one` 异常路径：fake adapter 抛 RuntimeError → 返回 `status="error"`
- `write_reports` 输出 JSON schema 验证（4 顶层字段 + 必需子字段）
- `--dry-run` argparse 路径退出 0 且无 train 调用

### FR-08: 文档同步与 ROADMAP/README 勾选

覆盖决策：D-004@v1

Given 本变更完成
When 阅读 `.planning/ROADMAP.md` 与 `ellectric/README.md` Phase 4 持续改进段
Then 第 1 项「完整 96 维 RL training on full dataset」标记为已完成首轮并指向 `ellectric/reports/rl_full_dataset/training_report.md`

Given 阅读 `docs/Ellectric/modules/rl-trainer.md`
When 完成本变更
Then 包含新章节「full-dataset 训练入口」介绍 CLI、报告路径与 `--dry-run` 用法

## 非功能需求

- **兼容性**：旧 trading_env/rl_trainer/backtester/features/shandong_loader/forecaster/price_forecaster 公开 API 全部保留；旧 notebook 行为不变。
- **可回退**：单算法失败不阻断；weather 不可用自动降级 Tier1-3；删除 `ellectric/scripts/train_rl_full_dataset.py` 与对应测试即可完全回退。
- **可测试**：测试不真调 sb3；不依赖网络；不依赖真实 weather cache（用 fixture）。
- **可复现**：默认 seed=42；CLI 参数全部默认值确定；报告含 `git_sha` 字段。
- **资源约束**：默认 50k×3 算法预计 60-120 分钟，需在普通笔记本可跑；CI 上仅跑 `--dry-run` + 单元测试。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 价格代理 | FR-01, FR-05 | price_da = rt_price 重命名；报告 metadata 记录 |
| D-002@v1 profit_only | FR-03, FR-05 | env reward_fn 固定 profit_only |
| D-003@v1 单算法失败 | FR-03, FR-04 | 仅记录 error，跳过该算法回测 |
| D-004@v1 单脚本方案 | FR-08, 全局 | 不抽新模块，CLI 即唯一入口 |
| D-005@v1 50k+三基线 | FR-03, FR-04 | timesteps_per_algo=50000；三基线回测 |
| D-006@v1 切分+Tier1-4 | FR-01, FR-02 | 默认窗口与 tier4 启用 |
| D-007@v1 fake adapter | FR-07, FR-06 | 测试不真调 sb3；--dry-run 不调 train |
| D-008@v1 双 max_capacity | FR-05 | metadata 同时记录 train/test |
