---
description: Scan project codebase — generate architecture docs, code conventions, directory structure
argument-hint: "[--change <name>]"
tools:
  read: true
  write: true
  bash: true
  glob: true
  grep: true
  question: true
---
Run `sillyspec scan` via the CLI.

1. `sillyspec run scan $ARGUMENTS` — outputs step prompt
2. Follow the prompt strictly
3. On completion: `sillyspec run scan --done --output "摘要"`
4. Repeat 2-3 until done
