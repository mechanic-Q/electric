# 架构调研

**领域:** AI驱动的电力交易学习平台
**调研日期:** 2026-05-20
**置信度:** HIGH

## 标准架构

### 系统总览

系统遵循**分层管道架构**，各层之间有清晰的数据契约边界。每一层均可独立学习、测试和替换——与 PROJECT.md 中的四个学习阶段路线图相匹配。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     第5层：接口层                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────────┐  │
│  │  FastAPI      │  │  CLI         │  │  LLM 聊天机器人                │  │
│  │  (REST API)   │  │  (assume +   │  │  (LangChain + OpenAI/Ollama)  │  │
│  │               │  │   custom)    │  │                               │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────┬───────────────┘  │
│         │                 │                           │                  │
├─────────┴─────────────────┴───────────────────────────┴──────────────────┤
│                     第4层：智能体/交易层                                    │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    交易编排器                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │    │
│  │  │ RL Agent      │  │ Rule-Based   │  │ Backtesting Engine   │    │    │
│  │  │ (TD3/SAC/PPO) │  │ Strategies   │  │ (hist replay)        │    │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘    │    │
│  │         │                 │                      │                │    │
│  │         └─────────┬───────┴──────────────────────┘                │    │
│  │                   │  投标决策 (价格, 量, 时间)                      │    │
│  └───────────────────┼──────────────────────────────────────────────┘    │
│                      │                                                    │
├──────────────────────┼────────────────────────────────────────────────────┤
│                      ↓                                                    │
│               第3层：市场仿真层 (ASSUME)                                    │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    World (编排器)                                   │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │    │
│  │  │ Market Op.   │  │ Day-Ahead    │  │ Real-Time Market     │    │    │
│  │  │ (coordinator)│  │ Market       │  │ (balancing)          │    │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘    │    │
│  │         │                 │                      │                │    │
│  │         └─────────┬───────┴──────────────────────┘                │    │
│  │                   ↓  出清 (uniform / pay-as-bid / nodal)          │    │
│  │  ┌──────────────────────────────────────────────────────────┐    │    │
│  │  │  Unit Operators (管理投资组合)                              │    │    │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │    │    │
│  │  │  │PowerPlant│  │ Storage  │  │ Demand   │  │ Renewable│ │    │    │
│  │  │  │ Unit     │  │ Unit     │  │ Unit     │  │ Unit     │ │    │    │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │    │    │
│  │  └──────────────────────────────────────────────────────────┘    │    │
│  │  输出: 出清价格, 调度, 利润, 市场指标                               │    │
│  └───────────────────────────┬──────────────────────────────────────┘    │
│                              │  需要: 负荷预测, 电价预测,                  │
│                              │  可再生能源预测, 边际成本                    │
├──────────────────────────────┼────────────────────────────────────────────┤
│                              ↑                                            │
│                  第2层：预测层                                              │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    预测管道                                        │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │    │
│  │  │ Load Forecast │  │ Price Forecast│  │ Renewable Gen.      │    │    │
│  │  │ (XGBoost/     │  │ (LEAR/DNN/   │  │ Forecast            │    │    │
│  │  │  OpenSTEF)    │  │  epftoolbox)  │  │ (meteo→power model) │    │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘    │    │
│  │         │                 │                      │                │    │
│  │         └─────────┬───────┴──────────────────────┘                │    │
│  │                   ↓  特征工程 + 模型训练                            │    │
│  │  ┌──────────────────────────────────────────────────────────┐    │    │
│  │  │  Feature Store (日历, 天气, 滞后特征)                       │    │    │
│  │  └──────────────────────────────────────────────────────────┘    │    │
│  └───────────────────────────┬──────────────────────────────────────┘    │
│                              │  需要: 清洗后的时序数据                     │
├──────────────────────────────┼────────────────────────────────────────────┤
│                              ↑                                            │
│                    第1层：数据层                                            │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    数据管道                                        │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │    │
│  │  │ Data Ingest  │  │ Data Clean   │  │ Feature Engineering  │    │    │
│  │  │ (PUDL/IEA/   │  │ (enda/       │  │ (时间/日历/           │    │    │
│  │  │  CSV/API)    │  │  pandas)     │  │  天气特征)            │    │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘    │    │
│  │         │                 │                      │                │    │
│  │         └─────────┬───────┴──────────────────────┘                │    │
│  │                   ↓                                               │    │
│  │  ┌──────────────────────────────────────────────────────────┐    │    │
│  │  │  Data Store (SQLite/Parquet 文件, DuckDB 查询)             │    │    │
│  │  │  表: load, price, generation, weather, plant_metadata     │    │    │
│  │  └──────────────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 职责 | 典型实现 | 学习阶段 |
|-----------|----------------|------------------------|----------------|
| **Data Ingest** | 从 PUDL、IEA、公开 API 拉取原始数据；本地存储 | Python 脚本, `pudl` 包, `pandas` | 阶段 1 |
| **Data Cleaner** | 处理缺失值，重采样到统一频率，验证数据质量 | `enda` (时序), `pandas` | 阶段 1 |
| **Feature Store** | 构造日期时间特征 (小时, 星期几, 节假日), 天气特征, 滞后特征 | `enda` 特征工程, `pandas` | 阶段 1-2 |
| **Data Store** | 以可查询格式持久化清洗后的时序数据 | SQLite (遵循 PUDL 模式) 或 DuckDB + Parquet | 阶段 1 |
| **Load Forecaster** | 以15分钟/1小时分辨率预测未来电力需求 (MW) | XGBoost (阶段 1), OpenSTEF (阶段 2) | 阶段 1-2 |
| **Price Forecaster** | 预测日前电价以优化投标 | LEAR 模型, epftoolbox DNN | 阶段 2 |
| **Renewable Forecaster** | 从气象预报预测风电/光伏发电 | 物理模型 (风速→功率) 或 ML | 阶段 2 |
| **World (ASSUME)** | 编排仿真：管理时钟，协调市场 + 智能体 | `assume.World` 配合 mango agent 框架 | 阶段 2-3 |
| **Market Operator** | 运营一个或多个市场，处理出清后 (再调度) | `assume.markets.MarketRole` | 阶段 2 |
| **Day-Ahead Market** | 收集投标，运行出清算法的出清算法，发布价格/调度 | `assume.markets` 出清算法 | 阶段 2 |
| **Real-Time Market** | 处理不平衡，平衡能量定价 | ASSUME balancing market (开发中) | 阶段 3 |
| **Unit Operator** | 管理投资组合：聚合机组约束，提交协调投标 | `assume.UnitOperator` | 阶段 3 |
| **Power Plant Unit** | 带技术约束的火电机组 (爬坡、最小/最大、效率) | `assume.units.PowerPlant` | 阶段 2 |
| **Storage Unit** | 带 SoC、充放电限制的储能/抽水蓄能 | `assume.units.Storage` | 阶段 3 |
| **Renewable Unit** | 带天气依赖可用性的风电/光伏 | `assume.units` + 自定义预测器 | 阶段 3 |
| **Demand Unit** | 固定或柔性负荷 | `assume.units.Demand`, `DSMFlex` | 阶段 2 |
| **Bidding Strategy** | 映射状态 → 投标 (价格, 量)。可插拔: 规则型、优化型或 RL | `assume.strategies.*` | 阶段 2-3 |
| **RL Agent** | 通过 DRL 学习投标策略 (TD3, SAC, PPO) | `assume.strategies.learning_strategies` | 阶段 3 |
| **Backtesting Engine** | 重放历史数据，对照历史市场评估策略 | 围绕 ASSUME 的自定义包装器或独立模块 | 阶段 3 |
| **Trading Orchestrator** | 组合预测 + 仿真 → 执行回测 → 报告指标 | 自定义 Python 模块 | 阶段 3-4 |
| **FastAPI Server** | 暴露 REST API：运行预测，触发仿真，查询结果 | FastAPI + Pydantic schemas | 阶段 4 |
| **CLI** | 命令行界面：运行管道、回测、查看数据 | `assume` CLI + 自定义 Click/Typer 命令 | 所有阶段 |
| **LLM Chatbot** | 自然语言界面："预测明天的负荷" → 运行管道 | LangChain + OpenAI/Ollama + function calling | 阶段 4 |

