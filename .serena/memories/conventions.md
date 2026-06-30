# Conventions

- Python modules start with Chinese/English module docstring explaining purpose and design tradeoffs.
- Use module-level `logger = logging.getLogger(__name__)`; progress via `logger.info`, degradations via `logger.warning`.
- Type annotate function signatures; use forward string annotations where needed.
- Pipeline uses simple classes/functions, no speculative abstraction.
- Data contract style: standard columns like `timestamp`, `load_mw`; Shandong loader adds `rt_price`, `da_price`, `province`, `source`, `granularity`.
- Time resolution invariant: use `TimeConfig.points_per_day`, `TimeConfig.points_per_week`, `TimeConfig.freq`; do not hardcode 24/168 as point counts. Field names like `lag_24h` mean time span, not array length.
- Pydantic v2 schemas use `BaseModel`, `Field`, `model_validator`; no v1 validators/class Config.
- Service handlers use function-local imports to avoid cycles.
- Do not add comments unless explicitly requested; follow existing dense docstring style when updating docs.