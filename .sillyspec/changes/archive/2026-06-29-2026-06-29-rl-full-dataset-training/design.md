---
author: lmr
created_at: 2026-06-29 01:39:00
---

# Design: 完整 96 维 RL full dataset 训练（山东 15min）

## 背景

Phase 4 收尾结论 [[electric-phase4-closeout-20260627]] 标记的最重要持续改进项：「完整 96 维 RL training on full dataset」未跑过。当前仓库已具备：

- `ellectric/pipeline/trading_env.py:ElectricityMarketEnv` 96 维 Dict 观测/Box(96) 动作
- `ellectric/pipeline/rl_trainer.py:RLAgentFactory` PPO/SAC/TD3 三算法工厂
- `ellectric/pipeline/backtester.py:BacktestRunner` 多策略回测 + persistence/mean/oracle 三基线
- `ellectric/pipeline/features.py` Tier1-4（含 weather Tier4 cache 降级）
- `ellectric/pipeline/shandong_loader.py:ShandongDataLoader` 山东 15min 全量数据
- `ellectric/reports/weather_tier4/*` 已建立的报告范式（JSON + Markdown，hard_threshold_applied=false）

缺口仅在「跑过一次完整端到端 + 落地可复现产物」。本变更补这个缺口，不引入新框架。

## 设计目标

- G1：在山东 15min 全量数据上跑通 PPO/SAC/TD3 三算法 50k steps 训练并落盘 checkpoint
- G2：训练后用 BacktestRunner 在保留回测窗口跑 PPO/SAC/TD3 + persistence/mean/oracle 共 6 条线
- G3：产出 `training_report.json` + `training_report.md`（4 顶层字段：metadata、training、backtest、interpretation），沿用 weather-tier4-validation 报告范式
- G4：CLI 单命令复现：`python -m ellectric.scripts.train_rl_full_dataset ...`
- G5：单算法失败仅记录到报告，其它算法继续；端到端 60-120 分钟可接受
- G6：现有 trading-env/rl-trainer/backtester/feature-engineer/shandong-loader 公共 API 不变

## 非目标

- 不追求策略质量阈值，不设 MAE/RMSE/MAPE/Sharpe 硬性下限（D-001 报告式验证）
- 不做超参数搜索、不做超长训练（>50k steps）
- 不引入准实时/调度/cron/daemon/queue
- 不做多省/多节点/多市场覆盖
- 不接真实交易、不接付费数据源
- 不修改 trading_env / rl_trainer / backtester / feature-engineer / shandong-loader 的公开 API
- 不抽象新 pipeline 模块（如 `full_dataset_trainer.py`），训练循环作为 scripts 入口存在
- 不新增 notebook（学习者后续可调用脚本函数自行编写）

## 拆分判断

无需拆分，也不走批量模式。

- 模块耦合强：数据/特征/训练/回测/报告必须串接为一条 pipeline
- 算法数 3 个，不满足 ">10 重复实例" 批量模式条件，在脚本内用 `for algo in algos` 参数化即可
- 角色单一：开发者运行 CLI 产出报告

## 总体方案

按 Wave 串行实现，每 Wave 可独立单测；脚本最终把 7 个 Wave 串成 1 个 CLI 入口。

### Wave 1：数据装配与价格代理

文件：`ellectric/scripts/train_rl_full_dataset.py:build_datasets()`

1. `ShandongDataLoader().load_data()` 拿到 71,520 行 15min 全量 DataFrame
2. 构造 `load_df`：包含 `timestamp, load_mw` 及其它 schema 列
3. 构造 `price_df`：复制 `timestamp` + 把 `rt_price` 重命名为 `price_da`（D-001@v1 价格代理）
4. 用 `bfill().ffill()` 处理 `rt_price` 的 0.1% 残余 null
5. 按 `--train-start / --train-end / --test-start / --test-end` 切分 train_load / train_price / test_load / test_price 四份 DataFrame
6. UTC 时区一致性校验（ShandongDataLoader 已保证）

### Wave 2：特征工程

文件：`ellectric/scripts/train_rl_full_dataset.py:build_features()`

1. `prepare_features(load_df, tiers=["tier1","tier2","tier3","tier4"], weather_cache_path=None, fetch_if_missing=False)`：默认走 `DEFAULT_WEATHER_CACHE`，cache 缺失 → 自动降级到 Tier1-3 并记录 `weather_source=degraded`
2. 用 `engineer.get_feature_columns("tier4")` 获取最终特征列表（实际可用列已由 FeatureEngineer 内部跟踪）
3. 训练 `XGBoostForecaster`（load）+ `LEARForecaster`（price），用于 `ElectricityMarketEnv._get_prediction()` 内的预测查询
4. 训练特征仅在训练窗口拟合（防 look-ahead）

### Wave 3：环境装配

