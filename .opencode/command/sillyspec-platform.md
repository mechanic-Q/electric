---
description: SillyHub platform sync — connect, sync, approve, reject
argument-hint: "[connect <url> [--token <t>] | disconnect | sync [--change <name>] | sync-docs [--change <name>] | status | approve <change-name> | reject <change-name> --reason ...]"
tools:
  read: true
  write: true
  bash: true
  question: true
---
Run `sillyspec platform $ARGUMENTS` for SillyHub platform operations.

Subcommands: connect, disconnect, sync, sync-docs, status, approve, reject.
