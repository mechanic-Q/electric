# 功能调研

**领域:** AI驱动的电力交易学习平台
**调研日期:** 2026-05-20
**置信度:** HIGH

## 功能全景

### 基本必备 (用户期望这些)

用户假定存在的功能。缺少这些 = 学习平台感觉很残破 —— 没有这些就无法教授电力交易。

| 功能 | 为什么是期望的 | 复杂度 | 备注 |
|---------|--------------|------------|-------|
| **公开数据接入管道** | 每个 ML/能源项目都从数据开始。没有干净数据, 其他一切都不工作。 | MEDIUM | 使用 PUDL (US EIA data, SQLite/Parquet outputs) 作为主要来源; 用 IEA Real-Time Electricity Tracker 补充。构建 Python 脚本: (a) 通过 Zenodo DOI 或 Kaggle 下载 PUDL data, (b) 加载到本地 SQLite, (c) 提供抽象的 `DataLoader` 类。包含数据版本锁定以实现可复现性。 |
| **数据清洗与预处理** | 原始能源数据有缺失、异常值、时区问题。学习者必须看到现实的数据整理。 | MEDIUM | 利用 `enda` 进行时序缺失检测、重采样、合同到时序转换。构建可复用的清洗管道: 缺失值填充、异常值检测 (IQR)、时间戳归一化到 UTC。通过带前后对比可视化的 Jupyter notebooks 暴露。 |
| **负荷预测 (ML Pipeline)** | 核心技能: 从天气、日历、历史模式预测电力需求。 | HIGH | 两层方法: (a) **手动模型**: XGBoost 带特征工程 (hour-of-day, day-of-week, 节假日标志, 滞后特征) 以促进教学清晰度; (b) **自动管道**: OpenSTEF 用于比较。必须包含训练/测试划分、回测、模型持久化。评估指标: MAE, RMSE, MAPE。 |
| **电价预测** | 电价预测是预测问题的另一半 —— 没有它, 无法做交易决策。 | MEDIUM | 使用 `epftoolbox` 用于日前市场的基准模型 (LEAR, DNN)。包含 5 个参考数据集 (EPEX-BE/FR/DE, NordPool, PJM)。必须提供相对于朴素基线的比较 (persistence, weekly-average)。 |
| **市场仿真环境** | 交易发生在市场中。学习者需要一个安全实验市场动态的沙盒。 | HIGH | 使用 ASSUME framework 作为核心仿真引擎。运行基于智能体的电力市场仿真，具有可配置的: 发电组合 (煤, 气, 风, 光, 储能), 需求曲线, 市场出清机制 (pay-as-clear, pay-as-bid), 电网拓扑。通过 Docker Compose 包含 Grafana dashboards 用于结果可视化。 |
| **结果可视化** | 学习者需要看到发生了什么 —— 投标, 出清, 利润, 预测准确度。 | LOW-MEDIUM | 时序图表 (matplotlib/plotly): 负荷 vs 预测叠加图, 电价热力图, 智能体 PnL 随时间变化。必须在 Jupyter notebooks 中工作。包含接受标准数据形状的预构建绘图工具。 |
| **Jupyter Notebook 作为主要界面** | 数据科学教育的默认界面。Notebooks 是这个平台的 "实验台"。 | LOW | 提供一套按学习阶段组织的文档完善的 notebooks。每个 notebook: markdown 解释 → code cell → 输出可视化 → 反思问题。支持本地 Jupyter 和 Google Colab。 |
| **环境设置工具** | 初学者无法学习如果花 3 天安装依赖。 | LOW | `requirements.txt` 或 `environment.yml` 带锁定版本。Docker Compose 用于数据库 + Grafana。一键命令设置: `make install` 或 `docker compose up`。为仅 CPU 的机器包含无 CUDA 路径。 |

### 差异化功能 (使其具有教育性)

使这个学习平台不仅仅是阅读文档的功能。这些创造使学习项目有价值的 "顿悟时刻"。