## 推荐的项目结构

```
ellectric/
├── data/                          # 数据层 (阶段 1)
│   ├── raw/                       # 下载的原始数据 (PUDL SQLite, IEA CSV)
│   ├── processed/                 # 清洗后的 Parquet 文件
│   ├── external/                  # 天气数据, 节假日日历
│   └── README.md                  # 数据字典
│
├── src/
│   ├── data_pipeline/             # 第1层: 数据接入与预处理
│   │   ├── __init__.py
│   │   ├── ingest.py             # 从 PUDL, IEA, 本地 CSV 拉取
│   │   ├── clean.py              # 缺失值, 重采样, 验证
│   │   ├── features.py           # 日历特征, 滞后特征, 天气
│   │   └── store.py              # 写入 Parquet, 读取工具
│   │
│   ├── prediction/                # 第2层: 预测模型
│   │   ├── __init__.py
│   │   ├── load_forecast.py      # XGBoost 基线 + OpenSTEF 集成
│   │   ├── price_forecast.py     # 通过 epftoolbox 的 LEAR 模型
│   │   ├── renewable_forecast.py # 风电/光伏发电预测
│   │   └── evaluation.py         # MAE, RMSE, sMAPE, MASE 指标
│   │
│   ├── simulation/                # 第3层: 市场仿真 (ASSUME 包装器)
│   │   ├── __init__.py
│   │   ├── config/                # ASSUME 场景 YAML/CSV 配置
│   │   │   ├── market_config.yaml
│   │   │   ├── power_plants.csv
│   │   │   ├── demand_units.csv
│   │   │   └── renewables.csv
│   │   ├── scenarios/             # 预构建的学习场景
│   │   │   ├── basic_2unit/       # 2机组市场 (热身)
│   │   │   ├── multi_agent/       # 多个发电机 + 储能
│   │   │   └── renewable_pen/     # 高可再生能源渗透率
│   │   ├── runner.py             # 启动 ASSUME 仿真
│   │   └── results.py            # 解析仿真输出
│   │
│   ├── agents/                    # 第4层: 交易策略与 RL
│   │   ├── __init__.py
│   │   ├── strategies/            # 自定义投标策略
│   │   │   ├── base.py
│   │   │   ├── marginal_cost.py   # 按边际成本投标
│   │   │   ├── markup.py          # 成本 + 加成
│   │   │   └── prediction_based.py # 使用第2层预测
│   │   ├── rl/                    # RL agent 包装器
│   │   │   ├── env.py            # 兼容 Gym 的交易环境
│   │   │   ├── agent.py          # DRL agent (TD3/SAC via stable-baselines3)
│   │   │   └── reward.py         # 自定义奖励函数
│   │   └── backtest.py           # 历史回测引擎
│   │
│   ├── interface/                 # 第5层: API, CLI, 聊天机器人
│   │   ├── __init__.py
│   │   ├── api/                   # FastAPI 应用
│   │   │   ├── main.py           # 应用入口
│   │   │   ├── routes/            # API 端点
│   │   │   │   ├── data.py       # /data/* 端点
│   │   │   │   ├── prediction.py  # /predict/* 端点
│   │   │   │   ├── simulation.py # /simulate/* 端点
│   │   │   │   └── backtest.py   # /backtest/* 端点
│   │   │   └── schemas.py        # Pydantic 模型
│   │   ├── cli/                   # CLI 命令
│   │   │   ├── main.py           # Typer/Click CLI 入口
│   │   │   ├── data_cmd.py
│   │   │   ├── predict_cmd.py
│   │   │   └── simulate_cmd.py
│   │   └── chatbot/               # LLM 聊天机器人
│   │       ├── agent.py          # LangChain agent 带工具
│   │       ├── tools.py          # 功能工具 (预测, 仿真, 查询)
│   │       └── prompts.py        # 系统提示词
│   │
│   └── shared/                    # 共享工具
│       ├── __init__.py
│       ├── config.py             # 项目配置 (路径, 参数)
│       ├── types.py              # 共享数据类型/dataclasses
│       └── visualization.py      # 绘图工具 (matplotlib/plotly)
│
├── notebooks/                     # Jupyter notebooks 用于学习
│   ├── 01_data_exploration.ipynb
│   ├── 02_load_forecasting_xgboost.ipynb
│   ├── 03_price_forecasting.ipynb
│   ├── 04_assume_intro.ipynb
│   ├── 05_bidding_strategies.ipynb
│   ├── 06_rl_trading.ipynb
│   └── 07_full_pipeline.ipynb
│
├── tests/
│   ├── test_data_pipeline/
│   ├── test_prediction/
│   ├── test_agents/
│   └── test_interface/
│
├── requirements.txt               # 核心依赖
├── requirements-dev.txt           # 开发依赖 (pytest, black 等)
└── README.md
```

