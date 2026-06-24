# Ellectric 项目全面技术文档

> AI + 电力交易技术学习平台 — 端到端技术闭环的完整实现

---

## 目录

1. [项目概述](#1-项目概述)
2. [总体架构](#2-总体架构)
3. [Phase 1：负荷预测基础](#3-phase-1负荷预测基础)
4. [Phase 2：电价预测与市场仿真](#4-phase-2电价预测与市场仿真)
5. [Phase 3：强化学习交易智能体与回测](#5-phase-3强化学习交易智能体与回测)
6. [Phase 4：API / CLI / LLM 三层接口](#6-phase-4api--cli--llm-三层接口)
7. [Phase 5：Web Chat UI（SSE 流式对话）](#7-phase-5web-chat-ui-sse-流式对话)
8. [数据更新与工程改进](#8-数据更新与工程改进)
9. [11 个渐进式 Jupyter Notebook 学习路径](#9-11-个渐进式-jupyter-notebook-学习路径)
10. [技术决策总览](#10-技术决策总览)

---

## 1. 项目概述

**Ellectric** 是一个教育/学习用途的技术平台，目标是跑通从公开电力数据接入到自动交易策略的完整技术闭环：

```
公开电力数据接入 → 负荷/电价预测 → 电力市场仿真 → 自动交易策略
```

项目定位为非生产系统，所有数据来自公开来源，所有工具为开源方案，单机可运行，Python 3.11+。

### 1.1 五个开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | OWID 数据接入 → 清洗 → 特征工程 → XGBoost 负荷预测 | ✅ 完成 |
| Phase 2 | LEAR 电价预测 + ASSUME 电力市场仿真 | ✅ 完成 |
| Phase 3 | RL 交易智能体 (PPO/SAC/TD3) + 回测 + SHAP 可解释性 | ✅ 完成 |
| Phase 4 | FastAPI + CLI + LangChain/DeepSeek LLM 接口 | ✅ 完成 |
| Phase 5 | Web Chat UI：SSE 流式对话界面 | ✅ 完成 |

---

## 2. 总体架构

### 2.1 三明治架构

```
┌─────────────────────────────────────────────┐
│  接入层                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ FastAPI   │  │ Typer CLI │  │ LLM Agent │  │
│  │ (REST+SSE)│  │ (命令行)  │  │ (自然语言) │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │         │
│        └──────────────┼──────────────┘         │
│                       ▼                        │
│  ┌─────────────────────────────────────────┐  │
│  │  Service 层 (handlers.py + schemas.py)   │  │
│  │  桥接层：Pydantic 校验 + 统一错误处理      │  │
│  └─────────────────────┬───────────────────┘  │
├────────────────────────┼───────────────────────┤
│  核心层                ▼                       │
│  ┌─────────────────────────────────────────┐  │
│  │  Pipeline 层 (12 个模块)                 │  │
│  │  数据 → 清洗 → 特征 → 预测 → 交易 → 解释  │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

核心设计思想：**API、CLI、LLM 三条路径共享同一个 Service 层，Service 层再调用 Pipeline 层**。新增接入方式时只需写新的接入层代码，核心逻辑完全复用。

### 2.2 Pipeline 层模块清单

| 模块 | 文件 | 职责 |
|------|------|------|
| DataLoader | `data_loader.py` | 抽象基类 + 工厂，统一数据接入接口 |
| Cleaner | `cleaner.py` | 数据清洗：缺失值填充 + IQR 异常检测 + UTC 标准化 |
| FeatureEngineer | `features.py` | 三层渐进式特征工程 |
| XGBoostForecaster | `forecaster.py` | XGBoost 负荷预测 + 持久化基线 |
| PriceDataLoader | `price_loader.py` | 电价数据独立加载器 |
| LEARForecaster | `price_forecaster.py` | Lasso 自回归电价预测 |
| StatisticalTests | `statistical_tests.py` | Diebold-Mariano + Giacomini-White 检验 |
| ElectricityMarketEnv | `trading_env.py` | Gymnasium RL 交易环境 |
| RLTrainer | `rl_trainer.py` | PPO/TD3/SAC 统一训练接口 |
| BacktestRunner | `backtester.py` | 历史回测 + 多策略对比 |
| SHAPExplainer | `shap_explainer.py` | SHAP 可解释性（Tree + Linear） |

### 2.3 数据合约

所有模块间传递的 DataFrame 必须满足：

- `timestamp`: `datetime64[ns, UTC]` — 所有时间统一 UTC
- `load_mw`: `float64` — 负荷值，单位 MW

禁止使用别名（如 `date`、`datetime`、`load`、`demand` 等），任何 DataLoader 产出必须符合此合约。

---

## 3. Phase 1：负荷预测基础

### 3.1 干了什么

从公开数据源自动拉取中国电力数据，经过清洗和特征工程，训练 XGBoost 模型预测电力负荷。

**产出文件**：
- `data_loader.py`：OWID 远程拉取 + 本地文件加载
- `cleaner.py`：4 步数据清洗管道
- `features.py`：FeatureEngineer 类（11 个特征）
- `forecaster.py`：XGBoostForecaster + 持久化基线
- 5 个 Jupyter Notebook（01-05）

### 3.2 用了什么技术、为什么

#### 3.2.1 DataLoader ABC + 工厂模式

**技术**：抽象基类（`abc.ABC`）+ `create_loader(source)` 工厂函数。

**为什么**：
- **依赖倒置**：下游模块（清洗、特征、预测）只依赖 `DataLoader.load_data()` 接口，不依赖具体数据源实现。切换 OWID → 本地文件 → Ember 只需改工厂参数，下游代码零改动。
- **开闭原则**：新增数据源只需新增子类并注册到工厂，不修改已有代码。

**数据源与回退策略**：

| 优先级 | 数据源 | URL | 说明 |
|--------|--------|-----|------|
| 1 | OWID CDN | `owid-public.owid.io` | 最快，全球 CDN |
| 2 | GitHub Raw | `raw.githubusercontent.com/owid` | 备选，国内可能慢 |
| 3 | 本地 Parquet 缓存 | `data/owid_china_cache.parquet` | 离线可用 |

设计理由：在中国网络环境下，OWID 的 GitHub raw 经常超时。三级回退确保在任何网络条件下都能拿到数据。

#### 3.2.2 异常值保留策略（反 "spike-as-noise" 模式）

**技术**：IQR（Tukey's fences）检测异常值，但**只记录日志，不删除任何行**。

**为什么**：
- 电力尖峰（极端高温制冷负荷、寒潮取暖负荷、重大活动）往往是**最有价值的信号**，不是噪声。
- 删除尖峰 → 模型永远学不会极端场景 → 实际应用中在最需要准确预测的时刻表现最差。
- XGBoost 树模型天然对异常值鲁棒，不需要提前剔除。

#### 3.2.3 三层渐进式特征工程

**技术**：`FeatureEngineer` 类，三个层级累积构建：

| Tier | 特征数 | 内容 | 目的 |
|------|--------|------|------|
| Tier 1（核心） | 5 | `hour`, `day_of_week`, `month`, `is_weekend`, `lag_24h` | 用最少特征跑通管道，建立基线 |
| Tier 2（中级） | +2 | `is_holiday`, `lag_168h` | 引入节假日和周周期信息 |
| Tier 3（高级） | +4 | `rolling_mean_24h`, `rolling_std_24h`, `hour_sin`, `hour_cos` | 消除噪声，正确处理循环时间 |

**为什么分层**：
- **教学目的**：初学者先用 Tier 1 快速看到结果，再逐步添加特征观察效果提升，每一步都有明确的"为什么加这个特征"的理由。
- **防过度工程**：每层都有独立的性能基准，如果新特征不带来提升，可以回退。
- **循环编码（sin/cos）**：`hour` 是循环变量（0-23），直接用整数会让模型认为 23 和 0 距离很远。`(sin(2πh/24), cos(2πh/24))` 将时刻映射到单位圆，确保 23:00 和 00:00 在向量空间中真正相邻。

#### 3.2.4 TimeSeriesSplit + 折内缩放

**技术**：`TimeSeriesSplit(n_splits=5, gap=24)` + 每个 fold 内部独立 `StandardScaler.fit(train)`。

**为什么**：
- **防止 look-ahead bias**：时间序列不能用随机交叉验证。`TimeSeriesSplit` 确保训练数据始终在测试数据之前。
- **gap=24**：因为 `lag_24h` 特征的存在，如果不留 gap，训练集的最后 24 小时和测试集的前 24 小时会共享信息（通过 lag 特征泄露）。
- **折内缩放**：`scaler` 在 fold 内 fit → transform test，而不是在全量数据上 fit。如果先在全量数据上 fit scaler，测试集的分布信息已经泄露到训练过程中（data leakage）。

#### 3.2.5 XGBoost + 持久化基线

**技术**：XGBoost 梯度提升树 + `persistence_forecast()`（`forecast[t] = actual[t-24]`）。

**为什么**：
- **XGBoost**：表格数据上的 SOTA 方法，天然处理缺失值、特征交互、异常值鲁棒，比深度学习更适合中小规模时序数据。
- **持久化基线**：电力负荷有极强的日周期性（昼夜循环）。"昨天同时刻 = 今天预测"是最简单但极其有效的基线。如果 XGBoost 不能显著优于持久化，说明特征工程或模型调参有问题——这是一个**健康检查机制**。

---

## 4. Phase 2：电价预测与市场仿真

### 4.1 干了什么

在负荷预测基础上，引入电价数据、训练 LEAR 电价预测模型、进行统计显著性检验、并搭建了基于 ASSUME 框架的中国省间电力市场仿真。

**产出文件**：
- `price_loader.py`：独立电价数据加载器
- `price_forecaster.py`：LEARForecaster（Lasso 自回归）
- `statistical_tests.py`：DM/GW 预测精度统计检验
- `assume/`：仿真脚本 + 3 套场景配置 + Grafana 仪表板
- 3 个 Jupyter Notebook（06-08）

### 4.2 用了什么技术、为什么

#### 4.2.1 LEAR（Lasso Estimated AutoRegressive）

**技术**：Lasso（L1 正则化线性回归）+ 大量自回归滞后特征。

损失函数：`Min: MSE + α × Σ|βᵢ|`

**为什么不用 XGBoost 做电价预测**：
- **可解释性**：Lasso 产出线性系数，每个非零系数直接解释为"该特征每变化 1 单位，电价变化 X 元/MWh"。XGBoost 是黑盒。
- **自动特征选择**：L1 正则化将无关特征的系数压缩为零，最终只保留预测能力最强的少数滞后项。这本身就是一种"模型告诉你什么重要"的教学手段。
- **学术基准**：LEAR 由 Lago et al. (2021) 提出，是日前电价预测的标准基准方法。
- **对比学习**：Lasso（线性）和 XGBoost（非线性树）两种方法论形成对照，让学生理解"什么时候用简单模型反而更好"。

**PriceDataLoader 为什么不继承 DataLoader ABC**：
- 电价数据 7 列多维（日前价、实时价、负荷、风电、光伏、联络线），与 DataLoader 的单一 `load_mw` 合约不兼容。
- 强制继承 ABC 会增加不必要的抽象负担。使用**组合优于继承**——提供相同的 `load_data()` / `get_metadata()` 接口但不共享继承链。

#### 4.2.2 Diebold-Mariano + Giacomini-White 检验

**技术**：DM (1995) 检验 + GW (2006) 检验，比较两个预测模型的误差序列是否具有统计显著性差异。

**为什么**：
- **不能只看 MAE**：LEAR 的 MAE 比持久化低 2%，这个差异是真实改善还是随机波动？DM 检验给出 p-value，告诉你差异是否统计显著。
- GW 是 DM 的推广，能处理嵌套模型和参数估计不确定性，作为 DM 的补充验证。
- **学术严谨性**：在电力预测文献中，DM 检验是标配。引入它让学生接触学术研究的标准方法论。

#### 4.2.3 ASSUME 双引擎仿真

**技术**：ASSUME v0.6.0（Python 多智能体电力市场仿真框架）+ 内置纯 Python 回退引擎。

**为什么用双引擎**：
- ASSUME 功能完整（merit-order dispatch、agent bidding、market clearing），但依赖 PyTorch，安装重。
- 内置回退引擎确保在 ASSUME 未安装时也能运行仿真——降低学习门槛。
- 两个引擎输出相同的 4 文件合约（clearing_prices.csv / dispatch.csv / agent_profits.csv / metadata.json），对下游完全透明。

**三个仿真场景**：

| 场景 | 配置 | 目的 |
|------|------|------|
| `default` | 基准 80GW 需求，100GW 装机 | 标准市场运行 |
| `summer_peak` | 需求 +20%，天然气增加 | 迎峰度夏压力测试 |
| `wind_high` | 风电 30GW（+50%），煤电降至 40GW | 高可再生能源渗透率 |

**为什么设计多场景**：电力市场的核心挑战因场景而异——夏季高峰考验供给能力，高风电考验灵活性。单场景无法展示市场机制的复杂性。

#### 4.2.4 完全中国化修正（Phase 2 Replan）

原方案使用 epftoolbox 的 5 个基准数据集（全为欧美市场），后发现：
1. epftoolbox 依赖 TensorFlow，与 ASSUME 的 PyTorch 冲突
2. 欧美市场与中国电力市场结构差异巨大（定价机制、电源结构、管制环境）

**修正**：改为 ZionLuo 中国现货市场数据 + sklearn Lasso 实现 + 中国省间市场规则（Price Cap 1500 元/MWh，偏差考核 0.1）。

---

## 5. Phase 3：强化学习交易智能体与回测

### 5.1 干了什么

构建了完整的"预测 → 决策 → 回测 → 解释"闭环：自建 Gymnasium 电力交易环境，训练 PPO/TD3/SAC 三种 RL 智能体，回测对比策略表现，并用 SHAP 解释模型决策。

**产出文件**：
- `trading_env.py`：ElectricityMarketEnv（Gymnasium 环境）
- `rl_trainer.py`：BaseRLAgent ABC + PPO/TD3/SAC 适配器 + RLAgentFactory
- `backtester.py`：BacktestRunner + 3 种基线策略
- `shap_explainer.py`：SHAP TreeExplainer + LinearExplainer
- 3 个 Jupyter Notebook（09-11）

### 5.2 用了什么技术、为什么

#### 5.2.1 自建 Gymnasium 环境（不依赖 ASSUME）

**技术**：`ElectricityMarketEnv(gym.Env)`，Dict 观测空间 + Box 连续动作空间。

观测空间（5 个 key）：

| Key | Shape | 含义 |
|-----|-------|------|
| `load_forecast_24h` | (24,) | XGBoost 未来 24h 负荷预测 |
| `price_forecast_24h` | (24,) | LEAR 未来 24h 电价预测 |
| `time_features` | (4,) | hour_sin/cos + dow_sin/cos 循环编码 |
| `price_history_168h` | (168,) | 过去 7 天电价历史 |
| `account_state` | (2,) | [现金, 进度] |

动作空间：`Box(0, 1, (24,))` — 未来 24 小时的归一化投标量。

**为什么自建而不是用 ASSUME 的环境**：
- ASSUME 仿真环境与 RL 训练的生命周期不兼容（需要完整的 market clearing 流程，不能单步 step）。
- 自建环境可以在每步 step 中直接注入历史价格数据，实现确定性的 reward 计算。
- 控制粒度更细：可以自定义 reward 函数、观测空间、出清逻辑。

**三级预测回退**：
1. 优先使用训练好的 forecaster 模型
2. 降级为持久化预测（最近 24h 实际值）
3. 数据不足时返回零向量

#### 5.2.2 三种 RL 算法对比

**技术**：`stable-baselines3` 的 PPO、TD3、SAC，通过 `RLAgentFactory` 统一创建。

```python
RLAgentFactory.create("ppo", env)   # → PPO (on-policy)
RLAgentFactory.create("td3", env)   # → TD3 (off-policy, deterministic)
RLAgentFactory.create("sac", env)   # → SAC (off-policy, stochastic)
```

**为什么选这三种**：
- **PPO**：on-policy，稳定可靠，最常用的 RL 基线。适合初学者理解 RL 训练流程。
- **TD3**：off-policy，确定性策略。在连续控制任务中表现优异，解决 DDPG 的 overestimation bias。
- **SAC**：off-policy，随机策略 + 最大熵。在探索和利用之间平衡最好，适合不确定环境下的交易决策。

三种算法覆盖了 on/off policy、deterministic/stochastic 两个维度，形成完整的对比学习矩阵。

#### 5.2.3 三种奖励函数

| 奖励函数 | 公式 | 目的 |
|----------|------|------|
| `profit_only` | `Σ pnl_hourly` | 纯利润最大化 |
| `risk_adjusted` | `Σ pnl - σ(pnl)` | 考虑风险调整 |
| `volume_penalty` | `Σ pnl - 0.5 × max(0, mean_bid - 0.5) × 100` | 惩罚过度投标 |

**为什么需要多种奖励函数**：真实交易中纯利润最大化可能导致激进策略（大量投标 → 高偏差惩罚）。通过对比不同 reward 下智能体的行为差异，学生直观理解 reward shaping 对 RL 策略的决定性影响。

#### 5.2.4 BacktestRunner 多策略对比

**技术**：`BacktestRunner.replay()` 逐 24h 块回放 + `compare()` 四维度对比。

策略体系：

| 策略 | 类型 | 原理 |
|------|------|------|
| `oracle` | 基线（上界） | 完美预见，`bid[t] = actual[t]` |
| `baseline_persistence` | 基线（下界） | `bid[t] = actual[t-24]` |
| `baseline_mean` | 基线 | `bid[t] = mean(actual[t-168:t])` |
| PPO / TD3 / SAC | RL 策略 | 模型预测投标 |

对比指标：总收益、夏普比率、胜率、最大回撤。

**为什么需要 oracle 基线**：
- Oracle 代表理论上界（完美预测下的最优策略）。
- 如果 RL 策略的总收益超过 oracle → 有 bug（不可能比完美预测更好）。
- 如果 oracle 不是最优 → 回测逻辑或环境出清有问题。
- 这是内置的**逻辑一致性检查**。

#### 5.2.5 SHAP 双 Explainer

**技术**：`shap.TreeExplainer`（XGBoost）+ `shap.LinearExplainer`（Lasso）。

**为什么用 SHAP**：
- 基于博弈论 Shapley 值，`prediction = base_value + Σ shap_valueᵢ`，加法性分解保证一致性。
- TreeExplainer 精确计算 XGBoost 的 Shapley 值（不需要采样近似）。
- LinearExplainer 直接从 Lasso 系数推导 SHAP 值。
- **对比两种模型的特征归因**本身就是学习目标：树模型捕捉特征交互但归因复杂，线性模型归因透明但无交互。

**惰性导入设计**：SHAP 包体积大，只在真正需要解释时才 `import shap`。`feature_importance_ranking()` 不需要 SHAP，直接读模型的 `feature_importances_` / `coef_`。

---

## 6. Phase 4：API / CLI / LLM 三层接口

### 6.1 干了什么

为 Phase 1-3 的所有能力提供三种对外接口：REST API（FastAPI）、命令行（Typer CLI）、自然语言对话（LangChain + DeepSeek LLM Agent）。

**产出文件**：
- `api/server.py`：FastAPI 应用，7 个端点
- `service/schemas.py`：9 个 Pydantic v2 模型
- `service/handlers.py`：4 个 `run_*()` 处理函数
- `cli/main.py`：5 个 Typer 子命令
- `llm/agent.py`：LangChain agent（DeepSeek 驱动）
- `llm/tools.py`：3 个 `@tool` 函数

### 6.2 用了什么技术、为什么

#### 6.2.1 Pydantic v2 + 延迟导入

**技术**：所有请求/响应使用 Pydantic v2 模型校验 + handlers 层全部使用函数内延迟导入。

**为什么延迟导入**：
- `handlers.py` 被 `server.py`（FastAPI）、`cli/main.py`（Typer）、`llm/tools.py` 三处导入。
- 如果模块顶部 `import ellectric.pipeline.*`，在 CLI 环境中也会触发 pipeline 所有依赖的加载，拖慢命令行启动。
- 延迟导入到函数内 → 只有实际调用该 handler 时才加载对应的 pipeline 模块。

#### 6.2.2 三明治架构中的 Service 层

```
API (server.py)  ─┐
CLI (main.py)    ─┼─→ Service (handlers.py) ─→ Pipeline (12 modules)
LLM (agent.py)   ─┘
```

**为什么需要中间 Service 层**：
- **DRY 原则**：`run_forecast()` 的逻辑只在 handlers.py 写一次。API、CLI、LLM tool 三层复用同一份逻辑。
- **输入校验统一**：Pydantic 模型在 Service 层入口校验，不管请求来自 HTTP、命令行还是 LLM，校验规则完全一致。
- **错误处理统一**：`status: "success"/"error"` + `error_message` 的统一响应格式，三层消费者都能一致处理。

#### 6.2.3 FastAPI：同步端点 + 自动文档

**技术**：FastAPI 同步端点函数（非 async），5 个业务端点 + 1 个 health check。

**为什么用同步端点**：
- Pipeline 层的计算（模型推理、数据加载、回测）全是 CPU 密集型，没有 I/O 等待。
- Python 的 async/await 对 CPU 密集型任务无加速效果，直接 `def` 函数更简单。
- FastAPI 自动在 thread pool 中执行同步端点，不会阻塞事件循环。

唯一的异步端点是 `/chat/stream`（SSE 流式响应），因为它需要 `async generator` 逐 token 推送。

#### 6.2.4 LangChain + DeepSeek（OpenAI 兼容路径）

**技术**：`langchain_openai.ChatOpenAI` → `api.deepseek.com/v1`（OpenAI 兼容协议）。

**为什么这样接入**：
- DeepSeek 官方推荐 OpenAI SDK 兼容方式接入，不推荐专用 SDK。
- `ChatOpenAI(base_url="https://api.deepseek.com/v1")` 直接复用 LangChain 的 tool calling、streaming 等功能，无需额外适配。
- `temperature=0.3`：平衡确定性与多样性，避免电力交易建议过于随机。

**三个 LLM Tool**：

| Tool | HTTP 调用 | 功能 |
|------|-----------|------|
| `query_forecast` | `POST /predict` | 查询负荷/电价预测 |
| `run_simulation` | `POST /simulate` | 运行市场仿真 |
| `run_backtest` | `POST /backtest` | 运行策略回测 |

**为什么 Tool 通过 HTTP 调用 API 而不是直接调 handler**：
- 符合三明治架构：LLM layer 和 API layer 平级，都通过 Service 层。
- 架构一致性：如果 LLM tool 直接调 handler，就绕过了 Pydantic 校验层。
- 可独立部署：API 服务和 LLM agent 可以在不同进程中运行。

#### 6.2.5 无状态 Agent 设计

每次 `ask_agent()` 调用创建全新的 agent 实例，不保留对话历史。

**为什么无状态**：CLI 单次查询场景不需要多轮对话。Web Chat UI 场景由客户端管理历史 → 每次请求传完整 `history` 列表，服务端仍无状态。这种设计简化了服务端逻辑，避免了会话管理的复杂性。

---

## 7. Phase 5：Web Chat UI（SSE 流式对话）

### 7.1 干了什么

为 LLM 对话能力提供 Web 图形界面：纯前端单页应用 + SSE 流式输出，用户无需安装 Python 环境即可通过浏览器与 Ellectric AI 助手对话。

**产出文件**：
- `chat/streaming.py`：SSE async generator 封装
- `api/static/index.html`：纯 HTML/CSS/JS 聊天界面
- `api/server.py`（修改）：新增 `POST /chat/stream` + StaticFiles

### 7.2 用了什么技术、为什么

#### 7.2.1 SSE（Server-Sent Events）而非 WebSocket

**技术**：`StreamingResponse(media_type="text/event-stream")` + `async generator`。

事件类型：`token` / `tool_call` / `tool_result` / `error` / `done`。

**为什么 SSE 而非 WebSocket**：
- 对话场景是单向流（服务器→客户端推送 tokens），不需要客户端持续推送。
- SSE 是 HTTP 标准，不需要额外的协议升级握手，实现更简单。
- 浏览器原生支持 `EventSource` API，自动重连。
- WebSocket 对代理/防火墙更敏感，SSE 是纯 HTTP，兼容性更好。

#### 7.2.2 零依赖纯前端

**技术**：单个 HTML 文件，marked.js 从 CDN 加载（带 fallback 纯文本）。

**为什么零依赖**：
- 学习项目，前端不应成为焦点。一个 HTML 文件即可满足所有需求。
- 无构建工具（webpack/vite）、无 npm install、无 node_modules。
- CDN 失败时 fallback 为纯文本显示，不会白屏。

#### 7.2.3 LangChain astream_events

**技术**：`ChatOpenAI(streaming=True)` + `agent.astream_events()`。

**为什么**：
- `astream_events` 不仅推送 token，还能推送 tool_call 和 tool_result 事件。
- 前端可以显示"正在调用工具 X…"的状态标签，让用户理解 agent 在做什么（而非黑盒等待）。
- 工具调用完成后状态标签变绿，形成完整的可见性闭环。

---

## 8. 数据更新与工程改进

### 8.1 OWID 三级回退

**做了什么**：将 OWID 数据拉取从单点改造为 CDN → GitHub → 本地缓存三级回退。

**为什么**：GitHub raw 在中国网络环境下经常超时（30s+），OWID 的 CDN 更快但偶尔不可用。三级回退确保在各种网络条件下都能拿到数据，离线时也可用最后缓存的版本。

### 8.2 流式 CSV 解析

**技术**：`csv.DictReader` + `io.TextIOWrapper` 逐行处理 25MB OWID CSV，不整体加载到内存。

**为什么**：OWID 全球能源数据包含所有国家的数据，文件 25MB+。如果整体 `pd.read_csv()` 加载后再筛选中国数据，内存浪费严重且速度慢。流式解析在读取阶段就过滤掉非中国行。

### 8.3 Ember 数据源扩展

**做了什么**：新增 `EmberLoader`，探索 Ember Climate API 的小时级中国电力数据。

**为什么**：OWID 数据是年级别的，只能用于趋势分析。小时级负荷预测需要更细粒度的数据。Ember 的 API 提供小时级数据，是未来的数据升级方向。

---

## 9. 11 个渐进式 Jupyter Notebook 学习路径

### 9.1 全景学习路径

```
数据接入 (01)
  → 数据清洗 (02)
    → 特征工程 (03)
      → [分支A] XGBoost 负荷预测 (04) ─────────┐
      → [分支B] 端到端基线 Pipeline (05) ───────┤
                                                ├→ LEAR 电价预测 (06)
                                                │   → 模型对比仪表板 (07)
                                                │     → ASSUME 仿真分析 (08)
                                                │
                                                └→ RL 环境 + PPO 训练 (09)
                                                    → 多算法回测对比 (10)
                                                      → SHAP 可解释性 (11)
```

### 9.2 每个 Notebook 的设计理念

| # | Notebook | 核心教学点 | 关键方法 |
|---|----------|-----------|----------|
| 01 | 数据获取 | ABC 抽象、工厂模式、数据合约 | `create_loader('owid')` |
| 02 | 数据清洗 | IQR 原理、异常值保留决策、Schema 验证 | `clean_data()` |
| 03 | 特征工程 | 三层特征、循环编码数学原理 | `FeatureEngineer` |
| 04 | 负荷预测 | 梯度提升原理、TimeSeriesSplit、Persistence 基线检查 | `XGBoostForecaster` |
| 05 | 端到端基线 | "Walking Skeleton"理念、P&L 计算 | `persistence_forecast()` |
| 06 | 电价预测 | Lasso 原理、L1 稀疏化、LEAR 学术基准 | `LEARForecaster` |
| 07 | 模型对比 | DM/GW 统计检验、多维度误差分析 | `run_statistical_tests()` |
| 08 | 仿真分析 | Merit Order、新能源消纳率、多场景对比 | ASSUME 输出分析 |
| 09 | RL 入门 | Gymnasium 环境、PPO 训练、动作分布分析 | `ElectricityMarketEnv` |
| 10 | 策略对比 | 多算法对比、奖励函数行为分析、回测指标 | `BacktestRunner` |
| 11 | 可解释性 | Shapley 值原理、Tree vs Linear Explainer | `shap_explainer` |

每个 Notebook 包含：背景知识讲解 → 可执行代码 → 可视化输出 → 学习笔记 → 思考题。整套 Notebook 设计遵循"看懂数据 → 清洗 → 特征 → 预测 → 决策 → 解释"的渐进式自学路径。

---

## 10. 技术决策总览

### 10.1 核心设计原则

| 原则 | 说明 | 体现 |
|------|------|------|
| **依赖倒置** | 高层模块依赖抽象，不依赖具体实现 | DataLoader ABC、BaseRLAgent ABC |
| **渐进式复杂度** | 从简单到复杂，每一步都有理由 | 三层特征、Tier 1→3 预测、持久化→XGBoost→RL |
| **显式优于隐式** | 关键设计决策写入代码和文档 | `REQUIRED_COLUMNS`、模块 docstring、IQR 保留注释 |
| **防御性编程** | 优雅降级，不崩溃 | 三级回退、可选依赖 try/except、双仿真引擎 |
| **教学优先于性能** | 清晰胜于优化 | Lasso 比深度学习更适合教学、自建环境而非用 ASSUME |
| **时区安全性** | 所有 timestamp 强制 UTC | cleaner 默认假设 naive = UTC、非 UTC 自动转换 |

### 10.2 关键技术选择及理由

| 技术选择 | 备选方案 | 选择理由 |
|----------|----------|----------|
| XGBoost | LightGBM, CatBoost, LSTM | 表格数据 SOTA，缺失值鲁棒，对初学者友好，特征重要性可解释 |
| Lasso (LEAR) | XGBoost, NBEATS, Transformer | 线性可解释，系数即边际影响，学术基准，与 XGBoost 形成对照 |
| PPO/TD3/SAC | DQN, A2C, DDPG | 连续动作空间必需，三种覆盖 on/off-policy 和 deterministic/stochastic |
| stable-baselines3 | RLlib, CleanRL, 自实现 | 成熟稳定，文档丰富，符合教学定位 |
| FastAPI | Flask, Django | 自动 OpenAPI 文档（/docs），Pydantic 原生集成，异步支持 |
| LangChain + DeepSeek | OpenAI API, 自建 agent | DeepSeek 性价比高，LangChain 标准化 tool calling，中文能力强 |
| SSE | WebSocket, 轮询 | 单向流足够，HTTP 标准，浏览器原生支持，防火墙友好 |
| Pydantic v2 | dataclasses, JSON Schema | 运行时校验，三层复用，自动生成 API 文档 |
| Plotly | Matplotlib, ECharts | 交互式图表，Jupyter 原生支持，HTML 导出 |
| SHAP | LIME, 特征重要性 | 博弈论基础，加法性分解保证一致性，支持 Tree 和 Linear 两种 Explainer |
| Gymnasium | 自建 RL 接口 | 标准 RL 环境接口，与 SB3 原生集成 |
| ASSUME | 自建仿真 | 成熟的电力市场仿真框架，agent-based 匹配教学需求 |
| Parquet 缓存 | CSV, SQLite | 列存储压缩率高，pandas 原生支持，读写速度快 |

### 10.3 什么还没做（有意的技术债务）

| 事项 | 原因 |
|------|------|
| 0 自动化测试 | 教学项目，Notebook 提供交互式验证 |
| 无 CI/CD | 单机项目，不需要持续集成 |
| 无认证/授权 | 本地运行，不需要多用户 |
| 无数据库持久化 | Notebook + 文件系统足够 |
| 无前端框架 | 单页 HTML 足够，不想引入构建工具复杂度 |
| Docker Compose 全注释 | 教学项目不强制容器化 |
| `__init__.py` 导出不完整 | 各消费者直接按子模块路径导入，避免循环依赖 |

---

> 文档生成日期：2026-06-10
> 项目版本：v0.2.0
