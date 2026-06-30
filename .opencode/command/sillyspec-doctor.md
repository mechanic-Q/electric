---
description: Self-check and repair — fix progress.json inconsistencies
argument-hint: "[--apply]"
tools:
  read: true
  bash: true
  glob: true
  question: true
---
Run `sillyspec run doctor $ARGUMENTS` to check and fix SillySpec state.

- Default: dry-run, report inconsistencies only
- `--apply`: actually repair mismatches
- `--json`: structured output for programmatic use
