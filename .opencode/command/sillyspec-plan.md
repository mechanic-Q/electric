---
description: Break design into executable implementation plan (Wave groups + Tasks)
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
Run `sillyspec run plan` to decompose design into actionable tasks.

1. `sillyspec run plan $ARGUMENTS` — outputs step prompt
2. Follow the prompt strictly
3. On completion: `sillyspec run plan --done --output "摘要"`
4. Repeat 2-3 until done
