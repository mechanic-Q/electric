# RL Evaluation Pipeline Fix + Data Resync

## Problem Statement

RL 智能体 reward redesign（PR #42）合并后，展示服务器的网页仍然显示**旧的破损数据**：
- 策略排名面板显示 oracle=-4.25, rl_ppo=-197M, win_rate=0.151（全是修复前的值）
- Copilot 引用的训练报告是 2026-07-01 的旧版本（50k steps, 旧 reward 函数）

根因有两个 bug：

1. **Evaluation pipeline bug**：`RLAgentFactory.load()` 创建 `_SB3Adapter` 时 `_trained = False`，导致 `evaluate_rl_agents()` 调用 `predict()` 抛 `RuntimeError("模型未训练")`。RL 三行在 `evaluation_metrics.csv` 中标记为 `error`（空字段）。`run_backtest()` 有手动补丁 (`agent._trained = True`)，但 `evaluate_rl_agents()` 没有。

2. **.gitignore 过度排除**：`ellectric/reports/rl_full_dataset/*.json` 和 `*.md` 被排除，导致 T3 训练在 worktree 中生成的报告文件在 worktree 清理时永久丢失。只有 git 跟踪的 `evaluation_metrics.csv`（部分更新）通过 PR merge 存活。

## Solution

1. 在 `RLAgentFactory.load()` 根源修复 `_trained` flag，让所有调用点自动受益
2. 修改 `.gitignore`，只排除大文件（`*.log`, `*.html`），允许小报告文件（`*.json`, `*.md`）提交
3. 在主 repo 重新运行全量训练（200k × 3），生成正确的报告 + 模型
4. 重新烘焙 `rolling-demo.json` 静态文件
5. 提交报告 + 静态 JSON 到 git，推送后在服务器拉取并重启

## User Stories

1. 作为网站访问者，我希望策略排名面板显示正确的 RL 交易结果（正收益），这样我能看到 AI 智能体的真实表现
2. 作为网站访问者，我希望 Copilot 能引用最新的训练报告（200k steps, 正 reward），这样它的解释是基于正确数据的
3. 作为开发者，我希望 `RLAgentFactory.load()` 返回的 adapter 可以直接调用 `predict()` 而不抛异常，这样我不需要在每个调用点手动设 `_trained = True`
4. 作为开发者，我希望 `evaluate_rl_agents()` 产出的 CSV 中 RL 行有完整指标（total_pnl, sharpe, win_rate, max_drawdown 等），这样策略排名面板能显示所有字段
5. 作为开发者，我希望训练报告文件（training_report.json/md, evaluation_report.json/md）能被 git 跟踪，这样 worktree 清理后不会丢失
6. 作为开发者，我希望 `.gitignore` 只排除真正大的文件（25MB 日志、1.9MB HTML 图表），不排除小报告文件（<10KB JSON/MD），这样报告可以版本控制
7. 作为开发者，我希望 `rolling-demo.json` 在训练后自动反映最新的策略指标，这样不需要手动同步
8. 作为开发者，我希望服务器上的 `rolling-demo.json` 和本地一致，这样网页展示的数据是最新成果
9. 作为开发者，我希望删除 `train_rl_full_dataset.py` 中的手动 `_trained` 补丁，因为根因修复后不再需要
10. 作为开发者，我希望快速验证（PPO 20k）能确认 evaluation bug 已修复，这样不用等 3-4 小时全量训练才发现问题
11. 作为开发者，我希望全量训练后所有 RL 策略在 CSV 中 `status=ok`，这样网页策略面板有完整数据
12. 作为开发者，我希望服务器 systemd 服务在代码更新后正确重启，这样网页不会宕机

## Implementation Decisions

### Bug #1 修复：`RLAgentFactory.load()` 根因修复

- 模块：RL trainer factory
- 接口变更：`RLAgentFactory.load()` 返回的 adapter 的 `_trained` 属性在返回前设为 `True`
- 原因：`load()` 已经通过 SB3 原生 `algo_cls.load()` 加载了模型权重，adapter 的 `_trained` 应反映这一事实
- 同时删除 `train_rl_full_dataset.py` 中 `run_backtest()` 的手动补丁（`if hasattr(agent, "_trained"): agent._trained = True`），因为根因修复后不再需要
- `handlers.py:359` 的 `run_backtest()` API handler 也会自动受益（当前没有补丁，存在潜在 bug）

### Bug #2 修复：`.gitignore` 精确化

