# 技术栈调研

**领域:** AI驱动的电力交易学习平台
**调研日期:** 2026-05-20
**置信度:** HIGH

## 推荐技术栈

### 1. 能源时序数据处理与清洗

| Technology | Version | 用途 | 推荐原因 |
|------------|---------|---------|-----------------|
| **pandas** | 3.0.3 | 核心 DataFrame 操作, 时序索引, 重采样 | 通用数据科学标准。v3.0+ 带来原生 Arrow 后端类型, copy-on-write, 更快的操作。我们技术栈中的每个能源工具都构建在 pandas DataFrames 之上。 |
| **enda** | 1.0.5 | 能源特定的时序操作: 缺失检测, 频率变更, 重采样, 合同到时序转换 | 为 RescoopVPP 能源预测项目专门构建。处理 TSO/DNO 数据整理和天气数据管理，这些是通用工具缺失的。MIT license。 |
| **catalystcoop.pudl** | 2026.5.0 | 美国电力数据 ETL 管道 (EIA 860/861/923/930, FERC 1/714, EPA CEMS) | 586★, 11K commits, MIT license。提供来自美国机构的干净、分析就绪的电力数据。消除了数周的数据整理工作。也可在 Kaggle 和 AWS Open Data 上获取。 |
| **polars** | 1.40.1 | 高性能 DataFrame 替代方案，用于更大数据集 | 比 pandas 在大型时序数据上快 10-100 倍。当 PUDL 数据超出 pandas 内存限制时使用。Rust 后端, 惰性求值, 零拷贝。 |
| **numpy** | (via pandas) | 数值数组操作 | 整个技术栈的核心依赖，无需直接版本锁定。 |

**数据源说明:** 对于中国电力数据，用从国家能源局统计发布和菏泽市公共数据开放网手动接入来补充 PUDL。没有中国能源数据的 Python 包 —— 使用 `pandas` + `requests`/`httpx` 进行自定义抓取。

### 2. 电力负荷与电价预测 (ML/DL)

| Technology | Version | 用途 | 推荐原因 |
|------------|---------|---------|-----------------|
| **OpenSTEF** | 3.4.93 | 短期能源预测的自动化 ML 管道 (负荷 + 发电) | LF Energy 项目, MPL-2.0 license。生产稳定 (5/5 成熟度)。提供端到端管道: 特征工程 → 模型训练 → 回测 → 预测。v4.0.0 处于活跃 alpha 阶段 (43 个预发布), 向前兼容。 |
| **epftoolbox** | git (master) | 电价预测基准测试，含 LEAR 和 DNN 模型, 5个 EU/US 市场数据集 | 352★ 学术标准。提供 EPEX-BE/FR/DE, NordPool, PJM 的即用型日前电价预测。Diebold-Mariano 和 Giacomini-White 统计检验。通过 `pip install git+https://github.com/jeslago/epftoolbox.git` 安装。Apache-2.0 license。 |
| **scikit-learn** | 1.8.0 | ML 算法: RandomForest, GradientBoosting, LinearRegression, preprocessing, metrics | Python ML 生态系统的基础。被 OpenSTEF 内部使用。在转向 DL 之前先用 sklearn 模型。 |
| **xgboost** | 3.2.0 | 用于表格时序预测的梯度提升树 | 在能源预测基准测试中始终表现最佳。处理缺失数据, 内置特征重要性。CPU 优化 — 在开发硬件上运行。OpenSTEF 使用 xgboost 作为默认后端。 |
| **darts** | 0.44.1 | 用户友好的时序预测库 (可选) | 干净的 API 包装 30+ 模型 (ARIMA, Prophet, N-BEATS, TFT)。适合在 OpenSTEF 管道之外进行实验。在探索多样化模型架构时使用。 |

**模型策略 (根据 PROJECT.md 约束):**
1. **阶段 1-2**: XGBoost + scikit-learn (快速迭代, 低硬件需求)
2. **阶段 3-4**: 随着复杂度增加，添加 Darts + 可选的 LSTM/PyTorch 模型
3. **始终**: OpenSTEF 作为生产风格管道的参考实现

### 3. 电力市场仿真 (RL + 基于智能体的建模)