| 功能 | 价值主张 | 复杂度 | 备注 |
|---------|-------------------|------------|-------|
| **RL 交易智能体沙盒** | 学习者修改奖励函数, 观察涌现的投标策略, 理解 RL→交易 的联系。这是平台的核心 "酷炫因子"。 | HIGH | 利用 ASSUME 内置的 DRL 能力 (PPO, TD3, SAC agents)。提供预构建的 notebook 模板供学习者: (a) 更改奖励函数 (仅利润 vs 风险调整), (b) 通过 TensorBoard 观察智能体行为变化, (c) 比较 RL agent vs 基于规则的基线。将超参数暴露为 notebook 变量 (learning rate, discount factor, exploration rate)。 |
| **LLM 驱动的交易助手** | 自然语言界面查询预测、解释市场条件、解读智能体决策。让系统感觉 "智能" 并降低非编程人员的门槛。 | MEDIUM | 使用 LangChain + 本地/开源 LLM API 构建 (例如 Ollama with DeepSeek/Qwen, 或 OpenAI API 作为回退)。能力: (a) "明天下午 6 点预测负荷是多少?" → 查询预测数据库, (b) "解释为什么 RL agent 在第 18 小时投标高价" → 检索智能体状态 + 特征重要性, (c) "比较我的 XGBoost 模型与 OpenSTEF" → 运行比较并总结。使用结构化输出 (JSON function calling) 确保可靠的数据检索。 |
| **多模型比较仪表板** | 不同预测方法的并排比较教授模型选择技能，这些技能是原始指标单独无法传达的。 | MEDIUM | 交互式 plotly dashboard 比较: XGBoost vs OpenSTEF vs LSTM 用于负荷; LEAR vs DNN vs naive 用于电价。显示残差分布, 按小时的误差热力图, 并突出显示每个模型失败的地方。这是学习发生的地方 — "为什么我的模型在峰值小时失败?" |
| **场景构建器** | 学习者设计自己的市场场景: 改变可再生能源渗透率, 添加储能, 修改需求模式, 观察市场动态变化。 | HIGH | 使用 ASSUME 基于 YAML 的场景配置作为基础。构建基于 notebook 的构建器: (a) 让学习者指定发电机组组成, (b) 从数据加载需求曲线, (c) 运行仿真并比较结果。保存/加载场景预设。预构建场景: "大风日", "夏季高峰", "储能套利"。 |
| **模型可解释性工具** | 理解模型为什么预测某个值比预测本身更有教育意义。SHAP values, feature importance, partial dependence plots。 | MEDIUM | 为树模型集成 SHAP (XGBoost), 为黑盒模型使用 permutation importance。每个预测 notebook 包含 "模型为什么预测这个?" 部分，带 SHAP waterfall plots 显示主要贡献特征。 |
| **带里程碑的引导式学习路径** | 结构化的进展使学习者不会迷失。每个阶段有明确的成功标准并产生工作产物。 | LOW | 匹配 PROJECT.md 的四阶段路径: (1) 热身: 手动 XGBoost → 当 MAE < 阈值时通过; (2) 深入: OpenSTEF + ASSUME 首次仿真 → 当你运行了 7 天仿真时通过; (3) 搭建智能体: RL agent 击败基于规则的基线 → 当累计利润 > 基线时通过; (4) 整合: LLM 可以查询你的系统 → 当自然语言查询返回正确数据时通过。 |
| **端到端交易回测** | "全栈" 体验: 预测 → 投标 → 市场出清 → P&L 计算。学习者看到完整的交易循环运作。 | HIGH | 将 OpenSTEF 预测接入 ASSUME agent 的投标策略。运行多天回测。输出: 累计 P&L chart, 按小时的盈亏热力图, 策略 Sharpe ratio。这是将所有东西联系在一起的顶点功能。 |

### 反功能 (特意不构建的东西)

看似有吸引力但会削弱学习目的、产生维护负担或跨越到生产系统的功能。

