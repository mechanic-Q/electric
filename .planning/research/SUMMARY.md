# 项目调研总结

**项目:** Ellectric — AI驱动的电力交易学习平台
**领域:** 能源 AI / 带基于智能体市场仿真的 ML 教育平台
**调研日期:** 2026-05-20
**置信度:** HIGH

## 执行摘要

Ellectric 是一个**分层学习平台**，通过渐进的 AI 技术教授电力交易 —— 从简单的 XGBoost 负荷预测到深度强化学习智能体在现实的市场仿真中竞争。该领域的专家将此类系统构建为**严格分离的管道** (data → forecast → simulate → trade)，而非单体 notebooks，每层通过明确定义的数据契约 (带标准化 schema 的 Parquet 文件) 进行通信。

推荐的方法是**四阶段构建**，反映学习旅程：阶段 1 使用简单工具 (pandas + XGBoost + 插入到最小仿真中的朴素预测器) 建立可工作的端到端管道，在第 1 天证明集成有效。阶段 2 在基础稳固后引入领域特定的框架 (OpenSTEF 用于自动预测, ASSUME 用于市场仿真)。阶段 3 添加 "酷 AI" — RL 交易智能体、自定义奖励函数和历史回测。阶段 4 将所有内容包装在通过 LangChain + Ollama 的自然语言界面和 FastAPI 后端中。每个阶段都建立在上一阶段的基础上；不可跳过或重排序。

关键风险是**时序预处理中的 look-ahead bias** (将时间能源数据当作 i.i.d. 处理 — 第 1 失败模式)、**将价格尖峰误认为噪声** (裁剪异常值摧毁了重要的交易信号)、以及**针对学术指标而非交易 PnL 优化模型** (RMSE 无法盈利)。所有三者通过在第 1 周用朴素模型运行端到端、对所有预处理使用时间 (而非随机) 划分、以及针对交易利润而非仅预测准确度评估每个模型升级来预防。

## 关键发现

### 推荐技术栈

技术栈跨越五个维度，在各阶段逐步引入。**Python 3.11 是最低要求** (OpenSTEF 需要 >=3.11, ASSUME 0.6.0 + OpenSTEF 3.4.93 都支持它, 使 3.11 成为共同分母)。阶段 1 从精简开始: pandas 3.0.3 (Arrow-backed, fast) + scikit-learn 1.8.0 + XGBoost 3.2.0 + Jupyter notebooks。阶段 2 添加领域工具: OpenSTEF 3.4.93 (用于能源预测的自动 ML 管道), ASSUME 0.6.0 (基于智能体的、内置 DRL agents 的市场仿真), 和 epftoolbox (电价预测基准 — **仅数据集**, 由于 TensorFlow/PyTorch 冲突不在同一环境中安装)。阶段 4 添加 FastAPI 0.136.1, LangChain 1.3.1, Ollama 0.6.2 配合 Qwen2.5-7B (中英双语, 在 16GB RAM 上运行), 和 chromadb 用于 RAG。

**核心技术:**
- **pandas 3.0.3 + enda 1.0.5 + PUDL 2026.5.0**: 能源数据管道 — PUDL 提供分析就绪的美国电力数据 (EIA 860/861/923/930), enda 处理领域特定时序操作 (缺失检测, 合同转换), pandas 3.0 的 Arrow 后端处理性能
- **scikit-learn 1.8.0 + XGBoost 3.2.0**: 阶段 1-2 ML — XGBoost 在能源预测基准测试中持续领先, scikit-learn 提供预处理和评估。两者均 CPU 优化用于开发硬件
- **OpenSTEF 3.4.93 + epftoolbox**: 能源预测框架 — OpenSTEF (LF Energy, MPL-2.0) 提供用于负荷预测的生产风格 AutoML 管道; epftoolbox 提供基准 LEAR/DNN 模型和 5 个用于电价预测的参考市场数据集
- **ASSUME 0.6.0 + stable-baselines3 2.8.0**: 市场仿真 + RL — ASSUME (AGPL-3.0, 发表于 SoftwareX 2025) 处理多智能体电力市场仿真，具有可插拔的 DRL agents (PPO, SAC, TD3), 市场出清 (pay-as-clear, pay-as-bid, nodal), 和 Grafana dashboards
- **FastAPI 0.136.1 + LangChain 1.3.1 + Ollama 0.6.2**: 接口层 (阶段 4) — FastAPI 用于 REST API, LangChain 用于带 tool-calling 的 LLM agent 编排, Ollama 用于本地 LLM 服务 (Qwen2.5-7B-Instruct)

