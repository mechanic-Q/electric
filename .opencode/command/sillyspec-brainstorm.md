---
description: Requirement clarification and technical design before coding
argument-hint: "[需求描述] [--change <name>]"
tools:
  read: true
  write: true
  edit: true
  bash: true
  glob: true
  grep: true
  question: true
---
Run `sillyspec run brainstorm` for structured requirement analysis and technical design.

1. `sillyspec run brainstorm $ARGUMENTS` — outputs step prompt
2. Follow the prompt strictly, don't write code
3. On completion: `sillyspec run brainstorm --done --output "摘要"`
4. Repeat 2-3 until done
