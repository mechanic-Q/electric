# Structure — Ellectric

> **author**: lmr
> **created_at**: 2026-06-10T00:00:00+08:00
> **updated_at**: 2026-06-10T00:00:00+08:00
> **scan_type**: full
> **root**: `/mnt/e/Ellectric/`

## 项目阶段概览

| 阶段 | 范围 | 关键交付 |
|------|------|----------|
| **Phase 1** | 数据基础 + 负荷预测 | OWID 数据接入 → 清洗 → 特征工程 → XGBoost 负荷预测 → Notebook 01-05 |
| **Phase 2** | 电价预测 + 市场仿真 | LEAR 电价预测 (Lasso) → ASSUME 电力市场仿真 → Notebook 06-08 |
| **Phase 3** | RL 交易 + 回测 + 可解释性 | PPO/SAC/TD3 强化学习 → 多策略回测 → SHAP 模型解释 → Notebook 09-11 |
| **Phase 4** | 集成层 (API/CLI/LLM) | FastAPI REST 服务 → Typer 命令行 → LangChain DeepSeek 代理 |

**项目特点**：纯 Python 学习/教育平台，**无测试目录** (`tests/`)，**无 CI/CD** 配置。验证依赖 Jupyter Notebook 执行和手动脚本。

## Directory Tree

