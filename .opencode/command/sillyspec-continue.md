---
description: Auto-detect and execute next step in current workflow
argument-hint: ""
tools:
  read: true
  write: true
  edit: true
  bash: true
  glob: true
  grep: true
  question: true
---
Run `sillyspec run continue $ARGUMENTS` to automatically determine next stage/step.

Reads current progress and advances to the next logical action.