### 期望功能

**必须有 (基本必备 — P1):**
- **公开数据接入管道** — PUDL + IEA data, 一键下载, 版本锁定以实现可复现性。没有干净数据, 其他一切都不工作
- **数据清洗与预处理** — 缺失检测 (enda), 异常值处理 (IQR, 不裁剪), 时区归一化到 UTC, 训练/测试时间划分
- **负荷预测 (手动 XGBoost)** — 特征工程 (hour-of-day, day-of-week, holidays, lags), 在历史期间训练, 用 MAE/RMSE/MAPE 评估, 模型持久化。这是第一个 "我构建了东西" 的时刻
- **结果可视化** — 负荷-vs-预测叠加图, 误差分布直方图, 特征重要性图表。必须在 Jupyter notebooks 中工作
- **Jupyter Notebook 环境** — 文档完善的 notebooks: markdown 解释 → code cells → 输出可视化 → 反思问题。设置必须在干净机器上 <30 分钟内工作
- **引导式学习路径 (阶段 1)** — 带明确成功标准的结构化 notebooks 用于热身阶段

**应该有 (差异化 — P2):**
- **负荷预测 (OpenSTEF)** — 自动管道比较。"手动 vs 自动 ML" 比较有很高的教育意义
- **电价预测 (epftoolbox)** — 在 5 个参考市场 (EPEX-BE/FR/DE, NordPool, PJM) 上使用 LEAR/DNN 基准进行日前电价预测
- **市场仿真 (ASSUME)** — 基于智能体的沙盒，具有可配置的发电组合、需求曲线、市场机制。Grafana dashboards 用于可视化
- **多模型比较仪表板** — 并排 plotly dashboard 比较 XGBoost vs OpenSTEF vs LSTM (负荷) 和 LEAR vs DNN vs naive (电价)。按小时的误差热力图显示每个模型失败的地方
- **场景构建器** — 通过 ASSUME YAML 配置修改发电组合和需求。预构建场景: "大风日", "夏季高峰", "储能套利"

**推迟 (v2+ — P3):**
- **RL Agent Sandbox** — 修改奖励函数, 观察涌现的投标策略, TensorBoard monitoring。要求市场仿真先存在
- **端到端交易回测** — 顶点: forecast → bid → market clear → P&L calculation。要求所有三个支柱 (预测、电价预测、仿真) 单独工作
- **模型可解释性工具** — SHAP values, partial dependence plots。在学习者构建了多个模型后更有影响力
- **LLM 驱动的交易助手** — 包装所有平台能力的自然语言界面。最高的 "惊叹因子" 但要求其他一切先工作

**明确的反功能 (永远不构建):** 实时市场数据推送, 自动化真实资金交易执行, 专有数据抓取, 完整 SaaS web 应用, carbon/emissions trading, 大模型训练 (GPT-scale), 图形化拖放式投标, 多用户协作。

### 架构方法