```
Ellectric/                              # 项目根目录
├── AGENTS.md                           # GSD + SillySpec workflow 指令
├── INSTRUCTIONS.md                     # OpenCode CLI + Karpathy 行为指南
├── CLAUDE.md                           # Claude Code 项目指令（完整架构、约定）
├── .gitignore                          # Python, Jupyter, data, IDE, OS 排除规则
├── .claude/                            # Claude 配置（GSD skills 目录）
├── .opencode/                          # OpenCode 工具链 (node_modules, skills)
├── .sillyspec/                         # SillySpec 状态 & 扫描文档
│   ├── .runtime/                       # 运行时 DB, user-inputs, 扫描缓存
│   ├── docs/Ellectric/scan/            # 扫描输出 (STRUCTURE, ARCHITECTURE, CONVENTIONS...)
│   ├── knowledge/                      # 归档知识 (INDEX.md, uncategorized.md)
│   ├── projects/Ellectric.yaml         # 项目元数据
│   └── workflows/                      # 工作流模板
├── .planning/                          # GSD 规划资产（只读参考）
│   ├── PROJECT.md                      # 项目章程与约束
│   ├── REQUIREMENTS.md                 # v1/v2 需求与追溯矩阵
│   ├── ROADMAP.md                      # 4 阶段路线图与成功标准
│   ├── STATE.md                        # 里程碑状态跟踪
│   ├── config.json                     # GSD 配置开关
│   ├── phases/01-data-foundation-basic-prediction/  # Phase 1 规划文档
│   └── research/                       # 技术调研文档
├── docs/
│   ├── chinese-electricity-data-guide.md     # 中国电力数据获取指南
│   └── Ellectric/scan/                       # SillySpec 扫描文档
│       ├── ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, ...
│       └── INTEGRATIONS.md, TESTING.md, CONCERNS.md, PROJECT.md
└── ellectric/                          # 主 Python 包（Phase 1-4 交付物）
    ├── README.md                       # 项目 README：快速开始、结构、数据合约、学习路径
    ├── setup.sh                        # 一键环境引导脚本
    ├── requirements.txt                # Python 依赖（通用）
    ├── requirements-assume.txt         # ASSUME 框架依赖
    ├── requirements-phase4.txt         # Phase 4 集成层依赖
    ├── docker-compose.yml              # Grafana 仪表板（ASSUME 可视化）
    │
    ├── pipeline/                       # [Phase 1-3] 核心机器学习/交易管道（12 模块）
    │   ├── __init__.py                 # 包标记，导出 LEARForecaster, PriceDataLoader, run_statistical_tests
    │   ├── data_loader.py              # [P1] 数据加载：抽象基类 + OWID 自动抓取 + 本地文件加载 + 工厂
    │   ├── cleaner.py                  # [P1] 数据清洗：缺失填充、IQR 异常检测（仅报告）、UTC 标准化
    │   ├── features.py                 # [P1] 特征工程：FeatureEngineer 三层渐进式特征（Tier 1/2/3）
    │   ├── forecaster.py               # [P1] 负荷预测：持久性基线 + XGBoost + 时间感知交叉验证 + P&L 可视化
    │   ├── price_loader.py            # [P2] 电价数据加载：ZionLuo xlsx 7 列数据加载与标准化
    │   ├── price_forecaster.py        # [P2] 电价预测：LEAR (Lasso Estimated AutoRegressive) + 3 层价格特征
    │   ├── trading_env.py             # [P3] RL 交易环境：ElectricityMarketEnv (Gymnasium Dict/Box, 3 种奖励函数)
    │   ├── rl_trainer.py              # [P3] RL 训练：BaseRLAgent ABC + PPO/SAC/TD3 适配器 + RLAgentFactory
    │   ├── backtester.py              # [P3] 回测引擎：BacktestRunner + 3 种基线策略 + RL 策略对比
    │   ├── shap_explainer.py          # [P3] SHAP 可解释性：TreeExplainer (XGBoost) + LinearExplainer (LEAR)
    │   └── statistical_tests.py       # [P2] 统计检验：Diebold-Mariano + Giacomini-White（epftoolbox，mock 后备）
    │
    ├── api/                            # [Phase 4] FastAPI REST API
    │   └── server.py                   # 5 路由：/health (GET), /predict, /simulate, /backtest, /explain (POST)
    │
    ├── service/                        # [Phase 4] 服务层（桥接 API/CLI/LLM 到 pipeline）
    │   ├── schemas.py                  # Pydantic v2 模型：8 个请求/响应模型，cross-field validation
    │   └── handlers.py                 # 业务处理器：4 个函数（run_forecast/simulate/backtest/explain），全部延迟导入
    │
    ├── cli/                            # [Phase 4] Typer CLI
    │   └── main.py                     # 5 子命令：forecast, simulate, backtest, explain, ask (LLM 对话)
    │
    ├── llm/                            # [Phase 4] LangChain LLM 接口
    │   ├── agent.py                    # create_agent_executor() + ask_agent() (DeepSeek Chat API)
    │   ├── tools.py                    # 3 @tool 函数：httpx 调用本地 FastAPI（query_forecast, run_simulation, run_backtest）
    │   └── chat.py                     # 交互式终端对话循环
    │
    ├── assume/                         # [Phase 2] ASSUME 电力市场仿真
    │   ├── configs/                    # YAML 场景配置（default, summer_peak, wind_high）
    │   ├── grafana/                    # Grafana 仪表板 JSON
    │   ├── run_simulation.py           # 仿真入口（subprocess 目标）
    │   └── verify_simulation.py        # 仿真环境验证
    │
    ├── notebooks/                      # [Phase 1-3] 11 个渐进式 Jupyter Notebook
    │   ├── 01_data_ingestion.ipynb     # [P1] 数据获取
    │   ├── 02_data_cleaning.ipynb      # [P1] 数据清洗
    │   ├── 03_feature_engineering.ipynb # [P1] 特征生成
    │   ├── 04_load_forecasting.ipynb   # [P1] XGBoost 负荷预测
    │   ├── 05_end_to_end_baseline.ipynb # [P1] 端到端基线
    │   ├── 06_price_forecasting.ipynb  # [P2] LEAR 电价预测
    │   ├── 07_model_comparison_dashboard.ipynb # [P2] 模型比较
    │   ├── 08_assume_results.ipynb     # [P2] ASSUME 仿真结果
    │   ├── 09_rl_trading_agent.ipynb   # [P3] RL 交易智能体 (PPO/SAC/TD3)
    │   ├── 10_multi_agent_backtest.ipynb # [P3] 多策略回测
    │   └── 11_model_explainability.ipynb # [P3] SHAP 可解释性
    │
    ├── scripts/                        # 验证 & 演示脚本
    │   ├── run_demo.py                 # [P4] 全模型演示（XGBoost, LEAR, PPO/SAC/TD3 backtest, SHAP）
    │   ├── verify_assume.py            # [P2] ASSUME 环境验证
    │   └── verify_phase3.sh            # [P3] Phase 3 验证脚本
    │
    └── data/                           # 本地数据目录
        ├── .gitkeep
        ├── electricity_load_hourly.parquet   # OWID 清洗后负荷数据
        ├── demo_*.joblib / *.zip             # 演示模型（XGBoost, LEAR, PPO）
        ├── epft_*.csv                        # epftoolbox 标准数据集
        ├── dmgw_results.json                 # DM/GW 检验结果
        ├── demo_backtest.html                # 回测可视化
        ├── demo_shap_*.html                  # SHAP 瀑布图
        └── demo_test_data.parquet            # 回测测试数据
```

## Module Descriptions

### `ellectric/` — 主 Python 包
包含 Phase 1-4 所有交付物的 Python 包。设计为自包含学习环境：一键环境搭建、11 个渐进式 Jupyter Notebook、模块化流水线库。Python 3.11+ 要求。根目录下提供 `setup.sh` 一键安装脚本和 3 个 `requirements-*.txt` 分阶段依赖文件。