文件：`ellectric/scripts/train_rl_full_dataset.py:make_env(load_df, price_df)`

工厂函数返回 `ElectricityMarketEnv(load_df, price_df, load_forecaster, price_forecaster, max_capacity=load_df.load_mw.max(), reward_fn="profit_only", initial_cash=0.0)`（D-002@v1 统一奖励）。每个算法 + 训练/回测各自独立调用一次，避免状态污染。

### Wave 4：训练 runner

文件：`ellectric/scripts/train_rl_full_dataset.py:train_one(algo, env, timesteps, seed, log_dir, ckpt_path)`

1. `RLAgentFactory.create(algo, env, tensorboard_log=log_dir, seed=seed)`（已通过 `**kwargs` 传 seed）
2. `agent.train(total_timesteps=50_000)`
3. 训练完成后 `agent.save(ckpt_path)`
4. 整段 `try/except Exception as e`，异常时返回 `{status:"error", error:str(e), checkpoint_path:None}`（D-003@v1 单算法失败不阻断）

外层循环：`for algo in ["ppo","sac","td3"]: results[algo] = train_one(...)`。

### Wave 5：回测

文件：`ellectric/scripts/train_rl_full_dataset.py:run_backtest(train_results, test_load, test_price)`

1. 构造 `BacktestRunner(env_factory=lambda: make_env(test_load, test_price))`
2. 对每个基线策略名 `s in SUPPORTED_STRATEGIES`：`runner.replay(s, test_load, test_price, test_start, test_end, strategy_name=s)`
3. 对每个 `algo` 训练成功的 agent：`runner.replay(agent, test_load, test_price, ..., strategy_name=f"rl_{algo}")`
4. `runner.compare({...})` 得到 metrics DataFrame
5. `BacktestRunner.plot_comparison(results)` 保存到 `ellectric/reports/rl_full_dataset/cumulative_pnl.html`

### Wave 6：报告

文件：`ellectric/scripts/train_rl_full_dataset.py:write_reports(report_dict, report_dir)`

JSON schema（沿用 weather-tier4-validation 命名风格）：

```json
{
  "metadata": {
    "generated_at": "ISO 8601 UTC",
    "git_sha": "...",
    "time_config": {"freq": "15min", "points_per_day": 96},
    "seed": 42,
    "algos": ["ppo","sac","td3"],
    "timesteps_per_algo": 50000,
    "train_range": ["2024-01-01","2025-09-30"],
    "test_range":  ["2025-10-01","2026-01-14"],
    "tier": "tier4",
    "weather_source": "cache|fetch|degraded",
    "reward_fn": "profit_only",
    "price_proxy": "rt_price->price_da"
  },
  "training": {
    "ppo": {"status":"ok|error", "final_reward": float, "duration_s": float, "checkpoint_path": "...", "tb_log_path":"...", "error": null|str},
    "sac": {...},
    "td3": {...}
  },
  "backtest": {
    "metrics": [ {"strategy":"oracle","total_return":...,"sharpe":...,"win_rate":...,"max_drawdown":...,"n_trades":...}, ... ],
    "cumulative_pnl_html_path": "ellectric/reports/rl_full_dataset/cumulative_pnl.html"
  },
  "interpretation": {
    "hard_threshold_applied": false,
    "summary": "短摘要：成功算法数 / 总算法数；最佳策略名"
  }
}
```

Markdown 报告：把上面 4 段渲染为人类可读表格 + 解释段。

### Wave 7：CLI

文件：`ellectric/scripts/train_rl_full_dataset.py:main()`

`argparse` 入参：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--train-start` | `2024-01-01` | 训练窗口起 |
| `--train-end` | `2025-09-30` | 训练窗口止 |
| `--test-start` | `2025-10-01` | 回测窗口起 |
| `--test-end` | `2026-01-14` | 回测窗口止 |
| `--timesteps` | `50000` | 每算法训练步数 |
| `--algos` | `ppo,sac,td3` | 算法逗号列表 |
| `--tier` | `tier4` | `tier3` 或 `tier4`（启用 weather） |
| `--seed` | `42` | 全局 seed |
| `--report-dir` | `ellectric/reports/rl_full_dataset` | 报告目录 |
| `--checkpoint-dir` | `models/rl_full_dataset` | checkpoint 目录 |
| `--tb-log-root` | `tb_logs` | TensorBoard 根目录 |
| `--dry-run` | flag | 仅装配 smoke（不调 `.learn()`），退出 0 |

`--dry-run` 用途：CI/快速冒烟，验证数据 + 特征 + env + factory + report writer schema 通路无异常。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/scripts/train_rl_full_dataset.py` | 完整 96 维 RL full dataset 训练 CLI 入口（Wave 1-7 串接） |
| 新增 | `tests/test_train_rl_full_dataset.py` | 单元 + smoke 测试，不在 CI 跑 50k |
| 新增 | `ellectric/reports/rl_full_dataset/.gitkeep` | 报告目录占位（产物 .gitignore） |
| 修改 | `docs/Ellectric/modules/rl-trainer.md` | 增 "full-dataset 训练入口" 章节，引用脚本 + 报告路径 |
| 修改 | `.planning/ROADMAP.md` | Phase 4 持续改进第 1 项标注「已完成首轮」并指向报告 |
| 修改 | `ellectric/README.md` | Phase 4 持续改进项 checkbox 勾选「完整 96 维 RL training」 |
| 修改 | `.gitignore` | 忽略 `ellectric/reports/rl_full_dataset/*.json/*.md/*.html` 与 `models/rl_full_dataset/*.zip` 与 `tb_logs/rl_full_dataset_*/` |

