---
description: Progress tracking — init, show, check, repair, validate, reset
argument-hint: "[init | show | check | repair [--apply] | validate | reset [--stage X] | set-stage <stage> | add-step <stage> <name> | update-step <s> <n> --status <st> | complete-stage <stage>]"
tools:
  read: true
  write: true
  bash: true
---
Run `sillyspec progress $ARGUMENTS` for lightweight progress tracking.
- `show` — view current progress
- `check` — state consistency check (read-only)
- `repair --apply` — fix inconsistent metadata
- `validate` — validate and repair
- `init` — initialize project database
- `set-stage <stage>` — set current stage
- `complete-stage <stage>` — mark stage complete