系统遵循**5 层管道架构**，各层之间有清晰的数据契约边界。每层可独立学习、测试和替换 — 匹配四阶段学习路线图。数据严格向下流动: raw data → cleaned DataFrames → forecast DataFrames → simulation results → agent decisions → user interface。各层通过具有明确定义列 schema 的 Parquet 文件通信，绝不通过直接函数调用。关键模式: Strategy Pattern 用于可插拔投标 (rule-based → prediction-based → RL), Pipeline with Checkpoints 用于更快迭代 (每阶段缓存中间结果), 和 Config-Driven Simulation (ASSUME YAML/CSV configs, 无代码更改以测试不同市场)。

**主要组件:**
1. **Data Layer** (`src/data_pipeline/`) — 接入 (PUDL, IEA), 清洗 (enda, pandas), 特征工程 (calendar, weather, lags), 和存储 (Parquet)。产出 `cleaned_load.parquet`, `cleaned_price.parquet`, `weather_features.parquet`
2. **Prediction Layer** (`src/prediction/`) — 负荷预测 (XGBoost → OpenSTEF), 电价预测 (LEAR/DNN via epftoolbox), 可再生能源发电预测 (weather→power)。所有预测器共享 `predict(horizon) → pd.DataFrame` 接口。产出 `forecast_24h.parquet`
3. **Market Simulation Layer** (`src/simulation/`) — ASSUME wrapper 带 YAML/CSV configs 和预构建学习场景。World orchestration, market operations (日前出清, 平衡), unit operators 管理发电组合。产出 `results.csv` 含出清价格、调度和每机组利润
4. **Agent/Trading Layer** (`src/agents/`) — 可插拔投标策略 (marginal cost → markup → prediction-based → RL), 兼容 Gym 的 RL environments, 带压力测试场景的历史回测引擎。RL agents 通过 ASSUME 的学习接口使用 stable-baselines3 (TD3/SAC/PPO)
5. **Interface Layer** (`src/interface/`) — FastAPI REST API (阶段 4), Typer/Click CLI (all phases), LangChain chatbot with tool-calling (阶段 4)。所有三种访问模式调用相同的底层服务函数

### 关键陷阱

1. **时序预处理中的 Look-Ahead Bias** — 在时序划分前使用 `StandardScaler` 或在整个数据集上计算滚动统计会将未来信息泄露到训练中。预防: 仅在训练期间上拟合 scalers, 使用 `TimeSeriesSplit` (非 `train_test_split`), 审计每个预处理步骤的时间泄露。恢复成本: HIGH (需要从头重做所有特征工程和重新训练)

2. **将价格尖峰当作噪声处理** — 电价表现出负值、高于均值 10-100 倍的尖峰和多模态分布。裁剪异常值或 log-transforming 会摧毁交易利润重要的信号。预防: 在 RMSE 旁使用 sMAPE, spike MAE, spike recall; 永不裁剪价格; 在尖峰检测而非仅聚合误差上评估模型

3. **RL 奖励函数优化了错误的东西** — 纯利润最大化导致退化策略 (以最高价投标, 95% 时间零交易量, 在尖峰上获得巨大奖励)。ASSUME 文档明确警告: "更大的总奖励并不意味着学到的行为更好。" 预防: 始终验证行为 (投标曲线, 接受率) 而非仅奖励大小; 在添加 RL 前从朴素/启发式基线开始; 使用 ASSUME 的 `early_stopping` 配合大型 episodes

4. **不早日进行端到端运行** — 花费数周完善预测模型，然后才将其连接到仿真或交易。预防: 在第 1 周用平凡模型 (下一小时 = 上一小时) 运行完整管道 (data → naive forecast → simulation → P&L)。这验证了集成、数据格式，并建立了要击败的基线

5. **不切实际的市场假设** — 在没有输电约束、市场力、可再生能源间歇性或双重结算的情况下仿真市场。在简化市场中的策略在现实中失败。预防: 从 ASSUME 的内置示例场景开始 (已包含现实的德国市场配置), 逐步添加现实性特征 (阻塞 → 区域定价 → 多重市场 → 辅助服务)

## 对路线图的影响