| Technology | Version | 用途 | 推荐原因 |
|------------|---------|---------|-----------------|
| **ASSUME** | 0.6.0 | 基于智能体的电力市场仿真，含深度 RL 智能体 | 主要仿真框架。90★, 1.5K commits, 发表于 SoftwareX (2025)。支持 DRL agents (PPO, SAC, TD3 via stable-baselines3), 多种市场设计 (zonal, nodal, redispatch), 即插即用的智能体类型。集成 TimescaleDB + Grafana dashboards。AGPL-3.0 license (适用于学习平台)。 |
| **stable-baselines3** | 2.8.0 | 生产就绪的 RL 算法实现 (PPO, SAC, TD3, A2C, DQN) | 被 ASSUME 的学习模块内部使用。如果扩展 ASSUME agents, 直接与 sb3 交互。文档完善, 活跃维护。 |
| **gymnasium** | 1.3.0 | RL 环境 API 标准 | ASSUME 的市场环境遵循 Gymnasium 接口模式，使其可与任何 RL 库扩展。 |
| **PyPSA** | 1.2.1 | 电力系统分析: optimal power flow, 网络约束市场出清 | ASSUME 需要用于基于网络的出清 (zonal NTC, nodal, redispatch)。也可独立用于电网拓扑分析。 |
| **HAMLET** | 1.0.1 | 本地/社区能源市场仿真 (替代方案) | MIT license, TUM 项目。专注于配电网级别的本地能源交易，含家庭、光伏、EV、热泵。补充 ASSUME 的批发市场关注。用于阶段 2 本地市场设计的实验。需要 Gurobi solver (免费学术 license)。 |

**为什么 ASSUME 作为主要框架优于替代方案:**
- **vs. HAMLET**: ASSUME 针对批发市场使用 RL agents; HAMLET 针对本地/配电网级别市场使用更静态的策略
- **vs. AMIRIS**: ASSUME 是开源的 (AGPL), AMIRIS 仅供研究使用且许可证受限
- **vs. 自己构建**: 1.5K commits 的同行评审市场逻辑 —— 不值得为学习平台重新发明

### 4. 用于自然语言交易界面的 LLM 集成

| Technology | Version | 用途 | 推荐原因 |
|------------|---------|---------|-----------------|
| **langchain** | 1.3.1 | LLM 应用框架: chain 组合, tool calling, agent 编排 | 成熟 (v1.x), 文档丰富。LangChain v1.0+ 稳定且抽象干净。Tool-calling 支持实现 "查询预测 → 检查市场价格 → 建议交易" 链。 |
| **langchain-community** | 0.4.1 | 社区模型集成和工具 | 需要用于 Ollama 集成和特定模型提供者。 |
| **ollama** | 0.6.2 | 本地 LLM 服务 (无需云端 API) | 在开发硬件上本地运行 Qwen 2.5, Llama 3, DeepSeek 等模型。无 API key, 无频率限制, 无数据隐私担忧 —— 对学习平台至关重要。 |
| **sentence-transformers** | 5.5.0 | 用于交易文档和市场报告语义搜索的文本嵌入 | 实现 "查找类似交易场景" 和用于领域知识的 RAG (检索增强生成)。 |
| **chromadb** | 1.5.9 | 用于 RAG 嵌入的轻量向量数据库 | 进程内运行, 无需服务器。存储嵌入化的交易文档、电力市场法规、历史场景描述。 |

**LLM 策略:**
- **阶段 1-3**: 不使用 LLM — 专注于核心预测和仿真
- **阶段 4**: 添加 LangChain + Ollama 配合本地模型 (例如 Qwen2.5-7B 或 DeepSeek-R1-Distill-7B) 用于:
  - 自然语言查询: "显示 PJM 明天峰值负荷预测"
  - 交易命令解析: "第 8-16 小时投标 50MW 价格 $35/MWh"
  - 场景解释: "为什么昨天下午价格飙升?"
- **模型选择**: Qwen2.5-7B-Instruct (中英双语能力强, 在 16GB RAM 上以 4-bit quantization 运行)

### 5. 数据管道与 API 服务

