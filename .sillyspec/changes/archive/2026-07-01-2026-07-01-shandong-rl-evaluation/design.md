---
author: lmr
created_at: 2026-07-01 23:37:15
---

# Design — 山东 RL 统一对比评估

## 背景

山东 15min 数据上的 RL full dataset 训练脚本已经能完成 PPO/SAC/TD3 训练、基线回测和报告输出，但当前评估逻辑分散在 `train_rl_full_dataset.py`、`BacktestRunner.compare()` 和报告渲染函数中。问题不是缺少一个新算法，而是对比协议不够显式：数据切分、策略集合、指标口径、失败诊断和 artifact 路径都由脚本内联拼装，后续很难判断 RL 策略是否公平地优于 persistence/mean/oracle 基线。

用户确认本次主目标是“增强对比评估”，并选择方案 B：统一对比评估框架。该变更聚焦把评估协议、策略注册、指标计算、报告生成抽成清晰模块，让 PPO/SAC/TD3 与基线策略走同一回测路径、同一指标口径、同一报告输出。

## 设计目标

1. 统一山东 RL 策略评估协议：固定 train/test 窗口、seed、算法列表、基线列表、输出目录和 artifact 命名。
2. 统一策略执行路径：baseline 和 RL agent 都通过 `BacktestRunner.replay()` 产生交易明细。
3. 扩展评估指标：保留现有总收益、夏普比率、胜率、最大回撤、交易次数，同时新增面向对比的 `profit_factor`、`volatility`、`oracle_gap`、`baseline_delta`、`rank`、`status`。
4. 报告可复现：输出 markdown/json/csv/html，记录配置摘要、输入窗口、算法训练结果、策略失败原因、artifact 路径。
5. 支持 smoke/full 两档：dry-run 或极小样本用于装配验证，full run 用于最终证据报告。

## 非目标

- 不重定义 `ElectricityMarketEnv` 的 reward 公式。
- 不把 96 维动作空间改成 1 维动作。
- 不新增 Datawhale 数据源或外部数据下载流程。
- 不新增山东结算规则模拟。
- 不做超参数搜索、reward sweep 或算法收益优化。
- 不引入 ASSUME、多智能体仿真或实时调度。

## 拆分判断

本次变更虽然涉及 `backtester`、`rl_trainer`、`scripts` 和 `reports`，但它们服务同一个目标：统一 RL 对比评估。没有多角色权限、页面流程或大量模板化实例；不需要拆分成多个 SillySpec 变更，也不需要批量模式。

## 总体方案

### Wave 1: 评估协议与策略集合

新增评估协议数据结构，集中描述山东 RL 评估所需配置：训练窗口、回测窗口、算法列表、基线策略列表、seed、timesteps、checkpoint 目录、report 目录、price proxy、feature tier。脚本不再散落这些默认值，而是从协议对象生成后续训练、回测和报告所需上下文。

策略集合保持向后兼容：现有 `SUPPORTED_STRATEGIES` 继续支持 `baseline_persistence`、`baseline_mean`、`oracle`；RL 策略仍通过 `RLAgentFactory.load(algo, path, env)` 加载并交给 `BacktestRunner.replay(agent, ...)`。新增 registry/plan 层只负责描述“本次要评估哪些策略”，不改变策略实际交易逻辑。

### Wave 2: 指标层增强

在 `backtester` 周边新增纯函数指标层，输入仍是 `{strategy_name: trades_df}`，其中 trades_df 来自 `BacktestRunner.replay()`。指标层计算统一英文列名，避免后续报告同时处理中文/英文列名。现有 `BacktestRunner.compare()` 可保留中文列名以兼容旧 notebook；新评估脚本优先使用新增指标函数。

新增指标定义：
- `total_pnl`: `pnl_hourly.sum()`
- `sharpe`: 沿用现有 8760 年化口径，后续如需 15min 严格年化可单独调整
- `win_rate`: `pnl_hourly > 0` 比例
- `max_drawdown`: 累计 P&L 相对历史峰值的最小回撤
- `profit_factor`: 正收益和 / abs(负收益和)，无负收益时为 `inf`
- `volatility`: `pnl_hourly.std()`
- `oracle_gap`: `(oracle_total - strategy_total) / abs(oracle_total)`，oracle 不存在时为空
- `baseline_delta`: `strategy_total - baseline_persistence_total`，baseline 不存在时为空
- `rank`: 按 `total_pnl` 降序排名
- `status`: ok / error / skipped

