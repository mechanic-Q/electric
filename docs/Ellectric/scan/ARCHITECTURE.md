---
author: lmr
created_at: 2026-06-10T00:00:00+08:00
updated_at: 2026-06-10T12:00:00+08:00
---

# ARCHITECTURE: Ellectric (全 4 阶段)

## 技术栈

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Runtime | Python | 3.11+ | 核心执行环境 |
| Data I/O | pandas + pyarrow | 3.0.3 / 22.0.0 | DataFrame 操作，Arrow 后端，Parquet/CSV/Excel 读写 |
| Math | numpy | >=2.0.0 | 数值计算，数组操作 |
| ML | scikit-learn + xgboost | 1.8.0 / 3.2.0 | TimeSeriesSplit 分割，StandardScaler，XGBoost 回归器 |
| Price Forecasting | scikit-learn Lasso | 1.8.0 | LEAR 电价预测 — L1 正则化线性回归自动特征选择 |
| Statistical Tests | epftoolbox (git) | — | Diebold-Mariano + Giacomini-White 检验（可选降级） |
| RL Engine | stable-baselines3 + gymnasium | 2.8.0 / 1.2.3 | PPO/SAC/TD3 交易智能体训练 |
| Market Simulation | ASSUME 0.6.0 | 0.6.0 | 电力市场多智能体仿真（PyTorch 后端） |
| Explainability | shap | >=0.46 | TreeExplainer (XGBoost) + LinearExplainer (LEAR) |
| REST API | FastAPI + uvicorn | 0.136.1+ | 5 个路由（/predict, /simulate, /backtest, /explain, /health） |
| Schema Validation | Pydantic v2 | 2.13.4 | Rust 后端请求/响应校验，model_validator 模式 |
| CLI | typer | — | 5 个子命令（forecast, simulate, backtest, explain, ask） |
| LLM Agent | LangChain + langchain-openai | 1.3.1+ | DeepSeek Chat API 工具调用 agent |
| LLM Backend | DeepSeek API | — | ChatOpenAI 兼容接口，deepseek-v4-flash 模型 |
| HTTP Client | httpx | — | LLM tools 调用本地 FastAPI 的共享客户端 |
| Viz | plotly | 6.7.0 | 交互式图表（负荷叠加、误差直方图、P&L 曲线、SHAP waterfall） |
| Notebooks | jupyter + nbformat | 1.1.1 / >=5.0.0 | 11 个渐进式学习 notebook |
| Data Storage | Parquet / joblib / zip | — | 清洗后数据持久化，模型文件存储 |
| Container | Docker Compose | — | ASSUME Grafana 仪表板 |

## Pipeline 拓扑

所有 12 个 pipeline 模块 + API/Service/CLI/LLM 四层关系：