### 结构理由

- **`data/`:** 与 `src/` 分离 —— 大型二进制文件 (SQLite, Parquet) 不纳入 git 跟踪。`.gitignore` 排除 `data/raw/` 和 `data/processed/`，仅保留小样本。
- **`src/data_pipeline/`:** 隔离的接入 → 清洗 → 特征管道。可在其他层存在之前独立运行。通过文件路径产出下游层消费的 Parquet 文件。
- **`src/prediction/`:** 每个预测器是独立模块。可独立训练/评估。产出 CSV/Parquet 预测输出。预测器共享 `predict(horizon) → pd.DataFrame` 通用接口。
- **`src/simulation/`:** 包装 ASSUME (不重新发明)。配置驱动 —— YAML/CSV 文件定义世界。`runner.py` 是薄启动器。场景文件夹自包含 (可在学习者之间移植)。
- **`src/agents/`:** 策略代码与仿真引擎分离。策略消费预测输出并产出投标。RL agent 使用兼容 Gym 的环境包装器，可使用 ASSUME 或轻量仿真器。
- **`src/interface/`:** 三种访问模式 (API, CLI, Chatbot) —— 都调用相同的底层服务层。Chatbot 工具是 CLI/API 服务的 function-calling 包装器。
- **`notebooks/`:** 主要学习界面。每个 notebook 端到端地讲解一个概念，带有说明文字和可执行代码。
- **`src/shared/`:** 避免循环依赖。所有层从此处导入共享类型和配置。