| 反功能 | 为什么避免 | 替代做法 |
|--------------|-----------|-------------------|
| **实时市场数据推送** | 需要付费 API 订阅, 引入网络依赖, 将焦点从学习转移到 "保持管道运行"。也进入了生产领域。 | 使用来自 PUDL/IEA/epftoolbox 的静态、版本化数据集。学习者可以下载一次并离线工作。数据新鲜度不是重点 — 理解模式才是。 |
| **自动化真实资金交易执行** | 法律责任, 金融风险, 伦理问题。这是一个学习平台, 不是部署到生产的交易机器人。 | 所有交易都在仿真中 (ASSUME)。在每个 notebook 中明确说明: "这是一个仿真。不涉及真实资金。" |
| **专有数据抓取或网页爬取** | 抓取商业数据源的法律风险。网站变化导致脆弱爬虫损坏的维护负担。 | 仅使用具有明确开放访问条款的来源数据: PUDL (CC-BY-4.0), IEA open data, epftoolbox datasets。清楚记录数据许可证。 |
| **完整 SaaS Web 应用** | 巨大的范围蔓延。Web auth, 用户管理, 数据库扩展, 部署 —— 全部与学习能源 AI 无关。转移了教育内容的精力。 | 保持为 Jupyter notebooks + FastAPI backend + CLI。如果以后需要 web UI, 添加轻量级的 Streamlit/Gradio wrapper, 而不是完整的 React 应用。 |
| **碳市场 / 排放交易** | PROJECT.md 明确将其排除在外。碳市场有不同的动态 (cap-and-trade vs energy-only), 不同的数据源, 不同的监管框架。 | 专注于电力市场。如果成功, 碳市场可以作为阶段 5 的扩展。 |
| **训练大模型 (GPT-scale)** | 违反 "轻量级模型" 约束。需要 GPU 集群、数 TB 数据、数周训练 — 在开发笔记本上无法实现。 | 使用 XGBoost, 小型 LSTM, 和具有适度观测/动作空间的 RL (ASSUME 的默认 agents)。教育价值在于架构和工作流, 而非模型大小。 |
| **图形化投标界面 (拖拽式)** | 复杂的前端工作, 教育回报最小。学习在于代码和策略逻辑, 而非漂亮的 UI。 | 投标策略以 Python 函数/配置表达。如果需要轻量交互性, 使用 Streamlit。 |
| **多用户协作功能** | 用户账户、共享、权限 — 与能源 AI 学习无关的整个产品类别。 | 单用户 Jupyter 环境。如果需要协作, 学习者通过 git 分享 notebooks, 而非内置的平台。 |

## 功能依赖

```
Data Ingestion Pipeline
    ├──requires──> 公开数据源 (PUDL, IEA)
    └──feeds──> Data Cleaning Pipeline
                    ├──feeds──> Load Forecasting (XGBoost)
                    ├──feeds──> Load Forecasting (OpenSTEF)
                    ├──feeds──> Price Forecasting (epftoolbox)
                    └──feeds──> Scenario Builder
                                    └──feeds──> Market Simulation (ASSUME)
                                                    ├──feeds──> Results Visualization
                                                    ├──feeds──> RL Agent Sandbox
                                                    │               └──requires──> TensorBoard 用于学习指标
                                                    ├──feeds──> End-to-End Trading Backtest
                                                    │               ├──requires──> Load Forecasting
                                                    │               ├──requires──> Price Forecasting
                                                    │               └──requires──> Market Simulation
                                                    └──feeds──> LLM Trading Assistant
                                                                    ├──requires──> End-to-End Backtest (用于上下文)
                                                                    └──enhances──> Model Explainability Tools

Multi-Model Comparison Dashboard
    ├──requires──> Load Forecasting (both XGBoost and OpenSTEF)
    └──requires──> Price Forecasting (multiple models)

Model Explainability Tools ──enhances──> Load Forecasting
Model Explainability Tools ──enhances──> Price Forecasting
Model Explainability Tools ──enhances──> RL Agent Sandbox

Guided Learning Path ──wraps──> 以上所有功能按结构化顺序
```

### 依赖说明