```
                          Interface Layer (3 路并行)
  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────────────┐
  │   FastAPI REST   │    │    Typer CLI     │    │   LangChain LLM       │
  │  /predict        │    │  forecast        │    │   ask_agent(query)     │
  │  /simulate       │    │  simulate        │    │     → @tool (httpx)    │
  │  /backtest       │    │  backtest        │    │     → DeepSeek API     │
  │  /explain        │    │  explain         │    │     → 自然语言回答      │
  │  /health         │    │  ask             │    │                        │
  └────────┬─────────┘    └────────┬─────────┘    └───────────┬────────────┘
           │                      │                          │
           └──────────────────────┼──────────────────────────┘
                                  │
                          Service Layer (handlers.py)
              run_forecast()  run_simulate()  run_backtest()  run_explain()
                    │              │               │               │
                    │     ┌────────┘               │               │
                    │     │  subprocess→ASSUME      │               │
                    ▼     ▼                         ▼               ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                          Pipeline Layer                                   │
  │                                                                           │
  │  ┌──────────────┐    ┌──────────┐    ┌──────────────┐                   │
  │  │ data_loader  │───▶│ cleaner  │───▶│   features   │                   │
  │  │  OWID/Manual │    │ 清洗校验  │    │  Tier 1→2→3  │                   │
  │  └──────────────┘    └──────────┘    └──────┬───────┘                   │
  │                                              │                           │
  │  ┌──────────────┐    ┌──────────┐           ▼                           │
  │  │ price_loader │    │  price_  │    ┌──────────────┐                   │
  │  │  ZionLuo xlsx│───▶│forecaster│───▶│  forecaster  │                   │
  │  └──────────────┘    │(LEAR)    │    │ (XGBoost)    │                   │
  │                      └────┬─────┘    └──────┬───────┘                   │
  │                           │                 │                           │
  │  ┌──────────────┐        ▼                 ▼                           │
  │  │trading_env   │  ┌──────────────────────────────────┐                │
  │  │(Gymnasium)   │◀─│         backtester.py            │                │
  │  │  动作/观测/奖励│  │  BacktestRunner + 3 基线策略     │                │
  │  └──────┬───────┘  │  replay() + compare()            │                │
  │         │          └───────────────┬──────────────────┘                │
  │         ▼                          │                                   │
  │  ┌──────────────┐                 │                                   │
  │  │ rl_trainer   │◀────────────────┘                                   │
  │  │ PPO/SAC/TD3  │                                                     │
  │  └──────────────┘                                                     │
  │         │                                                             │
  │         ▼                                                             │
  │  ┌──────────────┐    ┌──────────────────────┐                        │
  │  │shap_explainer│    │ statistical_tests    │                        │
  │  │Tree+Linear   │    │ DM + GW (epftoolbox) │                        │
  │  └──────────────┘    └──────────────────────┘                        │
  └──────────────────────────────────────────────────────────────────────────┘
```

## 数据流

```
OWID GitHub (urllib raw CSV)          ZionLuo Excel (price_data.xlsx)
         │                                        │
         ▼                                        ▼
   OWIDChinaLoader                        PriceDataLoader
   流式解析 ~25MB                         7 列: price_da, price_rt,
   年级 TWh → 日均 MW                          load_mw, wind_mw, solar_mw,
   ISO-3166 过滤 CHN                               tie_line_mw
         │                                        │
         └────────────┬───────────────────────────┘
                      │
                      ▼
         DataFrame[timestamp, load_mw]
              [+ price_da, wind_mw, solar_mw]
                      │
                      ▼
                clean_data(df)
         缺失值 ffill/bfill  |  IQR 异常值报告
               UTC 时区标准化
                      │
             ┌────────┴────────┐
             ▼                 ▼
   FeatureEngineer       LEAR add_price_features
   Tier 1 → 2 → 3        Tier 1 → 2 → 3
   (负荷特征)              (电价特征)
             │                 │
             ▼                 ▼
  XGBoostForecaster      LEARForecaster
  TimeSeriesSplit        Lasso L1 正则化
  StandardScaler         自动特征选择
  5-fold CV              alpha 正则参数
             │                 │
             ▼                 ▼
  {MAE,RMSE,MAPE}        {MAE,RMSE,MAPE}
  + 预测 + Plotly        + 预测 + Plotly
             │                 │
             ▼                 ▼
       ┌──────────────────────────┐
       │     BacktestRunner       │
       │  基线: persistence/mean/oracle │
       │  RL:  PPO/SAC/TD3       │
       │  replay() + compare()   │
       └────────────┬─────────────┘
                    │
                    ▼
          ElectricityMarketEnv
          Box(0,1,(24,)) 动作空间
          Dict 观测空间 (5 keys)
          3 种奖励函数 (RewardRegistry)
                    │
                    ▼
            SHAP Explainer
          TreeExplainer (XGBoost)
          LinearExplainer (LEAR)
          waterfall + 特征重要性排名
                    │
                    ▼
         FastAPI + CLI + LLM Agent
```

## 模块职责

### Pipeline 模块 (12 个)

#### 1. `data_loader.py` — 数据接入层 (Phase 1)

**抽象基类 + 工厂模式：**

