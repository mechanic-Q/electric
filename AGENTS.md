<!-- GSD:project-start source:PROJECT.md -->
## Project

**AI + 电力交易技术学习平台**

一个动手实践性质的AI+电力交易技术学习项目。基于北京图迹科技(GeekBidder)的技术画像——大数据平台 + AI时序预测模型 + 电力市场仿真 + 自动交易智能体——使用开源替代方案搭建可运行的技术原型。目标是帮助开发者掌握"数据获取 → 负荷预测 → 市场仿真 → 自动交易"的完整技术闭环。

This is a hands-on learning platform for AI-driven electricity trading — it's NOT a production trading system. All data is public, all tools are open-source.

**Core Value:** 跑通"公开电力数据接入 → 负荷/电价预测 → 电力市场仿真 → 自动交易策略"的端到端技术闭环。

### Constraints

- **数据**: 仅使用公开可获取的数据集，不涉及商业数据购买
- **工具**: 全部使用开源工具和框架
- **模型**: 轻量级模型为主 (XGBoost, LSTM, 小型RL)，不训练大模型
- **硬件**: 普通开发机可运行 (不需要GPU集群)
- **语言**: Python 3.10+
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### 1. Energy Time-Series Data Processing & Cleaning
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **pandas** | 3.0.3 | Core dataframe operations, time-series indexing, resampling | Universal data science standard. v3.0+ brings native Arrow-backed types, copy-on-write, faster operations. Every energy tool in our stack builds on pandas DataFrames. |
| **enda** | 1.0.5 | Energy-specific timeseries manipulation: gap detection, frequency changes, resampling, contract-to-timeseries conversion | Purpose-built for the RescoopVPP energy forecasting project. Handles TSO/DNO data wrangling and weather data management that generic tools miss. MIT license. |
| **catalystcoop.pudl** | 2026.5.0 | US electricity data ETL pipeline (EIA 860/861/923/930, FERC 1/714, EPA CEMS) | 586★, 11K commits, MIT license. Provides clean, analysis-ready electricity data from US agencies. Eliminates weeks of data wrangling. Also available on Kaggle and AWS Open Data. |
| **polars** | 1.40.1 | High-performance DataFrame alternative for larger datasets | 10-100x faster than pandas on large time-series. Use when PUDL data exceeds pandas memory limits. Rust-backed, lazy evaluation, zero-copy. |
| **numpy** | (via pandas) | Numerical array operations | Core dependency of the entire stack, no direct version pin needed. |
### 2. Electricity Load & Price Forecasting (ML/DL)
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **OpenSTEF** | 3.4.93 | Automated ML pipeline for short-term energy forecasting (load + generation) | LF Energy project, MPL-2.0 license. Production-stable (5/5 maturity). Provides end-to-end pipeline: feature engineering → model training → backtesting → prediction. v4.0.0 in active alpha (43 pre-releases), forward-compatible. |
| **epftoolbox** | git (master) | Electricity price forecasting benchmark with LEAR and DNN models, 5 EU/US market datasets | 352★ academic standard. Provides ready-to-use day-ahead price forecasts for EPEX-BE/FR/DE, NordPool, PJM. Diebold-Mariano and Giacomini-White statistical tests. Install via `pip install git+https://github.com/jeslago/epftoolbox.git`. Apache-2.0 license. |
| **scikit-learn** | 1.8.0 | ML algorithms: RandomForest, GradientBoosting, LinearRegression, preprocessing, metrics | Foundation of the Python ML ecosystem. Used by OpenSTEF internally. Start with sklearn models before moving to DL. |
| **xgboost** | 3.2.0 | Gradient-boosted trees for tabular time-series prediction | Consistently top performer in energy forecasting benchmarks. Handles missing data, feature importance built-in. CPU-optimized — runs on dev hardware. OpenSTEF uses xgboost as default backend. |
| **darts** | 0.44.1 | User-friendly time-series forecasting library (optional) | Clean API wrapping 30+ models (ARIMA, Prophet, N-BEATS, TFT). Good for experimenting beyond OpenSTEF's pipeline. Use when exploring diverse model architectures. |
### 3. Electricity Market Simulation (RL + Agent-Based Modeling)
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **ASSUME** | 0.6.0 | Agent-based electricity market simulation with deep RL agents | Primary simulation framework. 90★, 1.5K commits, published in SoftwareX (2025). Supports DRL agents (PPO, SAC, TD3 via stable-baselines3), multiple market designs (zonal, nodal, redispatch), plug-and-play agent types. Integrated TimescaleDB + Grafana dashboards. AGPL-3.0 license (fine for learning platform). |
| **stable-baselines3** | 2.8.0 | Production-ready RL algorithm implementations (PPO, SAC, TD3, A2C, DQN) | Used internally by ASSUME's learning module. If extending ASSUME agents, interact with sb3 directly. Well-documented, active maintenance. |
| **gymnasium** | 1.3.0 | RL environment API standard | ASSUME's market environment follows the Gymnasium interface pattern, making it extensible with any RL library. |
| **PyPSA** | 1.2.1 | Power system analysis: optimal power flow, network-constrained market clearing | Required by ASSUME for network-based clearing (zonal NTC, nodal, redispatch). Also usable standalone for grid topology analysis. |
| **HAMLET** | 1.0.1 | Local/community energy market simulation (alternative) | MIT license, TUM project. Focused on distribution-level local energy trading with households, PV, EVs, heat pumps. Complements ASSUME's wholesale focus. Use for Phase 2 experimentation with local market designs. Requires Gurobi solver (free academic license). |
- **vs. HAMLET**: ASSUME targets wholesale markets with RL agents; HAMLET targets local/distribution-level markets with more static strategies
- **vs. AMIRIS**: ASSUME is open-source (AGPL), AMIRIS is research-only with restrictive licensing
- **vs. self-built**: 1.5K commits of peer-reviewed market logic — not worth reinventing for a learning platform
### 4. LLM Integration for Natural Language Trading Interfaces
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **langchain** | 1.3.1 | LLM application framework: chain composition, tool calling, agent orchestration | Mature (v1.x), extensive documentation. LangChain v1.0+ is stable with clean abstractions. Tool-calling support enables "query forecast → check market price → suggest trade" chains. |
| **langchain-community** | 0.4.1 | Community model integrations and tools | Required for Ollama integration and specific model providers. |
| **ollama** | 0.6.2 | Local LLM serving (no cloud API needed) | Runs models like Qwen 2.5, Llama 3, DeepSeek locally on dev hardware. No API keys, no rate limits, no data privacy concerns — critical for a learning platform. |
| **sentence-transformers** | 5.5.0 | Text embeddings for semantic search over trading docs and market reports | Enables "find similar trading scenarios" and RAG (retrieval-augmented generation) for domain knowledge. |
| **chromadb** | 1.5.9 | Lightweight vector database for RAG embeddings | In-process, no server needed. Stores embedded trading documents, electricity market regulations, historical scenario descriptions. |
- **Phase 1-3**: No LLM — focus on core forecasting and simulation
- **Phase 4**: Add LangChain + Ollama with a local model (e.g., Qwen2.5-7B or DeepSeek-R1-Distill-7B) for:
- **Model choice**: Qwen2.5-7B-Instruct (strong Chinese+English bilingual, runs on 16GB RAM with 4-bit quantization)
### 5. Data Pipeline & API Serving
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **FastAPI** | 0.136.1 | REST API framework (async, auto-docs, type-safe) | Modern standard for ML API serving. Automatic OpenAPI docs, Pydantic validation, async support. Far better DX than Flask for data-heavy endpoints. |
| **uvicorn** | 0.47.0 | ASGI server for FastAPI | Standard production server. Single-worker mode sufficient for learning platform. |
| **pydantic** | 2.13.4 | Data validation and settings management | Used by FastAPI (and ASSUME). v2 is Rust-backed (pydantic-core), 5-50x faster than v1. |
| **MLflow** | 3.12.0 | ML experiment tracking, model registry, deployment | Tracks forecasting experiments (hyperparameters, metrics, artifacts). OpenSTEF has optional MLflow integration (`pip install openstef[mlflow-full]`). |
| **optuna** | 4.8.0 | Hyperparameter optimization | Used with XGBoost and sklearn models. More Pythonic and faster than GridSearchCV. Supports pruning, visualization. |
| **jupyter** | 1.1.1 | Interactive notebooks for exploration and learning | Primary development interface for Phases 1-2. All tutorials from ASSUME, OpenSTEF, and epftoolbox are Jupyter-based. |
| **matplotlib** | 3.10.9 | Static visualization | Core plotting. Used by all energy libraries internally. |
| **plotly** | 6.7.0 | Interactive visualization | For dashboards and interactive time-series exploration. Complements matplotlib for web display. |
### Supporting Infrastructure
| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| **Python** | 3.11+ | Runtime | OpenSTEF requires ≥3.11 (overrides PROJECT.md's 3.10+ minimum). ASSUME supports 3.10-3.14. Pin to 3.11 for maximum compatibility. |
| **pip** | latest | Package manager | Standard. Use `pip-tools` (pip-compile) for lock files if dependency conflicts arise. |
| **venv** / **conda** | — | Virtual environment | venv is simpler and sufficient. Use conda only if Windows + OpenSTEF causes pywin32 conflicts (documented OpenSTEF issue). |
| **git** | — | Version control | Required for cloning ASSUME, epftoolbox, HAMLET. |
| **Docker** | — | ASSUME TimescaleDB + Grafana | Optional: `docker compose up -d` in ASSUME repo for database-backed simulation analysis. |
## Installation
# Create and activate virtual environment
# ---- Dimension 1: Data Processing ----
# PUDL data (install + download data separately)
# ---- Dimension 2: Forecasting ----
# epftoolbox — install from GitHub (not on PyPI)
# ---- Dimension 3: Market Simulation ----
# HAMLET — clone and install separately (requires Gurobi solver)
# git clone https://github.com/tum-ens/HAMLET.git
# ---- Dimension 4: LLM Integration (install in Phase 4) ----
# ---- Dimension 5: API & Pipeline ----
# ---- Development & Visualization ----
# ---- Optional: Workflow orchestration (Phase 4) ----
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Data processing | enda + pandas | **dask** | Dask adds distributed complexity unnecessary for a learning platform. pandas 3.0's Arrow backend handles our data sizes. Use polars if pandas is too slow. |
| Data processing | enda | **tsfresh** | tsfresh is for automated feature extraction from time series. enda is more energy-domain-specific (contracts, TSO data). Can use both if needed. |
| Forecasting | OpenSTEF | **sktime** | sktime is a general time-series ML framework. OpenSTEF is purpose-built for energy forecasting with domain-specific pipelines (weather features, holiday calendars, load decomposition). Use sktime if building custom prediction workflows outside OpenSTEF's scope. |
| Forecasting | XGBoost | **LightGBM** | Both are excellent. XGBoost is OpenSTEF's default and has better documentation for energy use cases. LightGBM may be slightly faster on very large datasets. |
| Forecasting | Darts | **Prophet** | Prophet is essentially unmaintained (last major release 2023). Darts has a cleaner API, 30+ model backends, and active development (2026 releases). |
| Market simulation | ASSUME | **AMIRIS** | AMIRIS (DLR) is a German research ABM but has restrictive licensing and less RL integration. ASSUME is fully open-source (AGPL-3.0) with built-in DRL. |
| Market simulation | ASSUME | **GridLAB-D** | GridLAB-D focuses on distribution grid physics, not market dynamics. Wrong level of abstraction for trading simulation. |
| LLM framework | LangChain | **LlamaIndex** (0.14.22) | LlamaIndex excels at RAG and document indexing. LangChain v1 is better for agent orchestration and tool-calling chains. Both can coexist — LlamaIndex for document retrieval, LangChain for agent logic. |
| LLM framework | LangChain | **pydantic-ai** (1.98.0) | Newer, cleaner API, but less mature ecosystem and fewer energy-domain examples. Consider for Phase 4+ if LangChain complexity becomes an issue. |
| API | FastAPI | **Flask** | Flask lacks native async, automatic OpenAPI docs, and Pydantic integration. FastAPI's type-driven development catches bugs at startup, not runtime. |
| API | FastAPI | **Django REST** | Django's ORM and admin are overkill for a data-science API. FastAPI is lighter, faster, and better suited for ML model serving. |
| Pipeline orchestration | Manual scripts | **Apache Airflow** | Airflow requires a scheduler, database, and web server. Prefect 3.x is lighter, Pythonic, and can run locally. Only add orchestration in Phase 4 when data refresh needs scheduling. |
| Pipeline orchestration | Manual scripts | **Kedro** (1.3.1) | Kedro is excellent for structuring data science projects but adds a learning curve. Consider for Phase 3+ if the pipeline grows complex. |
| RL library | stable-baselines3 | **RLlib** (Ray) | RLlib requires Ray cluster setup. sb3 is single-machine, simpler, and what ASSUME uses internally. |
| Visualization | plotly | **Dash** | Plotly alone is sufficient for Jupyter exploration. Use FastAPI + plotly JSON for web dashboards. Dash adds a server dependency that overlaps with FastAPI. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **TensorFlow / Keras** (as primary DL framework) | Heavier dependency, steeper learning curve. PyTorch is already pulled in by ASSUME's RL module. Two DL frameworks = doubled dependency weight. | PyTorch (via ASSUME) + scikit-learn/XGBoost for non-DL models |
| **Prophet** (Facebook/Meta) | Effectively unmaintained since 2023. No Python 3.12+ wheels. Community has moved to Darts/Nixtla. | Darts (wraps multiple models including Prophet if needed) |
| **Apache Airflow** | Requires persistent scheduler, database, and webserver. Massive overkill for a single-machine learning platform. | Manual scripts in Phase 1-3, Prefect in Phase 4 if needed |
| **Django / Django REST Framework** | Full-stack web framework with ORM, templates, auth — 90% unused for a data API. | FastAPI — built for API-first, ML-serving use cases |
| **pipenv** | Slow resolution, abandoned by maintainers, inconsistent lock behavior. | pip + venv (simple) or Poetry if you need lock files |
| **H2O** (as primary ML backend) | enda uses H2O as an optional backend, but it's a heavy JVM-based dependency. Not needed for our scale. | enda's scikit-learn backend is sufficient |
| **Ray / Ray Tune** | Distributed computing framework. Adds cluster complexity for no benefit on a single dev machine. | Optuna for hyperparameter tuning, manual parallelization with joblib if needed |
| **Kafka / message queues** | Event-driven streaming architecture for real-time trading. Out of scope — we use historical data, not live feeds. | Simple script orchestration and FastAPI endpoints |
| **Numba / Cython** | Premature optimization. Our data volumes (<100GB) and model sizes don't need compiled extensions. | pandas 3.0's Arrow backend + polars for speed when needed |
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| openstef 3.4.93 | Python ≥3.11, <3.13 | Requires Python 3.11+. Does NOT support 3.10. This is the floor. |
| openstef 4.0.0aX | Python ≥3.11 | Alpha pre-releases available. Expect breaking changes. Pin to 3.4.93 for Phase 1-2. |
| ASSUME 0.6.0 | Python 3.10-3.14 | Also requires PyTorch (CPU or CUDA), stable-baselines3 |
| ASSUME 0.6.0 + openstef 3.4.93 | Both require Python 3.11+ | Python 3.11 is the common denominator |
| enda 1.0.5 | Python ≥3.10 | Compatibility warning: uses statsmodels, may conflict with newer scipy |
| epftoolbox (git) | Python 3.9-3.11, TensorFlow | Old dependency on TensorFlow may conflict with PyTorch. Install in separate venv or use only its datasets/benchmark code |
| langchain 1.3.1 + ollama 0.6.2 | Python ≥3.10 | Both well-maintained, no known conflicts |
| pandas 3.0.3 | Python ≥3.10 | Arrow-backed; may break packages that rely on deprecated pandas APIs |
| PyPSA 1.2.1 | Python ≥3.10 | Required by ASSUME[network]. Optional for standalone use. |
## Stack Patterns by Phase
- Core: pandas + scikit-learn + xgboost + matplotlib
- Data: PUDL (via Kaggle or AWS) or IEA data
- Environment: Jupyter notebooks
- Because: Fastest path to a working prediction model without framework overhead
- Add: OpenSTEF + ASSUME + epftoolbox (datasets only)
- Workflow: Transition from notebooks to .py scripts
- Because: Introduce domain-specific tools after fundamentals are solid
- Add: stable-baselines3 direct usage, optuna for hyperparameter tuning
- Integration: Connect OpenSTEF predictions → ASSUME agent bidding
- Because: Customize RL agents beyond ASSUME defaults
- Add: FastAPI + LangChain + Ollama + chromadb + MLflow
- Deliverable: Unified API that queries forecasts, runs simulations, and accepts natural language commands
- Because: LLM and API are integration-layer concerns — build them last after core logic is stable
## Sources
- **PyPI** — All version numbers verified via `pip index versions` on 2026-05-20 (HIGH confidence)
- **GitHub repos** — README and release pages fetched directly:
- **Published papers**: ASSUME (SoftwareX 2025), HAMLET (SoftwareX 2025), epftoolbox (Applied Energy 2021) — peer-reviewed validation of tool quality
- **PROJECT.md** — Constraints and learning roadmap from project initialization (HIGH confidence)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- workflow-start source:SillySpec + Karpathy -->
## Workflow

本项目使用 **SillySpec** + **Karpathy Guidelines** 组合驱动开发。GSD 资产保留在 `.planning/` 中作为历史参考。

### SillySpec 命令入口

- `/sillyspec:scan` — 代码库扫描（棕地项目启动）
- `/sillyspec:brainstorm "需求"` — 需求探索 + 规范生成
- `/sillyspec:plan` — 实现计划（文件路径 + Wave 分组）
- `/sillyspec:execute` — TDD 执行（子代理并行）
- `/sillyspec:verify` — 验证（对照规范 + 测试套件）
- `/sillyspec:archive` — 归档到 knowledge/
- `/sillyspec:quick` — 小修小补，跳过完整流程
- `/sillyspec:explore` — 自由思考、调研
- `/sillyspec:continue` — 自动下一步
- `/sillyspec:resume` — 中断恢复
- `/sillyspec:status` — 查看进度

### Karpathy 行为准则（已注入 .opencode/karpathy-guidelines.md）

1. **Think Before Coding** — 不假设、不隐藏混淆、暴露权衡
2. **Simplicity First** — 最少代码解决问题，无推测性功能
3. **Surgical Changes** — 只改必要的地方，匹配已有风格
4. **Goal-Driven Execution** — 定义成功标准，循环验证直到通过

### 历史 GSD 资产

`.planning/` 目录中的 ROADMAP.md、REQUIREMENTS.md 和 phase plans 保留为只读参考。新阶段执行时，由 SillySpec brainstorm 读取并转化为 SillySpec 规范的 design.md + tasks.md。

### CLI 辅助（可选）

```bash
sillyspec progress show    # 查看项目状态
sillyspec run brainstorm   # 需求探索
sillyspec run plan         # 实现计划
sillyspec setup            # 安装 MCP 工具增强
```
<!-- workflow-end -->


<!-- profile-start -->
## Developer Profile

> Profile not yet configured.
<!-- profile-end -->