## 架构模式

### 模式 1: 基于 DataFrame 的数据契约

**是什么:** 每层通过具有明确定义列 schema 的 Pandas DataFrame (或基于文件的 Parquet) 与下一层通信。层之间没有直接函数调用 —— 数据被物化并传递。

**何时使用:** 每个层间边界。

**权衡:**
- **优点:** 每层可独立调试 —— 检查中间 DataFrame。
- **优点:** 学习者可以在不触及其他层的情况下替换某一层 (例如，将 XGBoost 换成 LSTM)。
- **缺点:** 文件 I/O 开销。通过使用 Parquet (快速、压缩) 和在 notebook 中使用内存 DataFrame 传递来缓解。

**示例:**
```python
# 第1层 → 第2层 契约: cleaned_load.csv
# 列: timestamp (UTC), load_mw (float), region (str)
# 频率: 每小时

# 第2层 → 第3层 契约: forecast_24h.csv
# 列: timestamp, predicted_load_mw, predicted_price_eur_mwh, 
#           predicted_wind_mw, predicted_solar_mw
# 频率: 每小时, 预测期: 24h

# 第3层 → 第4层 契约: market_results.csv
# 列: timestamp, cleared_price, dispatched_mw, unit_id, profit_eur
```

### 模式 2: 投标策略模式 (Strategy Pattern)

**是什么:** 投标策略实现通用接口 (`calculate_bids(state) → List[Order]`)。仿真引擎调用此接口 —— 它不关心策略是基于规则的、基于优化的还是基于 RL 的。

**何时使用:** 智能体层。ASSUME 已在内部实现了此模式 —— 我们的包装器遵循相同的接口。

**权衡:**
- **优点:** 学习者从简单的边际成本投标开始，然后升级到 RL，无需更改仿真代码。
- **优点:** 回测可以用相同的市场数据对不同策略进行重放。
- **缺点:** 状态表示必须标准化。某些策略需要比其他策略更多的状态 (RL 需要完整的观测空间)。

**示例:**
```python
# ASSUME 已使用此模式:
class BiddingStrategy(ABC):
    @abstractmethod
    def calculate_bids(self, unit, market_config, forecaster) -> List[Order]:
        ...

# 基于规则的 (阶段 2 - 热身):
class MarginalCostStrategy(BiddingStrategy):
    def calculate_bids(self, unit, market_config, forecaster):
        mc = unit.calculate_marginal_cost()
        max_power = unit.calculate_min_max_power()[1]
        return [Order(price=mc * 1.1, volume=max_power)]

# 基于预测的 (阶段 3):
class ForecastBasedStrategy(BiddingStrategy):
    def __init__(self, price_forecast_df):
        self.forecast = price_forecast_df
    
    def calculate_bids(self, unit, market_config, forecaster):
        predicted_price = self.forecast.loc[timestamp, 'price']
        mc = unit.calculate_marginal_cost()
        # 仅在预测价格 > 边际成本时投标
        if predicted_price > mc:
            return [Order(price=predicted_price * 0.95, volume=max_power)]
        return []
```

### 模式 3: 带检查点的管道

**是什么:** 长时间运行的管道 (数据 → 预测 → 仿真) 将中间结果保存到磁盘。每个阶段检查是否存在已有输出，如果已计算则跳过。

**何时使用:** 数据管道和回测。

**权衡:**
- **优点:** 更快的迭代 —— 只更改最后阶段。
- **优点:** 可复现 —— 每个检查点是有版本的产物。
- **缺点:** 缓存失效复杂性。通过对输入配置进行内容哈希来缓解。

