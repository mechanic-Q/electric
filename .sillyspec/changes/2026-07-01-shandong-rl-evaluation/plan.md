---
author: lmr
created_at: 2026-07-01 23:37:15
plan_level: full
---

# 实现计划

## Spike 前置验证

无需 Spike：技术方案基于现有 pandas/DataFrame、BacktestRunner、RLAgentFactory 和文件报告能力；无新技术栈、无安全隔离、无性能瓶颈假设。

## Wave 1（评估数据结构）

- [x] task-01: 新增评估协议与策略结果模型（覆盖：FR-01, D-001@v1, D-002@v1）

## Wave 2（策略执行，依赖 Wave 1）

- [x] task-02: 实现 baseline 统一评估与失败隔离（覆盖：FR-02, FR-04, D-002@v1, D-003@v1）
- [x] task-03: 实现 RL checkpoint 统一评估与失败隔离（覆盖：FR-03, FR-04, D-002@v1, D-003@v1）

## Wave 3（指标层，依赖 Wave 2）

- [x] task-04: 实现英文策略指标表与排名（覆盖：FR-05, D-001@v1, D-002@v1）

## Wave 4（报告文件，依赖 Wave 3）

- [x] task-05: 实现 evaluation 报告文件输出（覆盖：FR-06, D-001@v1, D-002@v1）

## Wave 5（图表 artifact，依赖 Wave 4）

- [x] task-06: 复用累计 P&L 图并记录 artifact 路径（覆盖：FR-06, D-002@v1）

## Wave 6（脚本与 smoke，依赖 Wave 5）

- [x] task-07: 集成 `train_rl_full_dataset.py` 到统一评估模块（覆盖：FR-07, D-002@v1, D-003@v1）
- [x] task-08: 新增独立评估入口（覆盖：FR-08, D-002@v1）
- [x] task-09: 新增评估 smoke tests（覆盖：FR-09, D-001@v1, D-003@v1）

## Wave 7（兼容验证，依赖 Wave 6）

- [x] task-10: 更新/保留 full dataset 兼容测试（覆盖：FR-07, FR-09, D-003@v1）

## Wave 8（归档文档，依赖 Wave 7）

- [x] task-11: 归档阶段同步模块卡片（覆盖：D-003@v1）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | 新增评估协议与策略结果模型 | W1 | P0 | — | FR-01, D-001@v1, D-002@v1 | 新增 `ellectric/pipeline/rl_evaluation.py` 的核心数据结构。 |
| task-02 | 实现 baseline 统一评估与失败隔离 | W2 | P0 | task-01 | FR-02, FR-04, D-002@v1, D-003@v1 | 复用现有 baseline 策略和 `BacktestRunner.replay()`。 |
| task-03 | 实现 RL checkpoint 统一评估与失败隔离 | W2 | P0 | task-01 | FR-03, FR-04, D-002@v1, D-003@v1 | 复用 `RLAgentFactory.load()` 和 `BacktestRunner.replay()`。 |
| task-04 | 实现英文策略指标表与排名 | W3 | P0 | task-02, task-03 | FR-05, D-001@v1, D-002@v1 | 输出统一英文指标，保留旧中文 compare 兼容路径。 |
| task-05 | 实现 evaluation 报告文件输出 | W4 | P0 | task-04 | FR-06, D-001@v1, D-002@v1 | 生成 json/csv/md 报告并记录失败诊断。 |
| task-06 | 复用累计 P&L 图并记录 artifact 路径 | W5 | P1 | task-02, task-03, task-05 | FR-06, D-002@v1 | 使用现有图表能力输出 html artifact。 |
| task-07 | 集成 full dataset 脚本 | W6 | P0 | task-04, task-05, task-06 | FR-07, D-002@v1, D-003@v1 | 保留原 CLI 参数与旧报告兼容。 |
| task-08 | 新增独立评估入口 | W6 | P1 | task-04, task-05, task-06 | FR-08, D-002@v1 | 支持跳过训练、只评估已有 checkpoint。 |
| task-09 | 新增评估 smoke tests | W6 | P0 | task-01~task-06 | FR-09, D-001@v1, D-003@v1 | 使用小 DataFrame 和 fake agent，不触发长训练。 |
| task-10 | 更新/保留 full dataset 兼容测试 | W7 | P0 | task-07, task-09 | FR-07, FR-09, D-003@v1 | 确认 dry-run 与旧报告兼容行为不破坏。 |
| task-11 | 归档阶段同步模块卡片 | W8 | P2 | task-01~task-10 | D-003@v1 | archive 时更新 backtester、rl-trainer、trading-env 模块说明。 |

