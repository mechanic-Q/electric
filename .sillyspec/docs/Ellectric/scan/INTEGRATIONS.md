# Integrations — Ellectric

> **author**: lmr
> **created_at**: 2026-06-06T00:00:00+08:00
> **scan_type**: full
> **source**: requirements.txt, pipeline/*.py, docker-compose.yml, setup.sh

## Runtime Dependencies (requirements.txt)

### Data Processing
| Package | Version | Usage |
|---------|---------|-------|
| **pandas** | 3.0.3 | Core DataFrame operations: time-series indexing, resampling, I/O (`read_csv`, `read_excel`, `read_parquet`), timestamp parsing, timezone normalization. Used in all pipeline modules. |
| **numpy** | >=2.0.0 | Numerical array operations: sin/cos cyclic encoding (`features.py`), statistical computations (`forecaster.py`), IQR bounds (`cleaner.py`). |
| **pyarrow** | 22.0.0 | Parquet columnar storage backend for pandas. Enables high-speed read/write of `electricity_load_hourly.parquet` with Arrow-backed memory layout. |

### Machine Learning
| Package | Version | Usage |
|---------|---------|-------|
| **scikit-learn** | 1.8.0 | `TimeSeriesSplit` (temporal cross-validation with gap parameter in `forecaster.py:335`), `StandardScaler` (fit-on-train-only enforced per fold in `forecaster.py:353`), regression metrics (`mean_absolute_error`, `mean_squared_error`, `r2_score`). |
| **xgboost** | 3.2.0 | `XGBRegressor` — gradient-boosted tree model for load forecasting. Default 100 estimators with L1/L2 regularization. CPU-optimized, no GPU required. Used in `forecaster.py:363`. |

### Visualization
| Package | Version | Usage |
|---------|---------|-------|
| **plotly** | 6.7.0 | Interactive time-series charts: `graph_objects.Scatter` for actual-vs-forecast overlay, `make_subplots` for multi-panel P&L dashboard (`forecaster.py:48-49`). Supports hover tooltips, box zoom, and PNG export. |

### Development Environment
| Package | Version | Usage |
|---------|---------|-------|
| **jupyter** | 1.1.1 | Jupyter Notebook server — primary interactive learning interface. Launched via `jupyter notebook notebooks/`. |
| **nbformat** | >=5.0.0 | Notebook file format library — ensures compatibility of `.ipynb` files across Jupyter versions. |

## Python Standard Library (no install needed)

| Module | File | Usage |
|--------|------|-------|
| **urllib.request** | `data_loader.py:55,153-154` | HTTP GET to OWID GitHub raw CSV (`https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv`) with custom User-Agent and 30s timeout. Streams ~25MB CSV without full in-memory load. |
| **csv** / **io** | `data_loader.py:57,157` | `csv.DictReader` + `io.TextIOWrapper` for streaming line-by-line CSV parsing. Filters to China (`iso_code == 'CHN'`) rows only. |
| **abc** / **pathlib** | `data_loader.py:52,59` | `ABC`/`abstractmethod` for DataLoader interface contract. `Path` for cross-platform file resolution. |
| **logging** | all pipeline modules | Standard Python logging with `getLogger(__name__)` pattern. Informational for pipeline steps, warning for anomalies (missing data, outliers, missing holidays package). |

## Optional Dependencies

| Package | File | Usage | Status |
|---------|------|-------|--------|
| **holidays** | `features.py:121` | Chinese legal holiday detection for `is_holiday` feature in Tier 2. Wrapped in try/except — silently defaults to 0 if not installed. | **Optional** — not in requirements.txt; can be added for better feature quality |

## External Data Sources

| Source | URL | Protocol | Module |
|--------|-----|----------|--------|
| **OWID Energy Data** | `https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv` | HTTPS (urllib) | `data_loader.py:66-69` |
| **Local data files** | `ellectric/data/*.{csv,parquet,xlsx,xls}` | Filesystem | `data_loader.py:252-257` |

## Infrastructure (Planned / Phase 2+)

| Component | Image | Status | Purpose |
|-----------|-------|--------|---------|
| **TimescaleDB** | `timescale/timescaledb:latest-pg16` | Commented out in `docker-compose.yml` | ASSUME market simulation database — stores bid/offer curves, clearing prices, dispatch logs |
| **Grafana** | `grafana/grafana:latest` | Commented out in `docker-compose.yml` | ASSUME visualization dashboards — merit order curves, dispatch, profit per agent |
| **Docker** | (host daemon) | Planned for Phase 2 | Container runtime for ASSUME dependencies |

## Phase 2+ Scheduled Integrations (from ROADMAP.md)

| Phase | Package | Purpose |
|-------|---------|---------|
| Phase 2 | **OpenSTEF** 3.4.93 | Automated ML forecasting pipeline (vs manual XGBoost comparison) |
| Phase 2 | **epftoolbox** (git) | Day-ahead electricity price forecasting (LEAR + DNN models) |
| Phase 2 | **ASSUME** 0.6.0 | Agent-based electricity market simulation (RL agents, multiple market designs) |
| Phase 2 | **PyPSA** | Power system optimal power flow (required by ASSUME for network-based clearing) |
| Phase 3 | **stable-baselines3** 2.8.0 | RL algorithms (PPO, SAC, TD3) for trading agent training |
| Phase 3 | **optuna** 4.8.0 | Hyperparameter optimization for XGBoost and RL agents |
| Phase 3 | **SHAP** | Model explainability — feature importance waterfall plots |
| Phase 4 | **FastAPI** 0.136.1 | REST API for prediction queries, simulation triggers, backtest runs |
| Phase 4 | **LangChain** 1.3.1 | LLM agent orchestration with tool-calling chains |
| Phase 4 | **Ollama** 0.6.2 | Local LLM serving (Qwen2.5-7B) — no cloud API needed |
| Phase 4 | **chromadb** 1.5.9 | Vector database for RAG over trading documents |
| Phase 4 | **MLflow** 3.12.0 | Experiment tracking and model registry |
| Phase 4 | **end** 1.0.5 | Energy-specific timeseries manipulation (gap detection, resampling, contract-to-timeseries) |

## Cross-Module Dependency Graph (Phase 1)

```
[External] OWID GitHub raw CSV ──(HTTPS/urllib)──► data_loader.py
[External] Local CSV/Parquet/Excel ──(Filesystem)──► data_loader.py

data_loader.py ──(pd.DataFrame)──► cleaner.py
                                     │
                                     ▼(cleaned DataFrame)
                                  features.py
                                     │
                                     ▼(feature DataFrame)
                                  forecaster.py
                                     │
                                     ├── persistence_forecast() ──► plotly Figure
                                     ├── XGBoostForecaster ──► metrics dict + model
                                     └── calculate_pnl() ──► cumulative P&L Series

[External] scikit-learn ──► forecaster.py (TimeSeriesSplit, StandardScaler, metrics)
[External] xgboost ──► forecaster.py (XGBRegressor)
[External] plotly ──► forecaster.py (graph_objects, make_subplots)
[External] holidays (optional) ──► features.py (is_holiday via try/except)
```

## Notes

- **No async/WebSocket/websocket**: Phase 1 is synchronous pipeline processing only. All HTTP is blocking `urllib.request`.
- **No database**: All data is in-memory pandas DataFrames or local Parquet files. TimescaleDB is Phase 2.
- **No API server**: FastAPI is scheduled for Phase 4.
- **No LLM**: LangChain/Ollama are Phase 4.
- **Security**: OWID data is public GitHub-hosted CSV. No API keys, no authentication, no secrets.
- **Mirror**: `setup.sh` auto-detects PyPI reachability and falls back to `https://pypi.tuna.tsinghua.edu.cn/simple` for users behind the GFW.
