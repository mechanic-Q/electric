---
description: Archive verified changes — module impact analysis, sync docs, update ROADMAP
argument-hint: "[--change <name>]"
tools:
  read: true
  write: true
  edit: true
  bash: true
  glob: true
  grep: true
  question: true
---
Run `sillyspec run archive` to archive completed changes.

1. `sillyspec run archive $ARGUMENTS` — outputs step prompt
2. Follow the prompt strictly
3. On completion: `sillyspec run archive --done --output "摘要"`
