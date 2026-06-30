# Core

- Project: Ellectric / AI + 电力交易技术学习平台. Learning prototype, not production trading.
- Main source: `ellectric/` Python package. Tests: `tests/`. Docs/module cards: `docs/Ellectric/`. Planning/change artifacts: `.sillyspec/changes/`.
- Current canonical high-frequency data: Shandong 15min CSV via `ellectric/pipeline/shandong_loader.py`; time resolution SSOT: `ellectric/config.py::TimeConfig`.
- Pipeline layers: data loaders -> cleaner -> features/price_forecaster/forecaster -> trading_env/backtester/rl_trainer -> service handlers -> FastAPI/CLI/LLM tools.
- Project uses SillySpec workflow; `.sillyspec/local.yaml` may define commands but currently has test/lint commented and `test_strategy: skip`.
- Read `mem:tech_stack` for dependencies/runtime, `mem:conventions` for code style, `mem:suggested_commands` for commands, `mem:task_completion` before finishing code changes.