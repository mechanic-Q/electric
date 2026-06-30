# Task Completion

- First read `.sillyspec/local.yaml`; currently no active test/lint command and `test_strategy: skip`.
- For 15min granularity changes, run: `rtk pytest tests/test_time_resolution_15min.py`.
- Run targeted `rg` checks for hardcoded point-count regressions, e.g. `gap: int = 24`, `gap=24`, `Box(0, 1, (24`, `start >= 24`, and docs residuals in touched modules.
- If code changed, run `graphify update .` from repo root to refresh knowledge graph.
- If SillySpec verify is required, run `sillyspec run verify --reopen --from-step 1 --change <change-name>` after fixes.
- Do not commit unless user explicitly asks.