```
DataLoader (ABC)
  load_data(start, end) → DataFrame[timestamp, load_mw]
  ├── OWIDChinaLoader    — 自动拉取 OWID GitHub raw CSV
  │                      — 年级 TWh → 日均 MW (_twh_to_daily_mw)
  └── ChineseDataLoader  — 加载本地 CSV/Excel/Parquet
                         — 列名标准化 (_standardize_columns): 中英文 → timestamp/load_mw
                         — 强制 UTC 时区

create_loader(source="owid"|"manual"|"file", **kwargs) → DataLoader
```

**数据合约:** `timestamp: datetime64[ns, UTC]`, `load_mw: float64`, 禁止别名。

#### 2. `cleaner.py` — 数据清洗 (Phase 1)

```
clean_data(df) → df
  列验证 → 缺失值 ffill+bfill → IQR 异常值检测（仅报告不删除）→ UTC 时区标准化

validate_schema(df) → dict
  列存在性/类型/时区检查 → {valid, issues, stats}
```

设计原则: 异常值仅报告不删除 — 电力负荷尖峰是有效信号。

#### 3. `features.py` — 特征工程 (Phase 1)

```
FeatureEngineer
  add_tier1(df) → df   — hour, day_of_week, month, is_weekend, lag_24h
  add_tier2(df) → df   — is_holiday, lag_168h
  add_tier3(df) → df   — rolling_mean_24h, rolling_std_24h, hour_sin, hour_cos
  get_feature_columns(tier) → list[str]

prepare_features(df, tier="tier3") → df   — 一键执行全部三级特征
```

循环编码 (hour_sin/cos): 将 0-23 映射到单位圆，保持时间邻近性。

#### 4. `forecaster.py` — 负荷预测 (Phase 1)

```
模块级函数: persistence_forecast(), calculate_pnl(), plot_pnl()

XGBoostForecaster
  __init__(n_splits=5, gap=24, **xgb_kwargs)
  train_evaluate(X, y) → dict   — 5-fold CV + MAE/RMSE/MAPE/R²
  predict(X) → np.ndarray
```

防泄漏: TimeSeriesSplit(gap=24), StandardScaler fit on train only。

#### 5. `price_loader.py` — 电价数据加载 (Phase 2)

独立设计（组合优于继承），不继承 DataLoader ABC。
数据列: timestamp, price_da, price_rt, load_mw, wind_mw, solar_mw, tie_line_mw。
数据源: ZionLuo/Electricity-Price-Forecasting GitHub。

#### 6. `price_forecaster.py` — LEAR 电价预测 (Phase 2)

```
LEARForecaster
  __init__(alpha=0.01, ...)            — sklearn Lasso
  add_price_features(df, tier) → df   — 3 级电价特征
  train_evaluate(df, tier) → dict      — 时序 CV + 指标
  save_model/load_model                — joblib 持久化
```

选 Lasso 而非 XGBoost: 系数=边际影响，可解释性强；LEAR 常达到或超越复杂深度模型精度。

#### 7. `trading_env.py` — 交易环境 (Phase 3)

```
ElectricityMarketEnv(gym.Env)
  观测: Dict {load_forecast, price_forecast, time_features, history, account}
  动作: Box(0, 1, (24,)) — 归一化投标量
  出清: cleared = min(bid, actual_load)  — 价格接受者
  奖励: 3 种函数通过 RewardRegistry 注册/查询
```

#### 8. `rl_trainer.py` — RL 训练框架 (Phase 3)

```
BaseRLAgent (ABC)
  train(total_timesteps) → dict
  predict(observation) → np.ndarray
  save/load_model
  ├── PPOAgent — on-policy, 稳定可靠首选
  ├── SACAgent — off-policy, 最大熵, 连续动作最优
  └── TD3Agent — off-policy, 双 Q 网络, 高维备选

RLAgentFactory.create("ppo"|"sac"|"td3", env) → BaseRLAgent
RLAgentFactory.load(algorithm, path) → BaseRLAgent
```

