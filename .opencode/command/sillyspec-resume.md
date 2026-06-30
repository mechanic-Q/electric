---
description: Resume work from interruption point
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
Run `sillyspec run resume $ARGUMENTS` to continue interrupted work.

Reads progress.json, restores context from last completed step.