- 只排除 `*.log`（25MB 训练日志）和 `*.html`（1.9MB 图表）
- 允许 `*.json`（evaluation_report.json = 4.8KB, training_report.json = 7.9KB）和 `*.md`（<2KB）提交
- 保留 `!ellectric/reports/rl_full_dataset/.gitkeep` 规则
- models/ 目录仍然排除（大模型文件 1.5-23MB）

### 训练 + 报告生成

- 在主 repo（非 worktree）运行 `python -m ellectric.scripts.train_rl_full_dataset`
- 200k steps × PPO/SAC/TD3，预计 3-4 小时
- 训练脚本自动生成：training_report.json/md, evaluation_report.json/md, evaluation_metrics.csv, cumulative_pnl.html, models/*.zip
- 修复 Bug #1 后，evaluation_metrics.csv 中 RL 行应有完整指标（status=ok, total_pnl > 0）

### rolling-demo.json 重新烘焙

- 运行 `python -m ellectric.scripts.prebake_demo`
- 脚本读取 `evaluation_metrics.csv` 生成策略排名面板数据
- 输出到 `ellectric/web/public/rolling-demo.json`
- 前端构建后复制到 `ellectric/api/static/rolling-demo.json`

### 服务器同步

- 服务器 `/opt/ellectric` 现在是 git repo（从 GitHub clone）
- `git pull origin master` 拉取最新代码 + 报告 + 静态 JSON
- 服务器无需 npm build（Node.js 12 太旧），直接使用本地构建的 static/ 目录
- `systemctl restart ellectric` 重启服务

## Testing Decisions

### 测试理念
- 只测外部行为，不测实现细节
- Bug #1 的外部行为：`RLAgentFactory.load()` 返回的 adapter 调用 `predict()` 不抛异常
- 集成行为：训练后 CSV 中 RL 行有完整指标

### Seam 1（单元测试，新增）
- 文件：`tests/test_rl_trainer.py`（如果存在）或 `tests/test_trading_env_reward.py`（已存在）
- 测试：`test_factory_load_sets_trained_flag` - 加载已有模型，调用 predict()，验证不抛 RuntimeError
- 使用 `models/rl_full_dataset/ppo.zip`（已存在）作为 fixture
- Prior art：`tests/test_train_rl_full_dataset.py` 中的 `test_make_env_action_space` 模式

### Seam 2（集成测试，已有）
- 文件：`tests/test_train_rl_full_dataset.py`
- 已有 `test_dry_run` 验证装配
- 新增验证：快速训练后检查 CSV 中 RL 行 status=ok（可选，因为需要 20k steps 训练）

### 验证标准（手动）
- Bug #1 修复后：`python -c "from ellectric.pipeline.rl_trainer import RLAgentFactory; a=RLAgentFactory.load('ppo','models/rl_full_dataset/ppo.zip'); print(a._trained)"` 输出 `True`
- 快速验证：PPO 20k 后 CSV 中 `rl_ppo` 行有完整字段（total_pnl, sharpe, win_rate 等）
- 全量训练后：所有 6 行（3 baseline + 3 RL）status=ok，RL P&L > 0
- 服务器验证：`curl http://8.210.117.245:8000/rolling-demo.json` 中 strategy.ranking 的 oracle pnl > 0

## Out of Scope

- Recommend 工具的 load vs price 问题（已确认无 bug，当前正确使用 price 预测）
- 其他预测器（XGBoost, LEAR）的 `_trained` flag（不存在此模式，只有 RL agent 有）
- 服务器 Node.js 升级（Node 12 -> 16+，后续单独处理）
- 服务器 Docker 化部署
- RL 模型文件提交到 git（仍然 gitignored，太大）
- 训练日志 `*.log` 提交到 git（仍然 gitignored，25MB 太大）
- cumulative_pnl.html 提交到 git（仍然 gitignored，1.9MB 太大）
- 新的 reward 函数设计（已在 PR #42 完成）
- 新的 action space 设计（已在 PR #42 完成）

## Further Notes

- 建议先修 Bug #1 + Bug #2，然后跑 PPO 20k 快速验证（15 min），确认 CSV 中 RL 行 status=ok 后再跑全量训练（3-4 hr）
- 服务器 `/opt/ellectric` 已是 git repo，后续同步只需 `git pull && systemctl restart`
- 服务器没有 npm（Node 12 太旧），前端静态文件需在本地构建后通过 git 提交 `ellectric/api/static/` 目录
- `rolling-demo.json` 同时存在于 `ellectric/web/public/`（源）和 `ellectric/api/static/`（构建产物），两者都需要更新
- 本次修复完成后，`training_report.json/md` 和 `evaluation_report.json/md` 将首次被 git 跟踪
