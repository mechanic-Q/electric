# Walking Skeleton — Ellectric (AI + 电力交易技术学习平台)

**Phase:** 1
**Generated:** 2026-05-20

## Capability Proven End-to-End

A learner runs `setup.sh`, opens `notebooks/05_end_to_end_baseline.ipynb`, runs all cells, and sees Chinese OWID energy data loaded from the internet, cleaned (missing value fill + IQR outlier report), persistence-forecasted (shift-24h), with a cumulative P&L chart rendered by plotly — proving the full data→forecast→trade pipeline connects before any sophisticated modeling begins.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.11 | OpenSTEF floor (Phase 2); NumPy 2.x + pandas 3.0.x Arrow backend compatibility |
| Development environment | Jupyter Notebook + modular .py pipeline modules | Notebooks for learning/exploration; .py modules for reusable production logic (per D-10). Thin notebook wrappers, thick pipeline modules. |
| Package management | pip + venv + requirements.txt (pinned versions) | One-command setup: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`. Target <30min on clean machine (per D-06). No Poetry/pipenv — overkill for learning platform. |
| Data layer | pandas/pyarrow with Parquet files (no database server) | Portable, columnar, pandas-native, fast read/write. Phase 1 has <100MB data — SQLite/Postgres is unnecessary overhead. TimescaleDB added in Phase 2 via Docker for ASSUME dashboards. |
| Data source strategy | OWID yearly data (auto-fetch) + Chinese open data platforms (manual download) | China-only per D-01. OWID provides proven, auto-fetchable yearly macro data. Chinese hourly/daily data requires manual browser download from 和鲸/天池/地方平台 (government portals have CAPTCHA/anti-bot barriers — RESEARCH.md §1). Unified DataLoader interface (per D-02/D-03). NO international data (no PUDL, no epftoolbox, no PJM). |
| Data format | Standardized column schema: `timestamp` (datetime64[ns, UTC]), `load_mw` (float64), plus metadata (region, data_source) | Per D-04/D-05. All timezone-aware. Parquet primary format. |
| Auth | None | Local Jupyter learning environment. No user accounts, no API keys. |
| Deployment target | Local Jupyter server (`setup.sh && jupyter notebook`) | No cloud deployment needed. Learner runs everything on their dev machine. |
| Visualization | plotly 6.7.0 (interactive, Jupyter-native) | Per D-15. Hover-to-see-values, zoom, pan — critical for learning data exploration. |
| Model evaluation | MAE only (Mean Absolute Error on temporal test split) | Per D-14. Keep it simple and interpretable. No RMSE, MAPE, sMAPE in Phase 1 — reduce cognitive load for learners. |
| Directory layout | `pipeline/` (modules), `notebooks/` (exploration), `data/` (raw data, gitignored) | Established pattern for all phases. pipeline/ modules are importable; notebooks/ are thin wrappers. |

## Stack Touched in Phase 1

- [x] Project scaffold — `setup.sh`, `requirements.txt`, directory structure, `pipeline/__init__.py`
- [x] Data loading — OWID China data via `urllib` auto-fetch, ChineseDataLoader for manual files
- [x] Data cleaning — missing value imputation, IQR outlier detection (report-only), UTC timezone normalization
- [x] Forecasting — persistence forecast (shift-24h baseline), minimal P&L calculation
- [x] Visualization — plotly line overlay (actual vs forecast) + cumulative P&L chart
- [ ] Feature engineering — deferred to Plan 01-02 (calendar features, lag features, rolling windows)
- [ ] XGBoost training — deferred to Plan 01-02 (TimeSeriesSplit, model persistence)
- [ ] Docker Compose — deferred to Plan 01-03 (skeleton YAML, uncommented in Phase 2)

## Out of Scope (Deferred to Later Slices)

- **XGBoost load forecasting** (PRED-01 full) — Plan 01-02 adds XGBoost with TimeSeriesSplit, progressive features, model persistence, and all visualizations
- **Docker Compose** (ENV-02) — Plan 01-03 creates commented skeleton YAML; actual services uncommented in Phase 2 for ASSUME+TimescaleDB+Grafana
- **OpenSTEF automated forecasting** (PRED-02) — Phase 2
- **epftoolbox price prediction** (PRED-03) — Phase 2
- **ASSUME market simulation** (SIM-01 through SIM-04) — Phase 2
- **RL trading agents** (AGENT-01 through AGENT-04) — Phase 3
- **SHAP explainability** (VIZ-02) — Phase 3
- **FastAPI + CLI + LangChain + Ollama** — Phase 4
- **Chinese electricity hourly/daily data** — manual download workflow documented (D-03); data files themselves are gitignored (user-provided, not committed)
- **Weather data integration** — Phase 2 (OpenSTEF provides weather feature engineering)
- **enda energy library** — Deferred per CONTEXT.md (H2O dependency conflicts with project constraints)
- **Grafana dashboards** — Phase 2 (via ASSUME+TimescaleDB Docker services)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- **Phase 2**: Deep prediction (OpenSTEF vs XGBoost comparison) + ASSUME market simulation with multiple generation mixes and Grafana dashboards
- **Phase 3**: RL trading agents (PPO/TD3/SAC) with custom reward functions, historical backtesting on stress periods, SHAP explainability
- **Phase 4**: FastAPI REST API, CLI toolchain, LangChain + Ollama natural language trading assistant
