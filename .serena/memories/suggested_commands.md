# Suggested Commands

- Show SillySpec progress: `sillyspec progress show`.
- Run verify for active change: `sillyspec run verify --change <change-name>`.
- Reopen verify from start after execute revision: `sillyspec run verify --reopen --from-step 1 --change <change-name>`.
- Focused 15min tests: `rtk pytest tests/test_time_resolution_15min.py`.
- Search code fast: `/usr/bin/rg -n '<pattern>' <paths>` (project AGENTS prefers Bash + rg over built-in grep).
- Local config: read `.sillyspec/local.yaml` before build/test/lint; currently test/lint entries are commented.
- Avoid `sillyspec worktree apply` when worktree has unrelated files not in design manifest; it may fail manifest validation.