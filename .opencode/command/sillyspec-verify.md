---
description: Verify implementation against design docs and module specs
argument-hint: "[--change <name>]"
tools:
  read: true
  bash: true
  glob: true
  grep: true
  question: true
---
Run `sillyspec run verify` to check implementation completeness and design consistency.

1. `sillyspec run verify $ARGUMENTS` — outputs step prompt
2. Verify against design.md + module docs
3. On completion: `sillyspec run verify --done --output "摘要"`