**示例:**
```python
# 在 backtest.py 中:
def run_backtest(config: BacktestConfig):
    # 阶段 1: 加载/缓存数据
    data = load_or_compute("cache/cleaned_data.parquet", 
                           lambda: ingest_and_clean(config.data_start, config.data_end))
    
    # 阶段 2: 生成预测
    forecasts = load_or_compute("cache/forecasts.parquet",
                                lambda: generate_forecasts(data, config.model))
    
    # 阶段 3: 运行仿真
    results = load_or_compute("cache/results.parquet",
                              lambda: run_assume_simulation(forecasts, config.scenario))
    
    return results
```

### 模式 4: 配置驱动的仿真

**是什么:** ASSUME 仿真完全由 YAML/CSV 配置文件定义。测试不同的市场设计、机组组合或策略无需代码更改。

**何时使用:** 仿真层。实现快速实验。

**示例:**
```yaml
# config/market_config.yaml
markets:
  - name: EOM
    start: "2019-01-01 00:00"
    end: "2019-01-07 00:00"
    time_step: 1h
    market_mechanism: pay_as_clear
    clearing_algorithm: complex_clearing
    products:
      - type: energy
        duration: 1h
        count: 24
```

## 数据流

### 完整管道流程

```
[公开数据源]
    │  PUDL, IEA, 天气 APIs
    ↓
┌───────────────────────────────────────┐
│ 第1层: 数据                             │
│                                         │
│ PUDL SQLite / IEA CSV                   │
│     → enda/pandas: 重采样, 填补缺失     │
│     → 特征工程 (日历,                    │
│       天气, 滞后)                        │
│     → 存储: Parquet 文件                │
│  输出: cleaned_load.parquet,            │
│        cleaned_price.parquet,           │
│        weather_features.parquet         │
└───────────────┬───────────────────────┘
                │
                ↓
┌───────────────────────────────────────┐
│ 第2层: 预测                             │
│                                         │
│ 负荷预测器:                              │
│   特征 → XGBoost/OpenSTEF → 负荷        │
│ 电价预测器:                              │
│   特征 → LEAR/DNN → 价格                │
│ 可再生能源预测器:                         │
│   天气 → 物理/ML → 风电, 光伏            │
│                                         │
│  输出: forecast_24h.parquet 包含        │
│   列: [timestamp, load_mw,              │
│    price_eur_mwh, wind_mw, solar_mw]   │
└───────────────┬───────────────────────┘
                │
                ↓
┌───────────────────────────────────────┐
│ 第3层: 市场仿真 (ASSUME)                │
│                                         │
│ World.setup(config.yaml)                │
│   → 创建市场, 机组, 运营者               │
│   → Forecaster.init_forecasts()         │
│     → 读取 forecast_24h.parquet         │
│ World.run()                             │
│   → 时钟推进 (每小时)                    │
│   → 市场开启 → 智能体投标 → 出清        │
│   → 结果存储 (TimescaleDB/CSV)          │
│                                         │
│  输出: results.csv 包含列:              │
│   [timestamp, market, unit_id,          │
│    bid_price, bid_volume, cleared_price,│
│    dispatched_mw, profit_eur]           │
└───────────────┬───────────────────────┘
                │
                ↓
┌───────────────────────────────────────┐
│ 第4层: 智能体 / 回测                    │
│                                         │
│ 回测引擎:                                │
│   → 遍历历史时间窗口                     │
│   → 每个窗口:                            │
│       1. 从数据生成预测                   │
│       2. 用策略运行 ASSUME               │
│       3. 收集指标 (PnL, Sharpe,         │
│          胜率)                           │
│   → 比较策略                             │
│                                         │
│ RL 训练循环:                            │
│   → 环境 = ASSUME 包装器                 │
│   → 智能体观测状态 (预测,                 │
│     投资组合, 市场历史)                   │
│   → 动作 = 投标 (价格, 量)              │
│   → 奖励 = 利润或风险调整后的             │
│   → 通过 TD3/SAC/PPO 训练              │
└───────────────┬───────────────────────┘
                │
                ↓
┌───────────────────────────────────────┐
│ 第5层: 接口                             │
│                                         │
│ FastAPI:                                │
│   POST /predict → 返回预测              │
│   POST /simulate → 运行 ASSUME → JSON  │
│   GET  /results/{run_id} → 指标        │
│                                         │
│ CLI:                                    │
│   $ ellectric predict --horizon 24h    │
│   $ ellectric simulate --scenario basic│
│   $ ellectric backtest --strategy rl   │
│                                         │
│ LLM Chatbot:                            │
│   用户: "明天负荷是多少?"                │
│   → 工具调用: run_load_forecast()       │
│   → 响应: "预测负荷: 450MW               │
│     峰值 18:00, 最低 280MW 04:00"       │
└───────────────────────────────────────┘
```