| Technology | Version | 用途 | 推荐原因 |
|------------|---------|---------|-----------------|
| **FastAPI** | 0.136.1 | REST API 框架 (async, auto-docs, type-safe) | ML API 服务的现代标准。自动 OpenAPI docs, Pydantic validation, async 支持。在数据密集型端点上比 Flask 开发体验好得多。 |
| **uvicorn** | 0.47.0 | FastAPI 的 ASGI 服务器 | 标准生产服务器。单 worker 模式对学习平台足够。 |
| **pydantic** | 2.13.4 | 数据验证和设置管理 | 被 FastAPI (和 ASSUME) 使用。v2 是 Rust 后端 (pydantic-core), 比 v1 快 5-50 倍。 |
| **MLflow** | 3.12.0 | ML 实验跟踪, 模型注册, 部署 | 跟踪预测实验 (超参数, 指标, 产物)。OpenSTEF 有可选的 MLflow 集成 (`pip install openstef[mlflow-full]`)。 |
| **optuna** | 4.8.0 | 超参数优化 | 用于 XGBoost 和 sklearn 模型。比 GridSearchCV 更 Pythonic 且更快。支持 pruning, visualization。 |
| **jupyter** | 1.1.1 | 用于探索和学习的交互式 notebooks | 阶段 1-2 的主要开发界面。ASSUME, OpenSTEF 和 epftoolbox 的所有教程都是基于 Jupyter 的。 |
| **matplotlib** | 3.10.9 | 静态可视化 | 核心绘图。被所有能源库内部使用。 |
| **plotly** | 6.7.0 | 交互式可视化 | 用于仪表板和交互式时序探索。补充 matplotlib 用于 web 展示。 |

### 支撑基础设施

| Tool | Version | 用途 | 备注 |
|------|---------|---------|-------|
| **Python** | 3.11+ | 运行时 | OpenSTEF 需要 ≥3.11 (覆盖 PROJECT.md 的 3.10+ 最低要求)。ASSUME 支持 3.10-3.14。锁定 3.11 以获得最大兼容性。 |
| **pip** | latest | 包管理器 | 标准。如果出现依赖冲突，使用 `pip-tools` (pip-compile) 生成 lock files。 |
| **venv** / **conda** | — | 虚拟环境 | venv 更简单且足够。仅当 Windows + OpenSTEF 导致 pywin32 冲突时使用 conda (文档记录的 OpenSTEF 问题)。 |
| **git** | — | 版本控制 | 用于克隆 ASSUME, epftoolbox, HAMLET。 |
| **Docker** | — | ASSUME TimescaleDB + Grafana | 可选: 在 ASSUME 仓库中 `docker compose up -d` 用于基于数据库的仿真分析。 |

## 安装

```bash
# 创建并激活虚拟环境
python3.11 -m venv .venv && source .venv/bin/activate

# ---- 维度 1: 数据处理 ----
pip install pandas==3.0.3 polars==1.40.1
pip install enda==1.0.5
# PUDL 数据 (安装 + 单独下载数据)
pip install catalystcoop.pudl==2026.5.0

# ---- 维度 2: 预测 ----
pip install scikit-learn==1.8.0 xgboost==3.2.0
pip install openstef==3.4.93
pip install darts==0.44.1  # 可选, 用于模型实验
# epftoolbox — 从 GitHub 安装 (不在 PyPI 上)
pip install git+https://github.com/jeslago/epftoolbox.git

# ---- 维度 3: 市场仿真 ----
pip install 'assume-framework[learning]'==0.6.0
pip install stable-baselines3==2.8.0 gymnasium==1.3.0
# HAMLET — 单独克隆和安装 (需要 Gurobi solver)
# git clone https://github.com/tum-ens/HAMLET.git

# ---- 维度 4: LLM 集成 (在阶段 4 安装) ----
pip install langchain==1.3.1 langchain-community==0.4.1
pip install ollama==0.6.2 sentence-transformers==5.5.0 chromadb==1.5.9

# ---- 维度 5: API & 管道 ----
pip install fastapi==0.136.1 uvicorn==0.47.0 pydantic==2.13.4
pip install mlflow==3.12.0 optuna==4.8.0

# ---- 开发 & 可视化 ----
pip install jupyter==1.1.1 matplotlib==3.10.9 plotly==6.7.0 seaborn==0.13.2

# ---- 可选: 工作流编排 (阶段 4) ----
pip install prefect==3.7.1  # 用于定时数据刷新管道
```

## 考虑过的替代方案