#### 9. `backtester.py` — 回测引擎 (Phase 3)

```
BacktestRunner
  replay(model, load, price, start, end) → DataFrame
  compare(results_dict) → DataFrame   — 多策略对比表

基线策略: baseline_persistence (t-24h), baseline_mean (168h), oracle (理论上限)
```

自动对齐负荷/价格数据时间范围；计算夏普比率、累计 P&L。

#### 10. `shap_explainer.py` — SHAP 可解释性 (Phase 3)

```
explain_xgboost_sample(model, X, sample_idx) → plotly Figure   — TreeExplainer
explain_lear_sample(model, X, sample_idx) → plotly Figure       — LinearExplainer
feature_importance_ranking(models, feature_cols) → DataFrame     — 跨模型排名
```

shap 可选依赖，通过 `_get_shap()` 惰性导入。

#### 11. `statistical_tests.py` — DM/GW 统计检验 (Phase 2)

```
Diebold-Mariano 检验: 两模型预测精度是否显著不同
Giacomini-White 检验: 条件预测比较

run_statistical_tests() → {dm: {dm_stat, p_value, significant},
                           gw: {gw_stat, p_value, significant}}
```

epftoolbox 可选依赖；缺失时模拟降级。

#### 12. `__init__.py` — 包标记

包标记，导出 LEARForecaster 等关键类。

### 接口层 (Phase 4)

#### FastAPI (`api/server.py`)

5 个路由: `/health` (GET), `/predict`, `/simulate`, `/backtest`, `/explain` (POST)。
各路由直接委托 Service 层 handler。

#### Service 层 (`service/`)

- `schemas.py`: 8 个 Pydantic v2 模型，`model_validator(mode="after")` 跨字段校验。
- `handlers.py`: 4 个业务函数 — `run_forecast()`, `run_simulate()`, `run_backtest()`, `run_explain()`。
  所有 pipeline 导入为函数内延迟导入，避免模块级循环依赖。
  被 API/CLI/LLM 三层共同调用。

#### CLI (`cli/main.py`)

5 个 Typer 子命令: forecast, simulate, backtest, explain, ask。
rich 库表格输出，`--json` 标志切换 JSON 模式。

#### LLM 接口 (`llm/`)

- `agent.py`: `create_agent_executor()` + `ask_agent(query)` — LangChain + DeepSeek Chat API。
- `tools.py`: 3 个 `@tool` — `query_forecast()`, `run_simulation()`, `run_backtest()`，通过共享 `httpx.Client` 调用本地 FastAPI。
- `chat.py`: 终端交互式对话入口。

## 关键设计模式

| 模式 | 位置 | 说明 |
|------|------|------|
| **ABC + Factory** | `data_loader.py`, `rl_trainer.py` | 抽象基类定义统一接口，工厂函数按参数创建具体实例 |
| **数据合约** | 全 pipeline | `REQUIRED_COLUMNS = {"timestamp", "load_mw"}` — 所有模块依赖同一份 schema |
| **3-Tier 特征** | `features.py`, `price_forecaster.py` | 渐进式 T1→T2→T3，Jupyter notebooks 逐步引入 |
| **延迟导入** | `service/handlers.py` | 所有 pipeline import 在函数内部执行，规避模块级循环依赖 |
| **可选依赖防护** | `shap_explainer.py`, `statistical_tests.py` | try/except ImportError 包裹非核心包，缺失时降级 |
| **三明治架构** | API → Service → Pipeline | API/CLI/LLM 三层并行调用同一 Service 层，无重复逻辑 |
| **组合优于继承** | `price_loader.py` | PriceDataLoader 不强行继承 DataLoader ABC，保持接口一致但不共享 ABC 链 |
| **统一接口约定** | 所有预测器 | train_evaluate/predict/save/load 接口一致 |
| **时序安全性** | `forecaster.py` | TimeSeriesSplit(gap=24)，Scaler 仅在训练集 fit，杜绝未来信息泄露 |