---

### `ellectric/pipeline/` — 核心流水线（Phase 1-3，12 模块）

该目录按阶段分层组织，Phase 1 完成数据接入→预测端到端基线，Phase 2 扩展电价预测与市场仿真，Phase 3 增加强化学习交易与可解释性。

| 模块 | 阶段 | 用途 | 关键类/函数 |
|------|------|------|-------------|
| `__init__.py` | — | 包标记；导出 LEARForecaster, PriceDataLoader, run_statistical_tests | — |
| `data_loader.py` | P1 | 数据获取层 — 抽象统一接口背后的数据源 | `DataLoader` (ABC), `OWIDChinaLoader` (自动抓取 GitHub CSV), `ChineseDataLoader` (本地 CSV/Excel/Parquet), `create_loader()` (工厂) |
| `cleaner.py` | P1 | 数据清洗与验证 — 强制执行下游数据合约（timestamp + load_mw） | `clean_data()` (4 步流水线：验证→填充→IQR 报告→UTC 标准化), `validate_schema()` (运行时 schema 检查) |
| `features.py` | P1 | 特征工程 — 三层渐进式特征生成（负荷预测用） | `FeatureEngineer` (add_tier1/2/3_features()), `prepare_features()` (便捷接口) |
| `forecaster.py` | P1 | 负荷预测 — 持久性基线 + XGBoost + 时间感知交叉验证 + 交互可视化 | `persistence_forecast()` (t-24h 基线), `calculate_pnl()`, `plot_pnl()` (Plotly), `XGBoostForecaster` (train_evaluate + predict, 每折独立 StandardScaler) |
| `price_loader.py` | P2 | 电价数据加载 — 读取 ZionLuo xlsx 7 列表格数据 | `PriceDataLoader` (load_data, get_metadata), `create_price_loader()` (工厂), `_standardize_columns()` (中英列名映射) |
| `price_forecaster.py` | P2 | 电价预测 — LEAR (Lasso Estimated AutoRegressive) 模型 | `LEARForecaster` (add_price_features 3 层, train_evaluate, predict, save/load_model, plot_price_forecast) |
| `trading_env.py` | P3 | RL 交易环境 — Gymnasium 强化学习环境 | `ElectricityMarketEnv` (Dict/Box 空间, 24h 竞价), `RewardRegistry` (profit_only/risk_adjusted/volume_penalty), `RewardFunction` (Protocol) |
| `rl_trainer.py` | P3 | RL 训练 — PPO/SAC/TD3 统一接口 | `BaseRLAgent` (ABC), `PPOAgent`/`SACAgent`/`TD3Agent` (适配器), `RLAgentFactory` (create/load) |
| `backtester.py` | P3 | 回测引擎 — 历史数据回放 + 多策略对比 | `BacktestRunner` (replay, compare), `baseline_persistence()`/`baseline_mean()`/`oracle_strategy()` |
| `shap_explainer.py` | P3 | SHAP 模型可解释性 — 瀑布图与特征重要性 | `explain_xgboost_sample()` (TreeExplainer), `explain_lear_sample()` (LinearExplainer), `feature_importance_ranking()` |
| `statistical_tests.py` | P2 | DM/GW 统计检验 — 预测模型比较 | `run_statistical_tests()` (epftoolbox 后端，mock 后备) |

---

### `ellectric/api/` — FastAPI REST API（Phase 4）
FastAPI 应用，5 条路由：
- `GET /health` — 健康检查
- `POST /predict` — 负荷/电价预测
- `POST /simulate` — ASSUME 市场仿真
- `POST /backtest` — 多策略回测
- `POST /explain` — SHAP 模型解释
所有请求/响应使用 `service/schemas.py` 中的 Pydantic v2 模型。自动生成 OpenAPI 文档（`/docs`, `/redoc`）。

### `ellectric/service/` — 服务层（Phase 4）
桥接 API/CLI/LLM 三层到 pipeline。包含：
- **`schemas.py`**：8 个 Pydantic v2 模型 — ForecastRequest/Response/Metrics, SimulateRequest/Response, BacktestRequest/Response, ExplainRequest/Response, FeatureImportance。使用 `model_validator(mode="after")` 进行跨字段验证，`config.exclude_none` 控制序列化。
- **`handlers.py`**：4 个业务处理器（run_forecast/run_simulate/run_backtest/run_explain）。所有 pipeline 导入均为函数内**延迟导入**，避免循环依赖。支持 3 种 ASSUME 仿真场景（default/summer_peak/wind_high）和 6 种回测策略。