基于来自所有四个文件的组合调研，架构、功能和陷阱都汇聚于具有严格依赖的四阶段构建顺序:

### 阶段 1: 数据基础 + 基本预测 (热身)

**理由:** 所有下游都依赖于干净数据和工作预测管道。此阶段建立 "骨架" — 所有五层以最小形式存在，证明集成在添加任何复杂度之前工作。调研一致认为: 在第 1 天用朴素模型运行端到端。

**交付:**
- PUDL 数据接入管道 → 清洗后的 Parquet 文件
- 带时序划分的数据清洗 (TimeSeriesSplit, 无 look-ahead bias)
- 带特征工程的手动 XGBoost 负荷预测模型 (calendar, lags)
- 基本可视化 (load vs prediction overlay, error distribution)
- 带 markdown 解释和反思问题的结构化 Jupyter notebooks
- **朴素端到端运行**: persistence forecast → minimal simulation → P&L calculation (验证完整管道存在)

**涵盖功能:** 公开数据接入管道, 数据清洗与预处理, 负荷预测 (手动 XGBoost), 基本结果可视化, Jupyter Notebook 环境, 引导式学习路径 (阶段 1)

**必须避免:** 陷阱 1 (look-ahead bias — 使用 `TimeSeriesSplit`, 仅在训练数据上拟合 scalers), 陷阱 2 (clipping price spikes — 从一开始就用尖峰感知指标评估), 陷阱 5 (no end-to-end — 在第 1 周运行完整循环)

**技术栈:** pandas 3.0.3 + scikit-learn 1.8.0 + XGBoost 3.2.0 + enda 1.0.5 + Jupyter + matplotlib。PUDL 用于数据。纯 CPU — 不需要 GPU。

### 阶段 2: 深入预测 + 市场仿真

**理由:** 阶段 1 证明管道工作。阶段 2 引入领域特定工具 (OpenSTEF 用于自动预测, ASSUME 用于市场仿真)，这些是平台的核心价值。预测输入仿真，所以在仿真场景有意义之前，预测必须成熟。ASSUME 是所有后续交易智能体工作的平台。

**交付:**
- OpenSTEF 自动预测管道 (与阶段 1 的手动 XGBoost 比较)
- 使用 epftoolbox 的电价预测 (LEAR model + 基准数据集, 5 个参考市场)
- ASSUME 安装, 首次 7 天仿真使用默认朴素 agents
- 多模型比较仪表板 (plotly): XGBoost vs OpenSTEF, LEAR vs naive price baselines
- 基本场景构建器 (通过 ASSUME YAML 修改发电组合, 需求曲线)
- 排序法可视化 (通过 ASSUME 的 Docker Compose 在 Grafana dashboards 中)
- 阶段 2 学习的扩展 notebooks

**涵盖功能:** 负荷预测 (OpenSTEF), 电价预测 (epftoolbox), 市场仿真 (ASSUME), 多模型比较仪表板, 场景构建器 (基本), 引导式学习路径 (阶段 2)

**必须避免:** 陷阱 4 (unrealistic market — 从 ASSUME 的 example_01a 开始, 验证仿真价格与真实数据相关 r > 0.6), 陷阱 6 (dual settlement gap — 引入概念即使尚未完全实现), 陷阱 9 (merit order ignorance — 验证排序法台阶出现在 Grafana 中)

**添加的技术栈:** OpenSTEF 3.4.93, epftoolbox (仅数据集 — 不要在同一环境中安装完整包由于 TF/PyTorch 冲突), ASSUME 0.6.0, plotly 6.7.0

### 阶段 3: 交易智能体 + 回测

**理由:** 交易策略没有可测试的市场就毫无意义。ASSUME 必须已经用朴素策略运行 (阶段 2) 才能添加、比较和验证 RL agents。这个阶段引入 "酷 AI" — RL agents 学习交易 — 但架构调研强调 RL 严格是附加的，不是基础的。