### Wave 3: 报告生成器

新增 report builder，负责把协议、训练结果、回测结果、指标表和失败诊断渲染为文件：
- `evaluation_report.json`: 机器可读完整结果
- `evaluation_metrics.csv`: 指标表，便于后续 notebook 或外部分析
- `evaluation_report.md`: 人类阅读报告，包含排行榜、基线对比、失败诊断、artifact 路径
- `cumulative_pnl.html`: 复用现有 Plotly 图表

报告目录默认沿用 `ellectric/reports/rl_full_dataset/`。日志和最终 full-run 证据仍保存在该目录下，避免 `/tmp` 重启丢失。

### Wave 4: 脚本集成与验证

优先复用 `ellectric/scripts/train_rl_full_dataset.py`，将当前内联的 `run_backtest()`、`write_reports()`、`_render_markdown()` 中的评估/报告逻辑逐步委托给新评估模块。为降低风险，可新增 `ellectric/scripts/evaluate_rl_strategies.py` 作为独立入口，先对已有 checkpoint 和基线做评估；再让 full dataset 脚本调用同一套函数。

测试补充以 smoke 为主：不跑 50k timesteps，不依赖长训练。构造小 DataFrame 和 dummy agent，验证策略注册、回测输出、指标计算、报告文件写入与失败策略不中断整体报告。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/pipeline/rl_evaluation.py` | 评估协议、策略评估结果、指标计算、报告生成纯函数。 |
| 修改 | `ellectric/pipeline/backtester.py` | 保留现有 API，必要时复用新指标函数或补充英文指标输出辅助函数。 |
| 修改 | `ellectric/scripts/train_rl_full_dataset.py` | 将内联评估/报告逻辑委托给 `rl_evaluation.py`，保留原 CLI 参数。 |
| 新增 | `ellectric/scripts/evaluate_rl_strategies.py` | 可选独立评估入口：加载 checkpoint + 基线，生成评估报告。 |
| 新增/修改 | `tests/test_rl_evaluation.py` | 覆盖指标计算、报告输出、失败诊断、smoke 协议。 |
| 修改 | `.sillyspec/docs/Ellectric/modules/backtester.md` | 归档时补充评估指标/报告职责。 |
| 修改 | `.sillyspec/docs/Ellectric/modules/rl-trainer.md` | 归档时补充评估脚本如何加载已训练模型。 |
| 修改 | `.sillyspec/docs/Ellectric/modules/trading-env.md` | 归档时记录本次不修改 reward/action，只作为评估环境。 |

## 接口定义

### 新增 `EvaluationProtocol`

```python
@dataclass(frozen=True)
class EvaluationProtocol:
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    algos: tuple[str, ...] = ("ppo", "sac", "td3")
    baselines: tuple[str, ...] = ("baseline_persistence", "baseline_mean", "oracle")
    seed: int = 42
    timesteps: int = 50000
    tier: str = "tier4"
    price_proxy: str = "rt_price->price_da"
    checkpoint_dir: str = "models/rl_full_dataset"
    report_dir: str = "ellectric/reports/rl_full_dataset"
```

### 新增 `StrategyEvaluation`

```python
@dataclass
class StrategyEvaluation:
    strategy: str
    status: str
    trades: pd.DataFrame | None = None
    error: str | None = None
    artifact_path: str | None = None
```

### 新增指标/报告函数

```python
def evaluate_baselines(
    runner: BacktestRunner,
    baselines: Iterable[str],
    load_data: pd.DataFrame,
    price_data: pd.DataFrame,
    start: str,
    end: str,
) -> dict[str, StrategyEvaluation]: ...


def evaluate_rl_agents(
    runner: BacktestRunner,
    algos: Iterable[str],
    checkpoint_dir: str,
    load_data: pd.DataFrame,
    price_data: pd.DataFrame,
    start: str,
    end: str,
) -> dict[str, StrategyEvaluation]: ...


def compute_strategy_metrics(
    evaluations: Mapping[str, StrategyEvaluation],
    baseline_name: str = "baseline_persistence",
    oracle_name: str = "oracle",
) -> pd.DataFrame: ...