| 类别 | 推荐 | 替代方案 | 为什么不选 |
|----------|-------------|-------------|---------|
| Data processing | enda + pandas | **dask** | Dask 增加了学习平台不必要的分布式复杂性。pandas 3.0 的 Arrow 后端可以处理我们的数据大小。如果 pandas 太慢，使用 polars。 |
| Data processing | enda | **tsfresh** | tsfresh 用于从时序中自动提取特征。enda 更能源领域特定 (合同, TSO 数据)。需要时可以两者都用。 |
| Forecasting | OpenSTEF | **sktime** | sktime 是通用时序 ML 框架。OpenSTEF 专为能源预测构建，具有领域特定的管道 (天气特征, 节假日日历, 负荷分解)。如果在 OpenSTEF 范围之外构建自定义预测工作流，使用 sktime。 |
| Forecasting | XGBoost | **LightGBM** | 两者都很优秀。XGBoost 是 OpenSTEF 的默认选择，并且在能源用例上有更好的文档。LightGBM 在非常大的数据集上可能稍快。 |
| Forecasting | Darts | **Prophet** | Prophet 实际上已不再维护 (最后主要发布在 2023 年)。Darts 有更干净的 API, 30+ 模型后端, 且活跃开发 (2026 年发布)。 |
| Market simulation | ASSUME | **AMIRIS** | AMIRIS (DLR) 是德国研究的 ABM 但许可证受限且 RL 集成较少。ASSUME 完全开源 (AGPL-3.0) 并内置 DRL。 |
| Market simulation | ASSUME | **GridLAB-D** | GridLAB-D 专注于配电网物理，而非市场动态。对于交易仿真来说抽象层级错误。 |
| LLM framework | LangChain | **LlamaIndex** (0.14.22) | LlamaIndex 擅长 RAG 和文档索引。LangChain v1 更好地用于 agent 编排和 tool-calling 链。两者可以共存 — LlamaIndex 用于文档检索, LangChain 用于 agent 逻辑。 |
| LLM framework | LangChain | **pydantic-ai** (1.98.0) | 更新, 更干净的 API, 但生态系统较不成熟且能源领域示例较少。如果 LangChain 复杂度成为问题，在阶段 4+ 考虑。 |
| API | FastAPI | **Flask** | Flask 缺乏原生 async, 自动 OpenAPI docs, 和 Pydantic 集成。FastAPI 的类型驱动开发在启动时捕获 bug, 而非运行时。 |
| API | FastAPI | **Django REST** | Django 的 ORM 和 admin 对于数据科学 API 来说过度了。FastAPI 更轻量、更快, 更适合 ML 模型服务。 |
| Pipeline orchestration | Manual scripts | **Apache Airflow** | Airflow 需要 scheduler, 数据库和 web 服务器。Prefect 3.x 更轻量、更 Pythonic, 可以本地运行。仅在阶段 4 数据刷新需要调度时添加编排。 |
| Pipeline orchestration | Manual scripts | **Kedro** (1.3.1) | Kedro 在结构化数据科学项目方面优秀但增加了学习曲线。如果管道变得复杂，在阶段 3+ 考虑。 |
| RL library | stable-baselines3 | **RLlib** (Ray) | RLlib 需要 Ray 集群设置。sb3 是单机、更简单, 且 ASSUME 内部使用。 |
| Visualization | plotly | **Dash** | Plotly 单独对于 Jupyter 探索足够了。使用 FastAPI + plotly JSON 用于 web 仪表板。Dash 添加了与 FastAPI 重叠的服务器依赖。 |

## 不应使用什么

| 避免 | 原因 | 使用替代 |
|-------|-----|-------------|
| **TensorFlow / Keras** (作为主要 DL 框架) | 更重的依赖, 更陡的学习曲线。PyTorch 已被 ASSUME 的 RL 模块引入。两个 DL 框架 = 双倍的依赖负担。 | PyTorch (via ASSUME) + scikit-learn/XGBoost 用于非 DL 模型 |
| **Prophet** (Facebook/Meta) | 自 2023 年以来实际上已停止维护。没有 Python 3.12+ 的 wheels。社区已转向 Darts/Nixtla。 | Darts (包装了包括 Prophet 在内的多种模型如果需要) |
| **Apache Airflow** | 需要持久化的 scheduler, 数据库和 webserver。对于单机学习平台来说严重过度。 | 阶段 1-3 手动脚本, 阶段 4 如需要则用 Prefect |
| **Django / Django REST Framework** | 全栈 web 框架带 ORM, 模板, auth — 90% 对数据 API 无用。 | FastAPI — 专为 API-first, ML-serving 场景构建 |
| **pipenv** | 解析慢, 被维护者放弃, 不一致的 lock 行为。 | pip + venv (简单) 或如果需要 lock files 则用 Poetry |
| **H2O** (作为主要 ML 后端) | enda 使用 H2O 作为可选后端, 但它是重型的 JVM 依赖。对我们的规模不需要。 | enda 的 scikit-learn 后端足够 |
| **Ray / Ray Tune** | 分布式计算框架。在单台开发机上增加集群复杂度而无好处。 | Optuna 用于超参数调优, 如需要则用 joblib 手动并行 |
| **Kafka / 消息队列** | 事件驱动的流架构用于实时交易。超出范围 — 我们使用历史数据, 而非实时流。 | 简单的脚本编排和 FastAPI 端点 |
| **Numba / Cython** | 过早优化。我们的数据量 (<100GB) 和模型大小不需要编译扩展。 | pandas 3.0 的 Arrow 后端 + polars 在需要时加速 |

