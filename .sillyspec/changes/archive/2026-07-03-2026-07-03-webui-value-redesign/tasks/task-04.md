---
id: task-04
title: 迁移 Chat-first SSE UI 为右侧 Copilot
author: lmr
created_at: 2026-07-03 17:06:03
priority: P0
depends_on: [task-02]
blocks: [task-05]
requirement_ids: [FR-010, FR-013]
decision_ids: [D-001@v1, D-002@v2, D-004@v1, D-005@v1]
allowed_paths: [ellectric/web/src/App.tsx, ellectric/web/src/api.ts, ellectric/web/src/types.ts, ellectric/web/src/styles.css]
---
goal: >
  Move chat from primary page UI into a secondary Copilot panel while preserving the existing SSE protocol.
implementation:
  - Add Copilot state for prompt, streaming text, tool calls, tool results, errors, and done state.
  - Render token streams, tool_call status, and tool_result cards from task-02 `streamChat`.
  - Style Copilot as a side panel on desktop and a lower section on mobile.
acceptance:
  - Copilot sends a query and renders token/tool_call/tool_result/error/done events.
  - JSON payload and plain text tool results both display safely.
  - Copilot remains secondary to the Dashboard-first content.
verify:
  - cd ellectric/web && npm run build
  - python -m pytest tests/test_chat_streaming_events.py -q
constraints:
  - Do not introduce new SSE event types.
  - Do not add chat persistence, auth, or multi-user features.
  - Missing LLM config must show a local error, not crash the page.