不动：`ellectric/pipeline/{trading_env.py,rl_trainer.py,backtester.py,features.py,shandong_loader.py,forecaster.py,price_forecaster.py}`、`ellectric/config.py`、wiki。wiki 在 archive 阶段统一写 closeout synthesis。

## 接口定义

`ellectric/scripts/train_rl_full_dataset.py` 模块级函数：

```python
def build_datasets(
    train_start: str, train_end: str, test_start: str, test_end: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """返回 (train_load, train_price, test_load, test_price)。
    price_df 列名为 timestamp + price_da（来源 rt_price 重命名）。"""

def build_features(
    load_df: pd.DataFrame, tier: str, weather_cache_path: str | None,
) -> tuple[pd.DataFrame, list[str], str]:
    """返回 (feature_df, feature_cols, weather_source)。
    weather_source ∈ {"cache","fetch","degraded"}。tier='tier3' 时 weather_source 固定 'skipped'。"""

def make_env(
    load_df: pd.DataFrame, price_df: pd.DataFrame,
    load_forecaster=None, price_forecaster=None,
) -> ElectricityMarketEnv: ...

def train_one(
    algo: str, env: ElectricityMarketEnv, *,
    timesteps: int, seed: int, log_dir: str, ckpt_path: str,
) -> dict:
    """返回 {status, final_reward, duration_s, checkpoint_path, tb_log_path, error}。
    异常被吞并以 status='error' 上报。"""

def run_backtest(
    train_results: dict, test_load: pd.DataFrame, test_price: pd.DataFrame,
    test_start: str, test_end: str, report_dir: str,
) -> dict:
    """返回 {metrics: list[dict], cumulative_pnl_html_path: str}。"""

def write_reports(report: dict, report_dir: str) -> tuple[str, str]:
    """返回 (json_path, md_path)。原子写入（先 .tmp 后 rename）。"""

def main(argv: list[str] | None = None) -> int:
    """CLI 入口。返回 0=成功；1=数据/特征装配失败；2=报告写入失败。"""
```

## 数据模型

无数据库 schema 变更。

派生产物：

| 路径 | 类型 | 说明 |
|---|---|---|
| `models/rl_full_dataset/{ppo,sac,td3}.zip` | 二进制 | sb3 模型 checkpoint |
| `tb_logs/rl_full_dataset_{ppo,sac,td3}/` | 目录 | TensorBoard 日志 |
| `ellectric/reports/rl_full_dataset/training_report.json` | 文本 | 主 JSON 报告 |
| `ellectric/reports/rl_full_dataset/training_report.md` | 文本 | 主 Markdown 报告 |
| `ellectric/reports/rl_full_dataset/cumulative_pnl.html` | 文本 | Plotly 累计 P&L 对比图 |

## 兼容策略