### 关键数据契约 Schema

**清洗后数据 Schema (第1层 → 第2层):**
| 列 | Type | 描述 |
|--------|------|-------------|
| `timestamp` | datetime64[ns, UTC] | 小时索引 |
| `load_mw` | float64 | 实际系统负荷 |
| `price_eur_mwh` | float64 | 日前出清价格 |
| `wind_mw` | float64 | 实际风电发电 |
| `solar_mw` | float64 | 实际光伏发电 |
| `temp_c` | float64 | 温度 |
| `hour` | int8 | 0-23 |
| `day_of_week` | int8 | 0=周一 |
| `is_holiday` | bool | 节假日标志 |
| `month` | int8 | 1-12 |

**预测 Schema (第2层 → 第3层):**
| 列 | Type | 描述 |
|--------|------|-------------|
| `timestamp` | datetime64[ns, UTC] | 预测目标小时 |
| `predicted_load_mw` | float64 | 负荷预测 |
| `predicted_price_eur_mwh` | float64 | 电价预测 |
| `predicted_wind_mw` | float64 | 风电发电预测 |
| `predicted_solar_mw` | float64 | 光伏发电预测 |
| `forecast_created_at` | datetime64[ns, UTC] | 预测生成时间 |

**市场结果 Schema (第3层 → 第4层):**
| 列 | Type | 描述 |
|--------|------|-------------|
| `simulation_id` | str | 唯一运行标识符 |
| `timestamp` | datetime64[ns, UTC] | 调度小时 |
| `market` | str | "EOM" 或 "CRM" |
| `unit_id` | str | 发电机/机组标识符 |
| `unit_type` | str | "power_plant", "storage", "demand", "renewable" |
| `bid_price` | float64 | 提交的投标价格 |
| `bid_volume` | float64 | 提交的投标量 (MW) |
| `cleared_price` | float64 | 市场出清价格 |
| `dispatched_mw` | float64 | 实际调度 (MW) |
| `marginal_cost` | float64 | 机组边际成本 |
| `revenue_eur` | float64 | 调度收入 |
| `profit_eur` | float64 | 收入减成本 |

### 状态管理

- **配置:** YAML/CSV 文件在 `src/simulation/config/` 和场景文件夹中。无运行时状态 —— 一切都是声明式的。
- **仿真状态:** 完全由 ASSUME 的 `World` 类和 mango agent 框架管理。我们不重新实现此部分。
- **模型产物:** 训练好的模型保存为 `.pkl` (XGBoost, scikit-learn) 或 `.pt` (PyTorch RL 策略) 在 `models/` 目录中。
- **API 状态:** FastAPI 是无状态的。运行元数据存储在 SQLite (`results.db`) 中。
- **Chatbot:** LangChain 对话记忆 (buffer) —— 临时的，不持久化。

## 构建 / 构建顺序影响

架构暗示了严格的构建顺序，匹配四阶段学习路线图：

### 阶段 1: 数据基础 + 基本预测
**构建:** `src/data_pipeline/` + 基本的 `src/prediction/load_forecast.py`
- 从 PUDL 或 IEA 接入数据
- 数据清洗管道
- 简单的 XGBoost 负荷预测器
- **为什么先做:** 所有下游都需要干净数据。基本预测验证管道是否工作。
- **依赖:** 无 (独立)
- **交付物:** 展示 "数据 → 负荷预测" 的可运行 notebook

### 阶段 2: 深入预测 + 市场仿真入门
**构建:** 完整 `src/prediction/` + `src/simulation/` (ASSUME 设置)
- OpenSTEF 集成用于自动化 ML 预测
- 使用 epftoolbox 进行电价预测
- ASSUME 安装和基本场景 (2机组市场)
- **为什么第二:** 预测输入仿真。ASSUME 是所有后续交易工作的平台。
- **依赖:** 阶段 1 (需要干净数据)
- **交付物:** 使用朴素策略运行 ASSUME 仿真

### 阶段 3: 交易智能体
**构建:** `src/agents/` (策略, RL, 回测)
- 自定义投标策略 (边际成本, 加成, 基于预测)
- RL agent 训练 (ASSUME 的学习能力)
- 历史回测引擎
- **为什么第三:** 策略在没有市场可测试的情况下毫无意义。仿真必须先存在。
- **依赖:** 阶段 2 (需要 ASSUME + 预测)
- **交付物:** RL agent 在回测中优于朴素策略