### `ellectric/cli/` — Typer CLI（Phase 4）
5 个子命令：
- `forecast` — 负荷/电价预测
- `simulate` — 市场仿真
- `backtest` — 历史回测
- `explain` — SHAP 模型解释
- `ask` — LLM 自然语言查询（调用 LangChain agent）
支持 `--json` 标志输出 JSON 格式。`rich` 不可用时自动回退到纯文本表格。

### `ellectric/llm/` — LangChain LLM 接口（Phase 4）
DeepSeek Chat API（OpenAI 兼容 SDK）驱动的 LangChain 代理：
- **`agent.py`**：`create_agent_executor()` 创建工具增强代理，`ask_agent()` 提供无状态单次查询接口。
- **`tools.py`**：3 个 `@tool` 函数 — `query_forecast()`、`run_simulation()`、`run_backtest()`。使用模块级共享 `httpx.Client` 调用本地 FastAPI。API 失败时返回错误描述。
- **`chat.py`**：交互式终端对话循环（`python -m ellectric.llm.chat`）。

---

### `ellectric/assume/` — ASSUME 市场仿真（Phase 2）
ASSUME 智能体基电力市场仿真脚本。包含 3 个 YAML 场景配置（default/summer_peak/wind_high），Grafana 仪表板 JSON 模板，以及 2 个 Python 脚本：
- `run_simulation.py` — 主仿真入口（从 handlers.py 通过 subprocess 调用）
- `verify_simulation.py` — 环境可用性验证

### `ellectric/scripts/` — 验证 & 演示脚本
- `run_demo.py`（Phase 4）— 全模型演示：XGBoost 预测、LEAR 电价预测、PPO/SAC/TD3 回测对比、SHAP 解释
- `verify_assume.py`（Phase 2）— ASSUME 框架安装与依赖验证
- `verify_phase3.sh`（Phase 3）— 自动化 Phase 3 验证脚本（RL 训练、回测、SHAP 输出检查）

### `ellectric/notebooks/` — 11 阶段渐进式学习路径
每个 Notebook 建立在前一个之上。按阶段分：
- **Phase 1 (01-05)**：数据获取 → 清洗 → 特征工程 → XGBoost 训练 → 端到端基线
- **Phase 2 (06-08)**：LEAR 电价预测 → 模型对比仪表板 → ASSUME 仿真结果分析
- **Phase 3 (09-11)**：PPO/SAC/TD3 智能体训练 → 多策略回测对比 → SHAP 可解释性分析

### `ellectric/data/` — 本地数据目录
包含原始和处理后的数据文件：负荷数据 Parquet、演示模型文件（joblib/zip）、epftoolbox 标准数据集 CSV、DM/GW 检验结果 JSON、回测可视化 HTML、SHAP 瀑布图 HTML。所有文件通过 `data_loader.py` / `price_loader.py` 加载，不直接在模块中引用路径。

---

## 设计说明

### 无测试目录
项目**没有** `tests/` 目录，也没有 CI/CD 配置。验证策略依赖：
- **Notebook 执行**：每个新功能配套 Jupyter Notebook，手动逐 cell 运行验证
- **验证脚本**：`verify_assume.py`（Phase 2）、`verify_phase3.sh`（Phase 3）
- **演示脚本**：`run_demo.py`（Phase 4）一次性覆盖所有模型
- **训练时评估**：`train_evaluate()` 在训练过程中计算 MAE/RMSE/MAPE/R²

### 三明治架构（Phase 4）
```
API (FastAPI) ─┐
CLI (Typer)   ─┼──→ Service (handlers) ──→ Pipeline → Model
LLM (LangChain) ┘
```
API、CLI、LLM 三层并行调用同一 Service 层，Service 层通过延迟导入桥接到 pipeline，避免循环依赖。

### 数据合约
所有 DataLoader 产出、下游模块消费的 DataFrame 必须包含：
- `timestamp`: datetime64[ns, UTC]
- `load_mw`: float64（MW）
禁止别名：`date`, `datetime`, `load`, `demand`, `power`, `日期`, `用电量`。

### 关键设计模式
- **抽象基类 + 工厂**：DataLoader ABC (OWIDChinaLoader / ChineseDataLoader)、BaseRLAgent ABC (PPO/SAC/TD3)
- **三层特征**：Tier 1（核心）→ Tier 2（中级）→ Tier 3（高级），渐进式学习
- **延迟导入**：handlers.py 中所有 pipeline 导入均为函数内延迟，避免模块级循环依赖
- **可选依赖防护**：非核心包（holidays, shap, epftoolbox）以 `try/except ImportError` 包裹
