---
description: Execute code implementation per plan — Wave by Wave, Task by Task
argument-hint: "[--change <name>] [--done --output ...]"
tools:
  read: true
  write: true
  edit: true
  bash: true
  glob: true
  grep: true
  agent: true
  question: true
---
Run `sillyspec run execute` to implement code per plan.

1. `sillyspec run execute $ARGUMENTS` — outputs step prompt
2. Execute strictly — no skipping, no extra steps
3. On completion: `sillyspec run execute --done --output "摘要"`
4. Repeat 2-3 until stage complete