### 阶段 4: 整合 + LLM 接口
**构建:** `src/interface/` (API, CLI, Chatbot)
- FastAPI 包装所有管道阶段
- CLI 带各层的子命令
- LangChain chatbot 带 tool-calling
- **为什么最后:** 接口层包装所有之前的层。底层必须稳定。
- **依赖:** 阶段 1-3 (所有层)
- **交付物:** 端到端 "问 chatbot → 获取预测 → 运行仿真" 流程

### 阶段依赖图

```
阶段 1 (数据 + 基本预测)
    │
    ├──→ 阶段 2 (深入预测 + 市场仿真)
    │        │
    │        ├──→ 阶段 3a (基于规则的策略)
    │        │        │
    │        │        └──→ 阶段 3b (RL Agents)
    │        │                 │
    │        │                 └──→ 阶段 4 (接口)
    │        │
    │        └──→ 阶段 2b (电价预测增强)
    │
    └──→ Notebooks (贯穿所有阶段持续进行)
```

## 扩展考量

| 规模 | 架构调整 |
|-------|--------------------------|
| **学习 (1 用户)** | 所有层在单进程中运行。数据较小 (<1GB)。本地磁盘上的 SQLite + Parquet。模型训练在 CPU (XGBoost)。ASSUME <20 机组。 |
| **研究 (1-5 用户)** | 添加 Docker Compose 以实现可复现性。ASSUME 50+ 机组, 1年仿真。DuckDB 替换 SQLite 以加速分析查询。GPU 可选用于 RL 训练。 |
| **课堂 (20+ 用户)** | 预构建的 Docker 镜像包含所有依赖。镜像中预下载数据。云端 JupyterHub。每个学习者获得隔离环境。 |
| **生产规模** | 根据项目约束超出范围。 |

### 扩展优先顺序

1. **第一个瓶颈:** ASSUME 仿真速度与大量智能体。缓解：使用 ASSUME 内置的并行执行 (使用 mango 容器的分布式仿真)。
2. **第二个瓶颈:** 数据量 (数年小时级数据)。缓解：DuckDB (列式、快速分析查询) 替代 SQLite。

## 反模式

### 反模式 1: 单体 Notebook

**常见错误:** 把所有东西放在一个巨大的 Jupyter notebook 中 —— 数据加载、清洗、训练、仿真、绘图。

**为什么错误:** 无法独立运行。不能替换其中一部分。重启 kernel = 重新运行一切。无法测试。

**正确做法:** 每层是一个带函数的 Python 模块。Notebooks 从模块导入，保持精简 (可视化 + 叙述)。模块可进行单元测试。

### 反模式 2: 重新发明市场仿真

**常见错误:** 自己从零写 order book、出清引擎、机组模型 "来学习其工作原理"。

**为什么错误:** 电力市场仿真极其复杂 (block orders, linked orders, 网络约束, 再调度)。需要数月时间得到一个有 bug 的版本。没有时间留给 AI/学习部分 —— 那才是实际目标。

**正确做法:** 将 ASSUME 作为仿真引擎。包装它、配置它、扩展其策略。ASSUME 已经正确处理了市场机制。将学习精力集中在预测模型和交易策略上 —— 这才是 AI 价值的所在。

### 反模式 3: 预测与交易的强耦合

**常见错误:** 交易策略代码直接内联调用预测模型。

**为什么错误:** 无法针对不同预测质量水平进行回测。无法在不触动策略代码的情况下将 XGBoost 换成 LSTM。无法分别评估预测和策略。

**正确做法:** 预测被物化为 DataFrame/文件。交易策略通过定义的接口消费预测 DataFrame。回测用不同的预测文件对同一策略进行重放。

### 反模式 4: 过早集成 LLM

**常见错误:** 在管道工作之前就开始构建 chatbot。

**为什么错误:** Chatbot 是功能工具的薄包装。如果底层功能不工作，chatbot 会幻觉、错误级联、学习者失去信任。

**正确做法:** 每个功能工具必须先是一个可工作的 CLI 命令。Chatbot 是最后添加的层 —— 仅在所有管道被证明稳定之后。

## 学习目标映射