## 关键路径

实现关键路径：task-01 → task-02/task-03 → task-04 → task-05 → task-06 → task-07 → task-10。归档收尾路径追加 task-11。

## 调用点搜索记录

- `ellectric/scripts/train_rl_full_dataset.py`: `run_backtest()`、`write_reports()`、`_render_markdown()`、`_build_interpretation()`、`RLAgentFactory.load()`、`BacktestRunner`、`SUPPORTED_STRATEGIES`。
- `tests/test_train_rl_full_dataset.py`: monkeypatch `BacktestRunner`/`SUPPORTED_STRATEGIES`、调用 `run_backtest()`、`write_reports()`。
- `ellectric/pipeline/backtester.py`: `SUPPORTED_STRATEGIES`、`BacktestRunner.replay()`、`BacktestRunner.compare()`、`BacktestRunner.plot_comparison()`。
- `ellectric/pipeline/rl_trainer.py`: `RLAgentFactory.load()`。

## 全局验收标准

- [ ] `python -m pytest tests/test_rl_evaluation.py tests/test_train_rl_full_dataset.py` 通过，或记录明确环境阻塞原因。
- [ ] `python -m ellectric.scripts.train_rl_full_dataset --dry-run --report-dir <tmp>` 返回 0。
- [ ] 未调用新评估入口时，`BacktestRunner.compare()` 当前中文列名输出保持可用。
- [ ] 新评估报告写入 `evaluation_report.json`、`evaluation_metrics.csv`、`evaluation_report.md`。
- [ ] 指标表包含 `strategy`、`total_pnl`、`sharpe`、`win_rate`、`max_drawdown`、`profit_factor`、`volatility`、`oracle_gap`、`baseline_delta`、`rank`、`status`。
- [ ] 缺失 checkpoint 或策略失败只影响该策略的 `status/error`，不阻断其他策略和报告输出。
- [ ] smoke tests 不调用真实 stable-baselines3 `.learn()`。
- [ ] full-run 证据和日志默认保存在 `ellectric/reports/rl_full_dataset/`。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-04, task-05, task-09 | AC: 统一评估目标、指标表、报告和 smoke tests。 |
| D-002@v1 | task-01, task-02, task-03, task-04, task-05, task-06, task-07, task-08 | AC: 统一框架覆盖 baseline/RL、指标、报告、脚本入口。 |
| D-003@v1 | task-02, task-03, task-07, task-09, task-10, task-11 | AC: 现有环境、回测、CLI 与测试兼容。 |
| FR-01 | task-01 | AC: 协议对象存在并被脚本使用。 |
| FR-02 | task-02 | AC: baseline trades 由统一 replay 路径生成。 |
| FR-03 | task-03 | AC: RL trades 由 checkpoint load + replay 路径生成。 |
| FR-04 | task-02, task-03, task-05 | AC: 失败策略记录 status/error，报告仍生成。 |
| FR-05 | task-04 | AC: 英文指标列完整。 |
| FR-06 | task-05, task-06 | AC: json/csv/md/html artifacts 生成。 |
| FR-07 | task-07, task-10 | AC: full dataset dry-run 兼容。 |
| FR-08 | task-08 | AC: 独立评估入口可运行。 |
| FR-09 | task-09, task-10 | AC: smoke tests 通过且不长训练。 |

## 自检结果

- [x] 每个 task 有编号（task-01、task-02 ...）
- [x] 每个 task 在 Wave 下有 checkbox（`- [ ] task-XX:` 格式）
- [x] 已标注 Wave 分组和依赖关系
- [x] 有任务总表（含优先级、依赖列，无估时列）
- [x] 有关键路径标注
- [x] 有全局验收标准
- [x] 覆盖全部当前版本 D-xxx@vN
- [x] 不存在 P0/P1 unresolved blocker
- [x] brownfield 兼容性条款已包含
- [x] 没有接口代码示例或函数实现细节
- [x] plan.md 与 design.md 文件变更清单一致
- [x] 已搜索调用点并纳入任务范围
- [x] 调用点搜索输出已记录
- [x] Wave 重排后同一 Wave 内无阻塞依赖
- [x] 没有泛泛风险分析