def write_evaluation_report(
    protocol: EvaluationProtocol,
    training: Mapping[str, dict],
    evaluations: Mapping[str, StrategyEvaluation],
    metrics: pd.DataFrame,
    report_dir: str | Path,
    cumulative_pnl_html_path: str = "",
) -> dict[str, str]: ...
```

### 现有接口保持

- `BacktestRunner.replay(model, load_data, price_data, start, end, strategy_name="rl") -> pd.DataFrame`
- `BacktestRunner.compare(results) -> pd.DataFrame`
- `BacktestRunner.plot_comparison(results, title="策略对比") -> go.Figure`
- `RLAgentFactory.load(algo, path, env=None) -> BaseRLAgent`

## 数据模型

本次不修改业务数据表或上游 DataFrame 合约。输入仍沿用：
- load data: `timestamp`, `load_mw`
- price data: `timestamp`, `price_da`
- trades df: `timestamp`, `bid_mw`, `cleared_mw`, `clearing_price`, `actual_load`, `pnl_hourly`, `pnl_cumulative`, `strategy`

新增报告数据结构仅写入文件：

```json
{
  "metadata": {"generated_at": "...", "git_sha": "..."},
  "protocol": {"train_start": "...", "test_start": "..."},
  "training": {"ppo": {"status": "ok"}},
  "evaluations": {"rl_ppo": {"status": "ok", "error": null}},
  "metrics": [{"strategy": "rl_ppo", "total_pnl": 0.0}],
  "artifacts": {"metrics_csv": "...", "cumulative_pnl_html": "..."}
}
```

## 兼容策略

- 未调用新评估入口时，现有训练、回测、notebook 行为不变。
- `BacktestRunner.compare()` 原中文列名输出保留，避免破坏既有报告和测试。
- `train_rl_full_dataset.py` 保留原 CLI 参数和默认路径，内部委托新模块。
- 新 report builder 写新增文件，不删除旧 `training_report.json` / `training_report.md`；过渡期可同时生成旧报告和新评估报告。
- 某个 RL 模型 checkpoint 缺失或加载失败时，仅该策略标记 error，不阻断基线与其他策略报告。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 指标口径变化导致旧报告不可直接对比 | P1 | 保留旧 `BacktestRunner.compare()`，新指标使用英文列名并在报告中写明口径。 |
| R-02 | RL checkpoint 不存在或 sb3 加载失败 | P1 | `StrategyEvaluation.status=error`，报告记录 error，不阻断整体评估。 |
| R-03 | smoke 测试误触发长时间训练 | P1 | 测试使用 dummy agent 和小 DataFrame，不调用 `.learn()`。 |
| R-04 | oracle 总收益低于其他策略时解释困难 | P2 | 沿用 `_log_oracle_dominance()` warning，并在报告诊断区显示 oracle_gap。 |
| R-05 | `TimeConfig.points_per_day` 为 96，历史文档仍写 24h/小时口径 | P2 | 报告 metadata 写入 `points_per_day`，设计中不改环境时间粒度。 |

## 决策追踪

- D-001@v1 覆盖章节：背景、设计目标、总体方案。结论：主目标是增强 RL 对比评估，不优先修改 reward/action 或训练算法。
- D-002@v1 覆盖章节：总体方案 Wave 1、兼容策略。结论：采用方案 B，抽出统一评估框架。
- D-003@v1 覆盖章节：文件变更清单、接口定义。结论：新增 `rl_evaluation.py`，保留现有 `BacktestRunner` 与 CLI 兼容。

## 自审

| 检查项 | 结论 |
|---|---|
| 需求覆盖 | 通过：覆盖用户确认的“增强对比评估”。 |
| Grill 覆盖 | 通过：design 引用当前版本 D-001@v1、D-002@v1、D-003@v1。 |
| 约束一致性 | 通过：保持 Python pipeline、typing、DataFrame 合约、报告目录约定。 |
| 真实性 | 通过：现有类/函数来自 `backtester.py`、`rl_trainer.py`、`train_rl_full_dataset.py`；新增接口明确标注为新增。 |
| YAGNI | 通过：不做 reward/action 重定义、不做 Datawhale、不做超参搜索。 |
| 验收标准 | 通过：可通过 smoke 测试、报告文件、指标列验证。 |
| 非目标 | 通过：明确排除训练优化和市场规则重构。 |
| 兼容策略 | 通过：保留旧 compare 和 CLI 参数。 |
| 风险识别 | 通过：记录指标口径、checkpoint、长训练、oracle、时间粒度风险。 |
| 长期运行契约 | 不适用：本次不涉及后台任务协议或分布式运行心跳。 |