- 旧 `trading_env / rl_trainer / backtester / features / shandong_loader / forecaster / price_forecaster` 公开 API 全部保留，本变更只**调用**它们
- 现有 `weather-tier4-validation` 报告 schema 不变；新报告复用风格但路径独立
- 未运行新脚本时，仓库行为与变更前完全一致
- `price_da = rt_price.rename(...)` 仅作用于本脚本内构造的 `price_df`，不修改 ShandongDataLoader 输出列名
- 旧 RL 演示（notebooks/09-10、demo_ppo.zip 等）不受影响

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 50k×3 算法 + 71,520 行 env 在普通笔记本可能 > 120 分钟 | P1 | 默认窗口已切到 21 个月训练、3.5 个月回测；`--algos ppo` 可子集跑；`--timesteps` 可降到 10k 应急 |
| R-02 | sb3 PPO 在 96 维 Box 动作 + Dict 观测下可能 NaN/divergence | P1 | seed 固定；try/except 隔离；TensorBoard 日志可事后排查 |
| R-03 | weather cache 缺失导致 Tier4 静默降级到 Tier3 | P1 | report.metadata.weather_source 记录实际来源；`--tier tier3` 用户可显式禁用 weather |
| R-04 | rt_price 残余 null（0.1%）破坏 trading_env 切片 | P2 | Wave 1 显式 `bfill().ffill()`；测试用例覆盖少量 null 输入 |
| R-05 | `BacktestRunner._log_oracle_dominance` 触发 warning 让报告噪声变大 | P2 | 报告里只引用 `compare()` 的 metrics，warning 只进 stderr 不阻断 |
| R-06 | 50k steps 训练时间长，CI 不应阻塞 | P1 | tests 不真调 `.learn()`：仅用 `--dry-run` 路径 + mock `RLAgentFactory.create` 返回 fake agent；脚本作为可选 GitHub Action 或本地手动跑 |
| R-07 | TimeSeriesSplit gap=24 假设小时级，已在 forecaster.py 内部使用；山东 15min 下 gap=24 仅相当于 6 小时 | P2 | 不在本变更范围；XGBoost/LEAR 训练沿用现有 forecaster 行为；接受这一既有偏差，留作后续单独变更 |
| R-08 | 训练 env 的 `max_capacity = train_load.load_mw.max()` 与回测 env 的 `max_capacity = test_load.load_mw.max()` 不一致（BacktestRunner.replay 内部覆盖） | P2 | RL agent 输出归一化 [0,1] 动作，max_capacity 仅作 scale；两端独立 env 不污染状态；report.metadata 同时记录 train/test 两个 max_capacity 便于审阅 |
| R-09 | sb3 PPO/SAC/TD3 在极小 timesteps（< n_steps=2048 或 learning_starts=100）下行为不可靠，单元测试不应真调用 `.learn()` | P1 | 测试用 `monkeypatch` 注入 fake adapter（实现 `predict/save/load/evaluate`），脚本逻辑/报告 schema/CLI 在测试中走 fake；真 sb3 训练仅在 `--dry-run=False` 的本地/可选 Action 中触发 |

## 决策追踪

- D-001@v1 价格列代理：用 `rt_price` 重命名为 `price_da` → 覆盖 Wave 1 / FR-数据装配
- D-002@v1 奖励函数统一 `profit_only` → 覆盖 Wave 3-4 / FR-训练
- D-003@v1 单算法失败仅记录 error 跳过 → 覆盖 Wave 4 / FR-训练 / R-02
- D-004@v1 实现方案 = 单 CLI 脚本无新 pipeline 模块 → 覆盖文件变更清单 / 兼容策略 / 非目标
- D-005@v1 50k steps + 三基线 → 覆盖 G2/G3 / Wave 4-5
- D-006@v1 训练/回测切分 + Tier1-4 → 覆盖 Wave 1-2 / R-03
- D-007@v1 tests 用 fake adapter，不真调 sb3 → 覆盖 R-06/R-09 / tests
- D-008@v1 report.metadata 同时记录 train/test max_capacity → 覆盖 R-08 / Wave 6
- A+ 范围决策（B 步预算 + B 数据切分）→ 覆盖 G1/G2/G3
- 方案 A 决策（单脚本无新模块）→ 覆盖文件变更清单

未解决：无（R-07 是显式接受的既有偏差，不属于本变更）。

## 自审

| 检查项 | 结果 | 说明 |
|---|---|---|
| 需求覆盖 | 通过 | 覆盖 brainstorm 3 轮回答（A+、B 预算、B 切分）+ Grill 3 决策 |
| Grill 覆盖 | 通过 | D-001@v1 / D-002@v1 / D-003@v1 均在 design 内引用 |
| 约束一致性 | 通过 | 延续 CONVENTIONS.md 的中文 docstring / Tier 模式 / logger 标准化 / 可选依赖降级；不动 ARCHITECTURE.md 中既有模块 |
| 真实性 | 通过 | ShandongDataLoader/ElectricityMarketEnv/RLAgentFactory/BacktestRunner/prepare_features 均真实存在；新增文件标 "新增" |
| YAGNI | 通过 | 无 notebook、无新 pipeline 模块、无超参搜索、无多省/多市场 |
| 验收标准 | 通过 | 报告 JSON schema 字段、tests 列表、CLI 入参、`--dry-run` 行为均可测试 |
| 非目标清晰 | 通过 | 列出 8 项非目标（包括 R-07 既有偏差） |
| 兼容策略 | 通过 | 不动 5 个 pipeline 模块公开 API；价格代理仅作用于本脚本 |
| 风险识别 | 通过 | R-01~R-09 含训练时长、NaN、cache 降级、null、oracle warning、CI、TimeSeriesSplit gap、max_capacity 不一致、sb3 极小 timesteps 不可靠 |
| 生命周期契约表 | 不适用 | 无 session/lease/agent_run/daemon/lifecycle/claim/heartbeat 关键词；脚本是单进程 CLI |