- **End-to-End Trading Backtest 需要 Load Forecasting, Price Forecasting, 和 Market Simulation:** 这是集成功能 — 只能在三个支柱都独立工作后构建。它是 PROJECT.md 路线图中的阶段 3 交付物。
- **LLM Trading Assistant 需要 End-to-End Backtest:** 助手需要一个工作的系统来查询。它包装现有功能而非替换它们。这是阶段 4。
- **RL Agent Sandbox 需要 Market Simulation:** ASSUME 提供 RL 基础设施。学习平台添加基于 notebook 的沙盒层用于实验。
- **Scenario Builder enhances Market Simulation:** 场景构建器是 ASSUME YAML 配置之上的 UX 层, 而非独立功能。
- **Model Explainability enhances 所有预测模块:** 可以增量添加 — 从 XGBoost feature importance 开始 (内置), 然后添加 SHAP, 然后为黑盒模型添加 permutation importance。

## MVP 定义

### 启动时带 (v1 — 阶段 1: 热身与基本预测)

最小可行产品 — 验证学习概念所需的。

- [ ] **公开数据接入管道** — 没有数据, 什么都不运行。必须从 PUDL 拉取并产出可用的 pandas DataFrame。
- [ ] **数据清洗管道** — 脏数据破坏模型。必须处理缺失值、时区归一化、训练/测试划分。
- [ ] **负荷预测 (手动 XGBoost)** — 第一个 "我构建了东西" 的时刻。必须产出预测并显示 MAE/RMSE。
- [ ] **基本结果可视化** — 至少: 负荷-vs-预测叠加图和误差分布直方图。
- [ ] **Jupyter Notebook 环境** — "实验台"。必须有在干净机器上 <30 分钟内工作的设置说明。
- [ ] **引导式学习路径 (仅阶段 1)** — 带 markdown 解释、code cells 和反思问题的 notebooks, 用于热身阶段。

### 验证后添加 (v1.x — 阶段 2: 深入预测与市场仿真)

一旦基本预测管道工作后添加的功能。

- [ ] **负荷预测 (OpenSTEF 自动管道)** — 与手动 XGBoost 模型比较。"自动 ML vs 手动" 的比较有很高的教育意义。
- [ ] **电价预测 (epftoolbox)** — 预测的第二个支柱。使用基准模型进行日前电价预测。
- [ ] **市场仿真 (ASSUME 首次运行)** — 使用默认 agents 运行基本的 7 天仿真。看到市场出清运作。
- [ ] **多模型比较仪表板** — 使用 plotly 进行并排预测模型比较。
- [ ] **场景构建器 (基本)** — 通过 ASSUME YAML 配置修改发电组合和需求。
- [ ] **引导式学习路径 (阶段 2)** — 扩展的 notebooks 用于深入阶段。

### 未来考虑 (v2+ — 阶段 3-4)

推迟到预测 + 仿真基础稳固之后的功能。

- [ ] **RL Agent Sandbox** — 修改奖励函数, 观察涌现策略。"酷 AI" 功能 — 仅在基本仿真被理解后有价值。
- [ ] **端到端交易回测** — 顶点: forecast → bid → clear → P&L。将所有东西联系在一起。
- [ ] **模型可解释性工具** — SHAP, feature importance。在学习者构建了多个模型并能比较后更有影响力。
- [ ] **LLM 驱动的交易助手** — 自然语言查询界面。最高的 "惊叹因子" 但最低优先级 — 要求其他一切先工作。

## 功能优先级矩阵

| 功能 | 用户价值 | 实现成本 | 优先级 |
|---------|------------|---------------------|----------|
| 公开数据接入管道 | HIGH | MEDIUM | P1 |
| 数据清洗与预处理 | HIGH | MEDIUM | P1 |
| 负荷预测 (手动 XGBoost) | HIGH | MEDIUM | P1 |
| 基本结果可视化 | HIGH | LOW | P1 |
| Jupyter Notebook 环境 | HIGH | LOW | P1 |
| 引导式学习路径 | MEDIUM | LOW | P1 |
| 负荷预测 (OpenSTEF) | HIGH | MEDIUM | P2 |
| 电价预测 (epftoolbox) | HIGH | MEDIUM | P2 |
| 市场仿真 (ASSUME) | HIGH | HIGH | P2 |
| 多模型比较仪表板 | MEDIUM | MEDIUM | P2 |
| 场景构建器 | MEDIUM | HIGH | P2 |
| RL Agent Sandbox | HIGH | HIGH | P3 |
| 端到端交易回测 | HIGH | HIGH | P3 |
| 模型可解释性工具 | MEDIUM | MEDIUM | P3 |
| LLM 驱动的交易助手 | MEDIUM | MEDIUM | P3 |