| 组件 | 学习目标 |
|-----------|-------------------|
| `data_pipeline/ingest.py` | 如何获取和版本化公开能源数据集 |
| `data_pipeline/clean.py` | 时序数据质量: 缺失值, 重采样, UTC 处理 |
| `data_pipeline/features.py` | 能源领域特征工程 |
| `prediction/load_forecast.py` | ML 管道: 训练/测试划分, 特征重要性, 评估 |
| `prediction/price_forecast.py` | 日前市场机制, LEAR 模型, 预测基准测试 |
| `simulation/config/` | 电力市场设计: EOM, 出清机制, 产品类型 |
| `simulation/runner.py` | 大规模运行多智能体仿真 |
| `agents/strategies/marginal_cost.py` | 发电机成本结构, 排序法, 投标制定 |
| `agents/rl/` | 强化学习: 状态/动作/奖励设计, DRL 算法 |
| `agents/backtest.py` | 策略评估: Sharpe 比率, PnL, 回撤, 统计检验 |
| `interface/api/` | 使用 FastAPI 构建生产就绪的 Python API |
| `interface/chatbot/` | LLM function calling, prompt engineering, 工具编排 |

## 集成点

### 外部库

| 库 | 集成模式 | 备注 |
|---------|---------------------|-------|
| **ASSUME** | 作为 `assume` 包导入。场景配置在 YAML/CSV 中。我们的代码包装 `World.setup()` 和 `World.run()`。 | AGPL-3.0 license. 安装 `pip install assume-framework[learning]`。 |
| **OpenSTEF** | 导入 `openstef` 用于自动化 ML 管道。使用其 `openstef.model` 和 `openstef.pipeline` 模块。 | MPL-2.0 license. 需要自定义数据库连接器或基于文件的回退。 |
| **enda** | 导入 `enda` 用于时序工具: `enda.timeseries`, `enda.feature_engineering`。 | MIT license. 轻量级, 无数据库依赖。 |
| **epftoolbox** | 导入 `epftoolbox` 用于 LEAR 模型和基准数据集。 | Apache-2.0 license. 包含 5 个市场数据集。 |
| **PUDL** | 使用 `pudl` Python 包或从 Kaggle/AWS 下载预构建的 SQLite。 | MIT license. 500MB+ SQLite 数据库。 |
| **LangChain** | `langchain` + `langchain-openai` 或 `langchain-ollama` 用于 chatbot。 | MIT license. |
| **FastAPI** | 标准 FastAPI + Pydantic v2 用于 REST API。 | MIT license. |
| **stable-baselines3** | 被 ASSUME 内部导入用于 RL。我们通过 ASSUME 的策略接口扩展。 | MIT license. |

### 内部边界

| 边界 | 通信方式 | 备注 |
|----------|---------------|-------|
| Data → Prediction | Parquet 文件 (路径作为配置传入) | Schema 在 `shared/types.py` 中定义 |
| Prediction → Simulation | DataFrame 传递给 ASSUME 预测器或 CSV 文件 | ASSUME 原生支持 CSV 预测输入 |
| Simulation → Agent | ASSUME 输出 CSV → 由回测引擎解析 | 或者如果内联运行则直接使用 Python 对象 |
| Agent → Interface | 同一进程内的函数调用 | 所有管道阶段是可导入的 Python 函数 |
| Interface → User | JSON (API), text (CLI), 自然语言 (Chatbot) | 三种并行访问模式 |

## 来源

- **ASSUME 框架架构:** https://assume.readthedocs.io/en/latest/introduction.html#architecture (官方文档, HIGH confidence)
- **ASSUME API 参考:** https://assume.readthedocs.io/en/latest/assume.html (官方文档, HIGH confidence)
- **ASSUME Unit Forecasts:** https://assume.readthedocs.io/en/latest/unit_forecasts.html (官方文档, HIGH confidence)
- **OpenSTEF GitHub:** https://github.com/OpenSTEF/openstef (官方仓库, HIGH confidence)
- **enda GitHub:** https://github.com/enercoop/enda (官方仓库, HIGH confidence)
- **epftoolbox GitHub:** https://github.com/jeslago/epftoolbox (官方仓库, HIGH confidence)
- **PUDL GitHub:** https://github.com/catalyst-cooperative/pudl (官方仓库, HIGH confidence)
- **ASSUME Paper (SoftwareX 2025):** Harder et al., "ASSUME: An agent-based simulation framework for exploring electricity market dynamics with reinforcement learning" (同行评审, HIGH confidence)
- **epftoolbox Paper (Applied Energy 2021):** Lago et al., "Forecasting day-ahead electricity prices" (同行评审, HIGH confidence)

---

*架构调研：AI驱动的电力交易学习平台*
*调研日期: 2026-05-20*