## 版本兼容性

| Package A | 兼容 | 备注 |
|-----------|-----------------|-------|
| openstef 3.4.93 | Python ≥3.11, <3.13 | 需要 Python 3.11+。不支持 3.10。这是最低要求。 |
| openstef 4.0.0aX | Python ≥3.11 | Alpha 预发布可用。预计有破坏性变更。阶段 1-2 锁定到 3.4.93。 |
| ASSUME 0.6.0 | Python 3.10-3.14 | 还需要 PyTorch (CPU or CUDA), stable-baselines3 |
| ASSUME 0.6.0 + openstef 3.4.93 | 两者都需要 Python 3.11+ | Python 3.11 是共同分母 |
| enda 1.0.5 | Python ≥3.10 | 兼容性警告: 使用 statsmodels, 可能与较新的 scipy 冲突 |
| epftoolbox (git) | Python 3.9-3.11, TensorFlow | 旧的 TensorFlow 依赖可能与 PyTorch 冲突。在单独的 venv 中安装或仅使用其数据集/基准测试代码 |
| langchain 1.3.1 + ollama 0.6.2 | Python ≥3.10 | 两者维护良好, 无已知冲突 |
| pandas 3.0.3 | Python ≥3.10 | Arrow 后端; 可能会破坏依赖已弃用 pandas API 的包 |
| PyPSA 1.2.1 | Python ≥3.10 | ASSUME[network] 必需。独立使用可选。 |

**关键兼容性说明:** `epftoolbox` 自 2023 年以来未更新，且依赖 TensorFlow (与 PyTorch 冲突)。**建议**: 不要在同一环境中安装 epftoolbox。相反，单独克隆它并仅使用其数据集和基准参考预测。LEAR 模型可以用 scikit-learn 重新实现 (它本质上是 LASSO regression)。

## 各阶段技术栈模式

**阶段 1 (热身与基础预测):**
- 核心: pandas + scikit-learn + xgboost + matplotlib
- 数据: PUDL (via Kaggle or AWS) 或 IEA 数据
- 环境: Jupyter notebooks
- 原因: 最快路径到可工作的预测模型，无框架开销

**阶段 2 (深入预测与市场仿真):**
- 添加: OpenSTEF + ASSUME + epftoolbox (仅数据集)
- 工作流: 从 notebooks 过渡到 .py scripts
- 原因: 基础扎实后引入领域特定工具

**阶段 3 (交易智能体):**
- 添加: stable-baselines3 直接使用, optuna 用于超参数调优
- 集成: 连接 OpenSTEF 预测 → ASSUME agent bidding
- 原因: 在 ASSUME 默认之外自定义 RL agents

**阶段 4 (整合与大模型赋能):**
- 添加: FastAPI + LangChain + Ollama + chromadb + MLflow
- 交付物: 统一 API 查询预测、运行仿真、接受自然语言命令
- 原因: LLM 和 API 是集成层关注点 — 在核心逻辑稳定后最后构建

## 来源

- **PyPI** — 所有版本号在 2026-05-20 通过 `pip index versions` 验证 (HIGH confidence)
- **GitHub repos** — 直接获取的 README 和发布页面:
  - `github.com/assume-framework/assume` — v0.6.0, AGPL-3.0, 90★ (HIGH confidence)
  - `github.com/OpenSTEF/openstef` — v3.4.93, MPL-2.0, 143★, LF Energy project (HIGH confidence)
  - `github.com/enercoop/enda` — v1.0.5, MIT, 16★ (HIGH confidence)
  - `github.com/tum-ens/HAMLET` — v1.0.1, MIT, 24★ (HIGH confidence)
  - `github.com/jeslago/epftoolbox` — git-only, Apache-2.0, 352★ (HIGH confidence)
  - `github.com/catalyst-cooperative/pudl` — v2026.5.0, MIT, 586★ (HIGH confidence)
- **已发表论文**: ASSUME (SoftwareX 2025), HAMLET (SoftwareX 2025), epftoolbox (Applied Energy 2021) — 工具质量的同行评审验证
- **PROJECT.md** — 项目初始化时的约束和学习路线图 (HIGH confidence)

---

*技术栈调研: AI + 电力交易技术学习平台*
*调研日期: 2026-05-20*
