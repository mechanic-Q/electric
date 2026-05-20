# Phase 1: Data Foundation + Basic Prediction - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a working Jupyter-based learning environment where users can: (1) install all dependencies in one command, (2) fetch and clean Chinese electricity load data from local open data platforms (hourly granularity), (3) train an XGBoost load forecasting model with proper temporal validation, and (4) run an end-to-end baseline pipeline (persistence forecast → simulation → P&L) proving all system layers connect. This is the "prove the skeleton" phase — get a full pipeline running before introducing domain-specific frameworks (OpenSTEF, ASSUME) in Phase 2.
</domain>

<decisions>
## Implementation Decisions

### Data Source Selection
- **D-01:** Use **Chinese electricity load data** from local government open data platforms (e.g., 菏泽市公共数据开放网, 广东省公共数据开放平台). Target: **hourly load data** (小时级负荷数据). This aligns with the learning goal of replicating Beijing Tuji's (图迹) domestic electricity trading approach.
- **D-02:** If hourly data is unavailable from open platforms, fall back to epftoolbox's built-in datasets (EPEX/PJM) to keep the pipeline runnable while continuing to search for Chinese data sources. The data loading layer must be abstracted so the source can be swapped without changing downstream code.
- **D-03:** Build a data fetching module that handles the specific format/API of the chosen Chinese data platform. Expect manual download + parse workflow (not a pip-installable package like PUDL). Document the data acquisition steps clearly in the notebook.

### Data Storage & Format
- **D-04:** Parquet as primary data format — portable, columnar, pandas-native, fast read/write without database server.
- **D-05:** Standardized column schema: `timestamp` (datetime64[ns, UTC]), `load_mw` (float64), plus metadata columns (region, data_source). All timestamps in UTC with timezone-aware pandas dtypes.

### Environment Setup
- **D-06:** pip + venv with `requirements.txt` (pinned versions). One-command setup: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`. Target: <30 minutes on clean machine.
- **D-07:** Docker Compose optional (for TimescaleDB + Grafana) — not required for Phase 1. Create skeleton YAML only, mark as "Phase 2 dependency."

### Feature Engineering Approach
- **D-08:** Progressive feature design — start with 3-5 core features (hour, day-of-week, month, is_weekend, lag-24h), validate model works, then add holiday flags, lag-168h, rolling windows. Each feature addition should be its own notebook cell with before/after metric comparison.
- **D-09:** CRITICAL: All scalers (StandardScaler, etc.) fit ONLY on training data using `TimeSeriesSplit`. NEVER call `fit()` on full dataset. This is the #1 pitfall identified in research and must be enforced by the notebook structure itself.

### Notebook Architecture
- **D-10:** Modular structure: thin Jupyter notebooks import from reusable `.py` modules (`pipeline/data_loader.py`, `pipeline/cleaner.py`, `pipeline/features.py`, `pipeline/forecaster.py`). Notebooks are for exploration and visualization; `.py` modules are for production logic.
- **D-11:** Notebook naming convention: `01_data_ingestion.ipynb`, `02_data_cleaning.ipynb`, `03_feature_engineering.ipynb`, `04_load_forecasting.ipynb`, `05_end_to_end_baseline.ipynb`. Sequential, self-documenting.

### End-to-End Baseline
- **D-12:** Baseline uses persistence forecast (yesterday's load = today's prediction) plus a minimal P&L calculation (assume flat price, buy at forecast, settle at actual). No ASSUME dependency — pure Python. Purpose: prove data → predict → trade pipeline works in <50 lines.
- **D-13:** Baseline P&L chart verifies: (a) predictions flow into trading logic, (b) cumulative profit graph renders, (c) pipeline layers are connected. Numerical P&L need not be positive — the point is integration, not profitability.

### Model Evaluation
- **D-14:** Primary metric: **MAE** (Mean Absolute Error) on temporal test split (last 20% of data). Keep it simple and interpretable for learning purposes.

### Visualization
- **D-15:** Use **plotly** for interactive visualizations — load-vs-prediction overlay (zoomable), error distribution, residuals-over-time. Plotly allows hovering to see exact values, which is valuable for learning.

### Claude's Discretion
- Exact XGBoost hyperparameters (n_estimators, max_depth, learning_rate) — start with defaults, tune later
- Error message wording for missing data or failed downloads
- Color scheme and figure sizes for plotly plots
- `requirements.txt` exact structure (flat vs grouped with comments)
- Specific Chinese open data platform to prioritize (research and determine during implementation)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Definition
- `.planning/PROJECT.md` — Core value, constraints, out-of-scope boundaries
- `.planning/REQUIREMENTS.md` — All 24 v1 requirements; Phase 1 covers ENV-01..03, DATA-01..04, PRED-01, VIZ-01

### Technology Stack
- `.planning/research/STACK.md` — Version-pinned stack: Python 3.11, pandas 3.0.3, scikit-learn 1.8.0, XGBoost 3.2.0, plotly 6.7.0

### Pitfalls (CRITICAL reads)
- `.planning/research/PITFALLS.md` — **Look-ahead bias** (scaler on full data, random splits), **spike-as-noise** (log-transforming prices destroys signal), and **no end-to-end early** trap. Phase 1 must actively prevent the first and third.

### Architecture
- `.planning/research/ARCHITECTURE.md` — Layered pipeline: Data Layer → Prediction Layer → Market Layer → Agent Layer. Phase 1 delivers Data Layer + manual Prediction Layer connector.

### Features
- `.planning/research/FEATURES.md` — Table stakes feature list, dependency chain.

### Roadmap
- `.planning/ROADMAP.md` § Phase 1 — 9 requirements, 5 success criteria, MVP mode
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — greenfield project. All code in Phase 1 will be new.

### Established Patterns
- `pipeline/` directory for `.py` modules (established in this phase as project convention)
- `notebooks/` directory for Jupyter exploration (established in this phase)
- `requirements.txt` with pinned versions (established in this phase)

### Integration Points
- Phase 1 `DataLoader` class will be consumed by Phase 2 (OpenSTEF + ASSUME input)
- Phase 1 `cleaned_load.parquet` output schema will be the contract for downstream phases
- Phase 1 `Forecaster.predict()` interface will be replaced by OpenSTEF in Phase 2 — design it as an abstraction
</code_context>

<specifics>
## Specific Ideas

- 你想学图迹科技的实战技术，所以优先使用中国电力市场数据而非美国数据
- 使用 plotly 做交互式可视化，方便学习中探索数据细节
- 评估指标保持简单（仅MAE），降低学习门槛
</specifics>

<deferred>
## Deferred Ideas

- 美国PJM数据 (PUDL) — 作为备用数据源，当中国数据不可用时降级使用
- enda 能源时序数据处理工具 — 研究发现其H2O依赖与项目约束冲突，推迟到Phase 2评估
- 天气数据集成 — 推迟到Phase 2（OpenSTEF自带天气特征工程）
- HAMLET 本地市场仿真 — repo可能不可用（404），优先级低于ASSUME
</deferred>

---
*Phase: 01-data-foundation-basic-prediction*
*Context gathered: 2026-05-20*
