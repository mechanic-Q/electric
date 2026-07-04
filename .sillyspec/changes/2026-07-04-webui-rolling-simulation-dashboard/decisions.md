---
author: lmr
created_at: 2026-07-04 08:27:15
---

# Decisions — WebUI Rolling Simulation Dashboard

## D-001@v1: VVB Canonical Term Is WebUI/Dashboard

- type: term
- status: accepted
- source: user
- question: User mentioned "VVB"; should implementation introduce a new VVB concept?
- answer: No. User corrected that VVB means WebUI.
- normalized_requirement: Code and docs use WebUI/Dashboard naming; do not introduce a VVB module or route.
- impacts: [FR-001, design-naming, task-frontend]
- evidence: user answer in brainstorm before change start: "VVB就是webui，刚才我写错了"
- priority: P1

## D-002@v1: First Screen Is Data Theater

- type: boundary
- status: accepted
- source: user
- question: Should the first screen prioritize a theater-style showcase, an analysis workbench, or a teaching path?
- answer: Data theater showcase.
- normalized_requirement: WebUI first screen defaults to automatic rolling playback of the Shandong 15min window with modular panels and visual emphasis; controls stay lightweight.
- impacts: [FR-002, FR-003, task-frontend]
- evidence: user answer in Step 6: "数据剧场展示"
- priority: P1

## D-003@v1: Homepage Simulation Means Historical Replay

- type: boundary
- status: accepted
- source: user + code
- question: Should the dashboard run live training or heavy ASSUME simulation on page load?
- answer: No. Simulation display means historical rolling replay / strategy backtest evidence over the richest Shandong data window.
- normalized_requirement: The dashboard must use a read-only display endpoint and must not trigger model training, real-time trading, or heavy ASSUME simulation from the homepage.
- impacts: [FR-004, FR-005, task-backend, task-frontend, verify-api]
- evidence: user requirement: finite data, use richest Shandong window; confirmed non-goals in Step 9; existing API has `/simulate` and `/backtest`, but selected design avoids calling heavy endpoints for first-screen animation.
- priority: P1

## D-004@v1: Selected Implementation Is Read-Only Endpoint + Native SVG/CSS

- type: architecture
- status: accepted
- source: user
- question: Which implementation option should be used?
- answer: Option A.
- normalized_requirement: Add a read-only rolling demo endpoint backed by real Shandong data and implement the data theater with existing React/Vite plus native SVG/CSS charts, without adding a chart dependency.
- impacts: [FR-001, FR-002, FR-003, FR-004, task-backend, task-frontend, verify-build]
- evidence: user answer in Step 8: "方案a"
- priority: P1
