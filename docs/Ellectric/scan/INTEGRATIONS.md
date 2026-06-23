# Integrations — Ellectric

> **author**: lmr
> **created_at**: 2026-06-06T00:00:00+08:00
> **updated_at**: 2026-06-10T00:00:00+08:00
> **scan_type**: full
> **source**: requirements.txt, pipeline/*.py, api/*.py, service/*.py, cli/*.py, llm/*.py, assume/*.py, docker-compose.yml, setup.sh

## Runtime Dependencies (requirements.txt + Phase 2-4 additions)

### Data Processing
| Package | Version | Usage |
|---------|---------|-------|
| **pandas** | 3.0.3 | Core DataFrame operations: time-series indexing, resampling, I/O (`read_csv`, `read_excel`, `read_parquet`), timestamp parsing, timezone normalization. Used in all pipeline modules. |
| **numpy** | >=2.0.0 | Numerical array operations: sin/cos cyclic encoding (`features.py`), statistical computations (`forecaster.py`), IQR bounds (`cleaner.py`), RL environment state arrays (`trading_env.py`). |
| **pyarrow** | 22.0.0 | Parquet columnar storage backend for pandas. Enables high-speed read/write of parquet files. |

### Machine Learning & Forecasting
| Package | Version | Usage |
|---------|---------|-------|
| **scikit-learn** | 1.8.0 | `TimeSeriesSplit` (temporal cross-validation with gap parameter in `forecaster.py:335`), `StandardScaler` (fit-on-train-only enforced per fold in `forecaster.py:353`), regression metrics (`mean_absolute_error`, `mean_squared_error`, `r2_score`). **Lasso** — core LEAR price forecasting regressor in `price_forecaster.py`. |
| **xgboost** | 3.2.0 | `XGBRegressor` — gradient-boosted tree model for load forecasting. Default 100 estimators with L1/L2 regularization. CPU-optimized, no GPU required. Used in `forecaster.py:363`. |

### Reinforcement Learning (Phase 3)
| Package | Version | Usage |
|---------|---------|-------|
| **stable-baselines3** | >=2.8.0 | RL algorithm implementations: PPO (on-policy), SAC (off-policy max-entropy), TD3 (off-policy double-Q). Used via adapters in `rl_trainer.py`. |
| **gymnasium** | >=1.2.3 | RL environment framework. `ElectricityMarketEnv` in `trading_env.py` uses `gym.Env`, `Box`, `Dict` spaces. Replaces deprecated `gym` library. |

### Market Simulation (Phase 2-3)
| Package | Version | Usage |
|---------|---------|-------|
| **assume-framework[learning]** | 0.6.0 | Agent-based electricity market simulation. Called via subprocess from `handlers.py:run_simulate()`. PyTorch + sb3 backends for RL agents within simulation. |
| **PyTorch** | (ASSUME transitive) | Neural network backend for ASSUME's RL agents within market simulation. |

### Explainability (Phase 3)
| Package | Version | Usage |
|---------|---------|-------|
| **shap** | >=0.46 | SHAP model explainability: `TreeExplainer` for XGBoost, `LinearExplainer` for Lasso/LEAR. Lazy-imported via `_get_shap()` in `shap_explainer.py`. |

### API & Schema (Phase 4)
| Package | Version | Usage |
|---------|---------|-------|
| **fastapi** | >=0.136.1 | REST API framework in `api/server.py`. 5 routes with auto-generated OpenAPI docs. |
| **uvicorn** | — | ASGI server for FastAPI. Launched via `uvicorn ellectric.api.server:app`. |
| **pydantic** | >=2.13.4 | Data validation with Rust-backed pydantic-core. `model_validator(mode="after")`, `field_validator`, `Literal` types in `service/schemas.py`. No v1 compatibility API used. |

### CLI (Phase 4)
| Package | Version | Usage |
|---------|---------|-------|
| **typer** | — | CLI framework in `cli/main.py`. 5 subcommands with automatic help text and argument parsing. |
| **rich** (optional) | — | Pretty table output in CLI. Falls back to plain-text `_format_table()` when unavailable. |

### LLM Agent (Phase 4)
| Package | Version | Usage |
|---------|---------|-------|
| **langchain** | >=1.3.1 | Agent framework in `llm/agent.py`. `create_agent()` builds tool-calling agent. |
| **langchain-openai** | — | OpenAI SDK adapter for LangChain. Connects to DeepSeek API (`https://api.deepseek.com/v1`) via `ChatOpenAI` class. |
| **httpx** | — | HTTP client for LLM tools in `llm/tools.py`. Module-level shared `httpx.Client(timeout=30.0)` calls local FastAPI endpoints. |

### Visualization
| Package | Version | Usage |
|---------|---------|-------|
| **plotly** | 6.7.0 | Interactive charts across all phases: load forecast overlay, P&L dashboard (`forecaster.py`), price forecast (`price_forecaster.py`), SHAP waterfall (`shap_explainer.py`), backtest comparison (`backtester.py`). |

### Development Environment
| Package | Version | Usage |
|---------|---------|-------|
| **jupyter** | 1.1.1 | Jupyter Notebook server — primary interactive learning interface. |
| **nbformat** | >=5.0.0 | Notebook file format compatibility. |

### Statistical Tests (Phase 2, optional)
| Package | Version | Usage |
|---------|---------|-------|
| **epftoolbox** (git) | — | Diebold-Mariano and Giacomini-White forecast comparison tests. Lazy-imported in `statistical_tests.py`. Falls back to mock data when unavailable. Install: `pip install git+https://github.com/jeslago/epftoolbox.git` |

## Python Standard Library (no install needed)

| Module | File | Usage |
|--------|------|-------|
| **urllib.request** | `data_loader.py:55,153-154` | HTTP GET to OWID GitHub raw CSV with custom User-Agent and 30s timeout. |
| **csv** / **io** | `data_loader.py:57,157` | `csv.DictReader` + `io.TextIOWrapper` for streaming line-by-line CSV parsing. Also used in `handlers.py:run_simulate()` for reading clearing_prices.csv. |
| **abc** / **pathlib** | `data_loader.py:52,59`; `rl_trainer.py:33` | `ABC`/`abstractmethod` for DataLoader and BaseRLAgent contracts. `Path` for cross-platform file resolution. |
| **logging** | all modules | `logging.getLogger(__name__)` pattern throughout. |
| **subprocess** | `handlers.py:143` | `subprocess.run()` to launch ASSUME simulation as child process. 600s timeout. |
| **os** | `handlers.py:46-51` | Environment variable lookup: `ELLECTRIC_MODEL_DIR`, `ELLECTRIC_DATA_DIR`, `DEEPSEEK_API_KEY`, `ELLECTRIC_API_URL`. |
| **argparse** | `assume/run_simulation.py:52` | CLI argument parsing for simulation runner. |
| **yaml** | `assume/run_simulation.py:30` | YAML config loading for ASSUME simulation scenarios. |

## Optional Dependencies (try/except guarded)

| Package | File | Usage | Fallback |
|---------|------|-------|----------|
| **holidays** | `features.py:121` | Chinese legal holiday detection for `is_holiday` feature in Tier 2 | Defaults `is_holiday` to 0 |
| **shap** | `shap_explainer.py:36-44` | TreeExplainer + LinearExplainer SHAP waterfall plots. Lazy-loaded via `_get_shap()`. | Throws `RuntimeError` with install instructions |
| **epftoolbox** (git) | `statistical_tests.py:40-48` | DM/GW forecast comparison tests | Uses mock result tables (`_MOCK_DM`, `_MOCK_GW`) |
| **rich** | `cli/main.py:47-53` | Pretty table formatting in CLI output | Falls back to `_format_table()` plain-text |

## External Data Sources

| Source | URL | Protocol | Module |
|--------|-----|----------|--------|
| **OWID Energy Data** | `https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv` | HTTPS (urllib) | `data_loader.py:66-69` |
| **ZionLuo Price Data** | `data/price_data.xlsx` (local copy of ZionLuo/Electricity-Price-Forecasting) | Filesystem | `price_loader.py` |
| **DeepSeek API** | `https://api.deepseek.com/v1` | HTTPS (httpx via LangChain ChatOpenAI) | `llm/agent.py` |
| **Local data files** | `ellectric/data/*.{csv,parquet,xlsx,xls,joblib,zip}` | Filesystem | All modules |

## Infrastructure

| Component | Image | Status | Purpose |
|-----------|-------|--------|---------|
| **Grafana** | `grafana/grafana:latest` | Operational in `docker-compose.yml` | ASSUME visualization dashboards — merit order curves, dispatch, profit per agent |
| **Docker** | (host daemon) | Required for Grafana | Container runtime for ASSUME visualization |

## Other Integrations (from ROADMAP.md — not yet implemented)

| Phase | Package | Purpose | Status |
|-------|---------|---------|--------|
| Phase 2 | **OpenSTEF** 3.4.93 | Automated ML forecasting pipeline | Not integrated |
| Phase 2 | **PyPSA** | Power system optimal power flow | Not integrated |
| Phase 3 | **optuna** 4.8.0 | Hyperparameter optimization | Not integrated |
| Phase 4 | **Ollama** 0.6.2 | Local LLM serving (planned alternative to DeepSeek API) | Not integrated |
| Phase 4 | **chromadb** 1.5.9 | Vector database for RAG over trading documents | Not integrated |
| Phase 4 | **MLflow** 3.12.0 | Experiment tracking and model registry | Not integrated |

## Cross-Module Dependency Graph (All Phases)

```
[External] OWID GitHub raw CSV ──(HTTPS/urllib)──► data_loader.py
[External] ZionLuo xlsx ──(Filesystem)──► price_loader.py
[External] Local files ──(Filesystem)──► data_loader.py / price_loader.py

                    ┌────────────────── Phase 1 ──────────────────────┐
                    data_loader.py ──► cleaner.py ──► features.py
                                                          │
                                                          ▼
                                                    forecaster.py
                                                    │
                                                    ├── XGBoostForecaster
                                                    ├── persistence_forecast()
                                                    └── calculate_pnl()/plot_pnl()

                    ┌────────────────── Phase 2 ──────────────────────┐
                    price_loader.py ──► price_forecaster.py (LEAR)
                                              │
                                              ├── LEARForecaster (Lasso)
                                              └── plot_price_forecast()

                    statistical_tests.py (DM/GW, optional epftoolbox)

                    ┌────────────────── Phase 3 ──────────────────────┐
                    trading_env.py (ElectricityMarketEnv)
                         │
                         ▼
                    rl_trainer.py (PPO/SAC/TD3 via BaseRLAgent)
                         │
                         ▼
                    backtester.py (BacktestRunner + 3 baselines)
                         │
                         ▼
                    shap_explainer.py (TreeExplainer + LinearExplainer)

                    ┌────────────────── Phase 4 ──────────────────────┐
                    service/schemas.py ──── Pydantic v2 models
                         │
                    service/handlers.py ──── Lazy-import bridge
                         │
                    ┌────┼────────────────┐
                    │    │                │
                    ▼    ▼                ▼
              api/     cli/              llm/
            server.py main.py          agent.py
            (FastAPI) (Typer)       (LangChain)
                                         │
                                    llm/tools.py
                                    (httpx ──► local API)

[External] scikit-learn ──► forecaster.py (TimeSeriesSplit, StandardScaler, metrics)
[External] scikit-learn ──► price_forecaster.py (Lasso)
[External] xgboost ──► forecaster.py (XGBRegressor)
[External] stable-baselines3 ──► rl_trainer.py (PPO, SAC, TD3)
[External] gymnasium ──► trading_env.py (Env, Box, Dict)
[External] shap (optional) ──► shap_explainer.py (TreeExplainer, LinearExplainer)
[External] assume-framework ──► assume/run_simulation.py (World)
[External] epftoolbox (optional) ──► statistical_tests.py (dm_test, gw_test)
[External] plotly ──► forecaster.py, price_forecaster.py, backtester.py, shap_explainer.py
[External] fastapi/uvicorn ──► api/server.py
[External] typer ──► cli/main.py
[External] langchain + langchain-openai ──► llm/agent.py
[External] httpx ──► llm/tools.py
[External] pydantic v2 ──► service/schemas.py
[External] holidays (optional) ──► features.py (is_holiday via try/except)
```

## Notes

- **Synchronous only**: All pipeline operations are synchronous. FastAPI endpoints use synchronous handlers (no async/await). LLM agent calls `httpx.Client` (not AsyncClient).
- **No database**: All data is in-memory pandas DataFrames or local files (Parquet, CSV, xlsx, joblib).
- **API + CLI + LLM**: Three parallel interface layers sharing the same Service layer. No duplicate business logic.
- **DeepSeek API dependency**: LLM agent requires `DEEPSEEK_API_KEY` environment variable and internet access to `api.deepseek.com`. No offline fallback currently implemented.
- **Security considerations**:
  - OWID data is public GitHub-hosted CSV. No API keys needed.
  - DeepSeek API key required for LLM features (Phase 4). Not required for pipeline/API/CLI.
  - No authentication on FastAPI endpoints (local/educational use only).
- **Optional dependency degradation**: shap, epftoolbox, holidays, rich gracefully degrade when not installed.
- **Grafana operational**: Unlike Phase 1 (commented-out), Phase 3 provides operational `docker-compose.yml` for Grafana connected to ASSUME output data.
- **Mirror**: `setup.sh` auto-detects PyPI reachability and falls back to `https://pypi.tuna.tsinghua.edu.cn/simple` for users behind the GFW.
