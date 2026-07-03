---
id: task-07
title: 更新 WebUI 使用文档
author: lmr
created_at: 2026-07-03 17:06:03
priority: P1
depends_on: [task-06]
blocks: []
requirement_ids: [FR-014]
decision_ids: [D-002@v2, D-005@v1]
allowed_paths:
  - README.md
---
## goal
- Update README.md: Dashboard-first WebUI, new dev/build/start workflow
## implementation
- Rename "Web Chat UI" row to Dashboard-first Vite+React in "做了什么" table
- Add `web/` to project tree; add `npm install && npm run dev`, `npm run build` before `uvicorn` in quick start
- Document `GET /` returns Dashboard page; keep all existing API/CLI docs intact (D-005@v1)
## acceptance
- `npm run dev`, `npm run build`, `uvicorn` commands present; frontend described as Vite+React+TS under `ellectric/web/`
- Build output to `ellectric/api/static/` documented
- No production/real-trading claims outside existing "learning prototype" disclaimer
## verify
- `/usr/bin/rg -n "ellectric/web|npm run build|uvicorn ellectric.api.server:app" README.md` — each pattern ≥1 match
- README uses "learning prototype" framing, avoids "production"/"live trading" outside disclaimer
## constraints
- Only README.md; no app code changes. Document build/dev/start commands + API compatibility
- Do not overstate production readiness