## 文件布局

```
ellectric/
├── pipeline/                       # Python 包 (12 模块, ~2,400 loc)
│   ├── __init__.py                 # 包标记
│   ├── data_loader.py              # 390 loc — DataLoader ABC + OWID/Chinese loaders
│   ├── cleaner.py                  # 178 loc — clean_data, validate_schema
│   ├── features.py                 # 224 loc — FeatureEngineer, prepare_features
│   ├── forecaster.py               # 431 loc — XGBoostForecaster + persistence
│   ├── price_loader.py             # 103 loc — PriceDataLoader
│   ├── price_forecaster.py         # 364 loc — LEARForecaster (Lasso)
│   ├── backtester.py               # 322 loc — BacktestRunner, 基线策略
│   ├── trading_env.py              # 277 loc — ElectricityMarketEnv (Gymnasium)
│   ├── rl_trainer.py               # 206 loc — BaseRLAgent ABC + PPO/SAC/TD3
│   ├── shap_explainer.py           # 230 loc — TreeExplainer + LinearExplainer
│   └── statistical_tests.py        # 197 loc — DM/GW 检验
├── api/                            # Phase 4: FastAPI
│   └── server.py                   # 121 loc — 5 路由
├── service/                        # Phase 4: 业务处理层
│   ├── schemas.py                  # 268 loc — Pydantic v2 模型
│   └── handlers.py                 # 380 loc — 4 个 handler + 延迟导入
├── cli/                            # Phase 4: Typer CLI
│   └── main.py                     # 312 loc — 5 子命令 + rich 输出
├── llm/                            # Phase 4: LangChain LLM 接口
│   ├── agent.py                    # 97 loc — create_agent_executor, ask_agent
│   ├── tools.py                    # 141 loc — 3 个 @tool (httpx → FastAPI)
│   └── chat.py                     # 41 loc — 终端交互式对话
├── assume/                         # Phase 2-3: ASSUME 仿真
│   ├── run_simulation.py           # 仿真入口
│   ├── verify_simulation.py        # 仿真验证
│   ├── configs/                    # YAML 场景配置
│   └── grafana/                    # Grafana 仪表板
├── notebooks/                      # 11 个渐进式 Jupyter notebooks
│   ├── 01_data_ingestion.ipynb     # Phase 1
│   ├── 02_data_cleaning.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_load_forecasting.ipynb
│   ├── 05_end_to_end_baseline.ipynb
│   ├── 06_price_forecasting.ipynb  # Phase 2
│   ├── 07_model_comparison.ipynb
│   ├── 08_assume_results.ipynb
│   ├── 09_rl_trading_agent.ipynb   # Phase 3
│   ├── 10_multi_agent_backtest.ipynb
│   └── 11_model_explainability.ipynb
├── scripts/                        # 验证/演示脚本
│   ├── run_demo.py
│   ├── verify_assume.py
│   └── verify_phase3.sh
├── data/                           # 数据文件
│   ├── electricity_load_hourly.parquet
│   ├── price_data.xlsx
│   ├── demo_*.joblib / demo_*.zip  # 演示模型
│   └── *.parquet                   # 回测测试数据
├── requirements.txt
├── setup.sh
└── docker-compose.yml              # Grafana (ASSUME)
```

## 阶段边界

| Phase | 模块 | 核心技能 | 数据源 |
|-------|------|----------|--------|
| Phase 1 | data_loader, cleaner, features, forecaster | OWID 时序数据管道 + XGBoost 预测 | OWID GitHub |
| Phase 2 | price_loader, price_forecaster, statistical_tests + assume/ | 电价 LEAR 预测 + 市场仿真 | ZionLuo Excel, ASSUME |
| Phase 3 | trading_env, rl_trainer, backtester, shap_explainer | RL 交易 + 回测 + 可解释性 | Phase 1-2 产出 |
| Phase 4 | api/, service/, cli/, llm/ | FastAPI + CLI + LLM 接口 | 上述所有层 |