**优先级说明:**
- **P1:** 启动时必须。没有这些, 平台不能作为学习工具运作。
- **P2:** 核心工作后添加。这些将平台与 "只是阅读库文档" 区分开来。
- **P3:** 顶点功能。这些使平台卓越 — 在基础稳固后构建。

## 竞品功能分析

由于这是受图迹科技 GeekBidder 商业技术启发的学习平台, 我们通过 "存在什么" vs "我们为学习构建什么" 的镜头比较功能。

| 功能区域 | 商业 (GeekBidder风格) | 学术 (ASSUME/HAMLET raw) | 我们的学习平台 |
|--------------|-------------------------------|------------------------------|----------------------|
| **Data pipeline** | 30TB+ 专有数据, Hadoop/Spark cluster | 要求用户自己获取数据 | 预打包来自 PUDL/IEA 的公开数据集, 一键下载 |
| **Load forecasting** | GeekModel (专有深度状态空间模型) | OpenSTEF (AutoML pipeline) | 手动 XGBoost → OpenSTEF 比较路径 — 学习者构建自己的, 然后看到自动化替代方案 |
| **Price forecasting** | 集成在 GeekBidder OS | epftoolbox 研究基准 | epftoolbox + custom models, 并排比较 dashboard |
| **Market simulation** | GeekBidder OS simulation engine | ASSUME CLI + Python API | ASSUME 配合基于 notebook 的场景构建器和 Grafana dashboards |
| **RL trading agents** | "自动交易机器人" (专有) | ASSUME DRL agents (PPO, TD3, SAC) | ASSUME agents + 用于修改奖励函数的沙盒 notebooks + TensorBoard monitoring |
| **Natural language interface** | "图小记" 对话agent | 无 | LangChain + LLM 查询助手包装所有平台能力 |
| **Learning structure** | 内部培训 (非公开) | 学术论文 + README | 带里程碑、反思问题和每个阶段工作产物的引导式 4 阶段学习路径 |

## 来源

- **ASSUME Framework** (GitHub: assume-framework/assume) — v0.5.6 (Dec 2025). Agent-based electricity market simulation with DRL. Core simulation engine for this platform. [HIGH confidence — 直接检查了仓库]
- **OpenSTEF** (GitHub: OpenSTEF/openstef) — v3.4.93 (Mar 2026). Automated ML pipeline for short-term energy forecasting. Under LF Energy. [HIGH confidence — 直接检查了仓库]
- **epftoolbox** (GitHub: jeslago/epftoolbox) — Electricity price forecasting benchmark with 5 EU/US markets, LEAR + DNN models. Published in Applied Energy 2021. [HIGH confidence — 直接检查了仓库]
- **PUDL** (GitHub: catalyst-cooperative/pudl) — v2026.5.0 (May 2026). Public Utility Data Liberation Project. CC-BY-4.0 licensed US energy data pipeline outputting SQLite/Parquet. [HIGH confidence — 直接检查了仓库]
- **enda** (GitHub: enercoop/enda) — v1.0.4 (Jul 2024). Energy timeseries data manipulation, load forecasting, contract handling. MIT licensed. [HIGH confidence — 直接检查了仓库]
- **HAMLET** (GitHub: tum-ens/HAMLET) — v1.0.1 (Mar 2025). Hierarchical Agent-based Markets for Local Energy Trading. Published in SoftwareX 2025. [HIGH confidence — 直接检查了仓库]
- **PROJECT.md** — Project definition with 4-stage learning roadmap, constraints, and out-of-scope decisions. [HIGH confidence — 主要项目文档]

---

*功能调研: AI-driven electricity trading learning platform (Ellectric)*
*调研日期: 2026-05-20*
