# Tech Stack

- Runtime: Python 3.11+.
- Data: pandas, numpy; CSV/Excel/Parquet data flow.
- ML: scikit-learn, xgboost; LEAR uses sklearn Lasso; TimeSeriesSplit for temporal CV.
- RL/env: gymnasium, stable-baselines3 in later phases; custom `ElectricityMarketEnv` in `ellectric/pipeline/trading_env.py`.
- API/CLI: FastAPI + Pydantic v2 schemas in `ellectric/service/schemas.py`; service handlers in `ellectric/service/handlers.py`; Typer CLI in `ellectric/cli/main.py`; LangChain tools in `ellectric/llm/tools.py`.
- Viz/notebooks: plotly, Jupyter notebooks under `ellectric/notebooks/`.
- No unified lock/build tool in active config; `.sillyspec/local.yaml` has build/test/lint commands commented out.