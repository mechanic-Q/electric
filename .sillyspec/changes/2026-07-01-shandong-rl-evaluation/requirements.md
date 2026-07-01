---
author: lmr
created_at: 2026-07-01 23:37:15
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 开发者 | 运行训练/评估脚本，查看报告，判断 RL 策略相对基线是否有改进。 |
| 学习者 | 通过报告理解 PPO/SAC/TD3、persistence、mean、oracle 的公平对比。 |
| 维护者 | 维护评估指标、报告 schema 和脚本兼容性。 |

## 功能需求

### FR-01: 评估协议集中化
覆盖决策：D-001@v1, D-002@v1

Given 开发者需要评估山东 RL 策略
When 创建评估配置
Then 系统应通过 `EvaluationProtocol` 集中保存 train/test 窗口、seed、算法列表、基线列表、checkpoint/report 路径、price proxy 和 feature tier。

### FR-02: baseline 统一评估
覆盖决策：D-002@v1, D-003@v1

Given 已有 `baseline_persistence`、`baseline_mean`、`oracle`
When 运行 baseline 评估
Then 每个 baseline 都应通过 `BacktestRunner.replay()` 产生 trades DataFrame。

### FR-03: RL checkpoint 统一评估
覆盖决策：D-002@v1, D-003@v1

Given PPO/SAC/TD3 checkpoint 路径存在
When 运行 RL 评估
Then 系统应通过 `RLAgentFactory.load()` 加载模型，并通过 `BacktestRunner.replay()` 产生 trades DataFrame。

### FR-04: 策略失败隔离
覆盖决策：D-001@v1, D-002@v1

Given 某个 baseline 或 RL 策略评估失败
When 继续评估其他策略
Then 失败策略应记录 `status=error` 与 `error` 信息，其他策略继续运行，最终报告仍生成。

### FR-05: 英文指标表
覆盖决策：D-001@v1, D-002@v1

Given 策略评估结果集合
When 计算指标
Then 输出应包含 `strategy`、`total_pnl`、`sharpe`、`win_rate`、`max_drawdown`、`profit_factor`、`volatility`、`oracle_gap`、`baseline_delta`、`rank`、`status`。

### FR-06: 评估报告输出
覆盖决策：D-001@v1, D-002@v1

Given 已完成评估和指标计算
When 写入报告
Then 系统应生成 `evaluation_report.json`、`evaluation_metrics.csv`、`evaluation_report.md`，并在可用时生成/引用 `cumulative_pnl.html`。

### FR-07: full dataset 脚本兼容集成
覆盖决策：D-002@v1, D-003@v1

Given 现有 `python -m ellectric.scripts.train_rl_full_dataset --dry-run`
When 集成新评估模块后运行
Then 原 CLI 参数和 dry-run 行为应保持可用，且不触发真实 long training。

### FR-08: 独立评估入口（可选）
覆盖决策：D-002@v1

Given 已有 checkpoint 和测试数据窗口
When 运行 `python -m ellectric.scripts.evaluate_rl_strategies`
Then 系统应能跳过训练，仅对已有策略集合生成评估报告。

### FR-09: smoke tests
覆盖决策：D-001@v1, D-003@v1

Given 测试环境不应执行长训练
When 运行新增测试
Then 测试应通过 fake/dummy agent 和小 DataFrame 覆盖指标、报告、失败隔离和脚本集成，不调用真实 stable-baselines3 `.learn()`。

## 非功能需求

- 兼容性：不删除或改变 `BacktestRunner.compare()` 当前中文列名输出。
- 可回退：新评估入口失败不影响旧训练报告生成路径。
- 可测试：测试不得依赖网络、真实 weather cache 或长时间训练。
- 可复现：报告必须记录协议配置、seed、git sha、时间粒度和 artifact 路径。
- 证据持久性：full-run 证据默认保存在 `ellectric/reports/rl_full_dataset/`。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-04, FR-05, FR-06, FR-09 | 主目标限定为增强对比评估。 |
| D-002@v1 | FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08 | 采用统一对比评估框架。 |
| D-003@v1 | FR-02, FR-03, FR-07, FR-09 | 保留现有环境/回测兼容路径。 |