**交付:**
- 自定义基于规则的投标策略 (marginal cost, markup, prediction-based)
- 通过 ASSUME 学习能力进行 RL agent 训练 (TD3/SAC/PPO)
- 奖励函数变体 (仅利润, 风险调整, 多组件)
- 用于训练监控的 TensorBoard 集成
- 带压力测试期的历史回测引擎 (2022 energy crisis, 2021 winter storm, COVID demand shock)
- 端到端交易回测: forecast → bid strategy → market clearing → P&L → strategy comparison
- Agent 行为验证套件 (投标曲线, 接受率, strategy Sharpe ratio)

**涵盖功能:** RL Agent Sandbox, End-to-End Trading Backtest, 模型可解释性工具 (SHAP for XGBoost, feature importance)

**必须避免:** 陷阱 3 (RL reward collapse — validate behavior not just reward, use ASSUME's `early_stopping` with large episodes, compare P&L vs naive baseline), 陷阱 8 (survivorship bias — backtest on crisis periods, not just stable markets), 陷阱 10 (pipeline coupling — use ForecastProvider interface so models are swappable)

**添加的技术栈:** stable-baselines3 2.8.0 (在 ASSUME 默认之外的直接使用), optuna 4.8.0 (超参数调优), 可选 PyTorch 如果在 ASSUME 之外训练自定义 RL 模型

### 阶段 4: 整合 + LLM 接口

**理由:** 接口层包装所有之前的层。架构调研明确: 每一个支持 LLM chatbot 的功能工具必须先是一个可工作的 CLI 命令。在管道稳定之前构建 chatbot 会导致幻觉、级联错误和学习者信任丧失。这是最后一层，所有架构反模式都同意。

**交付:**
- FastAPI REST API 带端点: `/predict`, `/simulate`, `/results`, `/backtest`
- CLI 带镜像管道阶段的子命令: `ellectric predict`, `ellectric simulate`, `ellectric backtest`
- LangChain + Ollama chatbot 带 tool-calling:
  - Natural language query: "明天的峰值负荷预测是多少?"
  - Trading command parsing: "第 8-16 小时投标 50MW 价格 $35/MWh"
  - Scenario explanation: "为什么昨天下午价格飙升?"
  - Model comparison: "比较我的 XGBoost 和 OpenSTEF 上周的表现"
- ChromaDB vector store 用于交易文档和历史场景的 RAG
- MLflow experiment tracking dashboard (追溯应用于所有之前阶段的实验)

**涵盖功能:** LLM-Powered Trading Assistant, 所有接口访问模式 (API, CLI, Chatbot)

**必须避免:** 架构反模式 4 (premature LLM integration — every tool must be a working CLI command first), 陷阱 10 (pipeline coupling — interface calls functions, doesn't embed logic)

**添加的技术栈:** FastAPI 0.136.1 + uvicorn 0.47.0, LangChain 1.3.1 + langchain-community 0.4.1, Ollama 0.6.2 + Qwen2.5-7B-Instruct, chromadb 1.5.9, MLflow 3.12.0

### 阶段排序理由

- **阶段 1 必须先来** 因为: (a) 所有层需要干净数据, (b) 用朴素模型运行端到端防止陷阱 5 (the "完美模型, 无集成" trap), (c) 在任何复杂度添加之前建立正确的时间预处理纪律
- **阶段 2 必须第二** 因为: (a) ASSUME 是所有交易工作的平台 — "没有市场可测试，策略就毫无意义。仿真必须先存在" (ARCHITECTURE.md), (b) OpenSTEF 比较只有在学习者在阶段 1 构建了自己的模型后才有意义
- **阶段 3 必须第三** 因为: (a) RL agents 与需要 ASSUME (阶段 2) 的基于规则的基线进行比较, (b) 回测要求预测 (阶段 1-2) 和仿真 (阶段 2) 都存在, (c) 奖励函数设计由阶段 2 仿真中观察到的行为指导
- **阶段 4 必须最后** 因为: 所有架构反模式和陷阱一致认为 — 接口层包装所有底层内容。每个 LLM tool 必须先是一个经过验证的 CLI 命令

### 调研标记

**在规划期间可能需要更深入调研的阶段 (`/gsd-plan-phase --research-phase`):**

- **阶段 2 (深入预测与市场仿真):** ASSUME 配置有文档记录的陷阱 (seed=null for RL, train_freq alignment, complex clearing corner cases)。epftoolbox TensorFlow conflict 需要一个具体的用 scikit-learn 重新实现 LEAR 的计划。PUDL 数据模型理解 (EIA generator IDs, fuel types, timezone handling) 非常重要。OpenSTEF CPU-only install path 需要在目标硬件上验证。

- **阶段 3 (交易智能体):** 电力市场的 RL reward function design 除了 ASSUME 的警告外文档不足。动作空间设计 (continuous vs discrete bidding) 影响算法选择。Multi-agent RL dynamics (centralized critic, gradient step timing per agent) 在 ASSUME release notes 中有文档记录但需要仔细研究。回测压力场景需要选择历史价格数据。

- **阶段 4 (整合 + LLM):** LangChain v1.x tool-calling patterns 用于领域特定数据管道比通用 chatbot 用例有更少示例。用于电力交易文档的 ChromaDB embedding strategy (which chunk size, which embedding model) 需要实验。Ollama Qwen2.5-7B quantization settings for 16GB RAM 需要基准测试。

**具有标准模式的阶段 (跳过 research-phase, 直接进行 plan):**

- **阶段 1 (数据基础):** pandas + scikit-learn + XGBoost data pipeline 是数据科学中文档最完善的模式。PUDL 有大量教程。TimeSeriesSplit 和 temporal preprocessing 在 sklearn docs 和能源预测论文中有详尽覆盖。标准模式 — 直接规划。

## 置信度评估

| 领域 | 置信度 | 备注 |
|------|------------|-------|
| 技术栈 | **HIGH** | 所有版本号在 2026-05-20 对照 PyPI 验证。库兼容性矩阵已记录。ASSUME, OpenSTEF, enda, PUDL 仓库直接检查过。已发表论文 (SoftwareX 2025, Applied Energy 2021) 验证工具质量。 |
| 功能 | **HIGH** | 功能优先级源于 PROJECT.md 4-stage roadmap。所有基本必备功能映射到特定库。差异化功能映射到 ASSUME/LangChain 能力，在官方文档中已验证。反功能与明确的 PROJECT.md 约束对齐。 |
| 架构 | **HIGH** | 分层设计反映 ASSUME 自身架构 (docs at assume.readthedocs.io)。数据契约 schema 已定义。项目结构遵循标准 Python data-science layout。构建顺序对照层级依赖要求验证。 |
| 陷阱 | **HIGH** | 前 10 个陷阱直接来源于 ASSUME official docs (readthedocs), release notes v0.1.0–v0.6.1 (11 个发布版本的 bug 修复历史), 和同行评审论文。预防策略包括工作代码示例和 ASSUME 特定的配置指导。每个关键陷阱提供恢复策略。 |

**整体置信度: HIGH** — 调研对这个领域来说异常彻底。ASSUME 有良好文档和已发表的学术验证, 所有库都有活跃维护和可访问的源代码, PROJECT.md 提供清晰的约束来限定调研范围。

### 待解决的缺口

这些领域在调研中无法完全解决，需要在规划或实现期间关注:

- **中国电力数据管道:** 没有中国能源数据的 Python 包 (PUDL 仅限美国)。STACK.md 注明从国家能源局和菏泽市公共数据开放网手动接入，但实际数据可用性、格式和更新频率需要在阶段 1 规划期间验证。缓解措施: 从 PUDL/IEA 数据开始证明管道; 将中国数据添加为阶段 1 的扩展任务。

- **epftoolbox LEAR model reimplementation:** TensorFlow/PyTorch 冲突意味着 epftoolbox 不能与 ASSUME 在同一环境中安装。用 scikit-learn 重新实现 LEAR model (本质上是带工程特征的 LASSO regression) 应该是直接的，但需要在阶段 2 有一个具体的实现计划。这是低风险的但需要一个任务。

- **ASSUME 中国电力市场配置:** ASSUME 的内置场景建模德国 (EPEX) 市场规则。中国电力市场 (省间 vs 省间, 不同的投标时间线, 不同的可再生能源整合政策) 可能需要自定义市场配置。在阶段 2 规划期间的调研应评估需要多少定制 vs 使用欧洲市场作为主要学习环境。

- **Qwen2.5-7B quantization performance:** STACK.md 推荐 Qwen2.5-7B-Instruct with 4-bit quantization for 16GB RAM, 但性能 (推理速度, 质量下降, 电力领域知识) 尚未为此特定用例进行基准测试。这是阶段 4 的 spike task — 在提交完整 chatbot 实现之前尝试并验证。

## 来源

### 主要 (HIGH confidence)
- **ASSUME Framework** — `https://assume.readthedocs.io/en/latest/` — Architecture, bidding strategies, market mechanisms, reinforcement learning docs, release notes v0.1.0–v0.6.1. GitHub: `github.com/assume-framework/assume` (v0.6.0, AGPL-3.0, 90★)
- **OpenSTEF** — `https://github.com/OpenSTEF/openstef` — v3.4.93 (MPL-2.0, 143★, LF Energy project). Automated ML pipeline for short-term energy forecasting
- **epftoolbox** — `https://github.com/jeslago/epftoolbox` (Apache-2.0, 352★). Electricity price forecasting benchmark with 5 EU/US markets. Published in Applied Energy (2021)
- **PUDL** — `https://github.com/catalyst-cooperative/pudl` (v2026.5.0, MIT, 586★, 11K commits). CC-BY-4.0 licensed US energy data pipeline
- **enda** — `https://github.com/enercoop/enda` (v1.0.5, MIT, 16★). Energy timeseries data manipulation
- **HAMLET** — `https://github.com/tum-ens/HAMLET` (v1.0.1, MIT, 24★). Published in SoftwareX (2025)
- **Harder et al. (2025)** — "ASSUME: An agent-based simulation framework for exploring electricity market dynamics with reinforcement learning," *SoftwareX*, Vol. 30, Article 102176
- **Harder, Qussous & Weidlich (2023)** — "Fit for purpose: Modeling wholesale electricity markets realistically with multi-agent deep reinforcement learning," *Energy and AI*, Vol. 14, 100295
- **Lago et al. (2021)** — "Forecasting day-ahead electricity prices: A review of state-of-the-art algorithms, best practices and an open-access benchmark," *Applied Energy*, Vol. 293, 116983
- **PROJECT.md** — Ellectric project definition with 4-stage learning roadmap, constraints, and out-of-scope decisions

### 次要 (MEDIUM confidence)
- PyPI package index — All version numbers verified via `pip index versions` on 2026-05-20
- scikit-learn, XGBoost, FastAPI, LangChain official documentation — Well-established libraries, used per standard patterns
- LangChain → LlamaIndex comparison — Based on v1.x API surface evaluation; both could coexist (LlamaIndex for retrieval, LangChain for agent orchestration)

### 三级 (LOW confidence)
- 中国电力数据从公开来源的可用性 (国家能源局, 菏泽市公共数据开放网) — 尚未验证。需要阶段 1 spike
- Qwen2.5-7B quantization performance for electricity-domain QA — 未进行基准测试。需要阶段 4 spike

---
*调研完成: 2026-05-20*
*准备路线图: yes*
