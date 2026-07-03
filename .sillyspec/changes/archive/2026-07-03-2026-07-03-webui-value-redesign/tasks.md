---
author: lmr
created_at: 2026-07-03 17:01:37
---

# Tasks

- [ ] task-01: 新增 Vite + React + TypeScript 前端工程骨架
  - 文件路径：`ellectric/web/package.json`, `ellectric/web/vite.config.ts`, `ellectric/web/tsconfig.json`, `ellectric/web/index.html`, `ellectric/web/src/main.tsx`
  - 覆盖：FR-007, FR-008, D-002@v2, D-005@v1

- [ ] task-02: 实现前端 API/SSE 类型与 fetch client
  - 文件路径：`ellectric/web/src/types.ts`, `ellectric/web/src/api.ts`
  - 覆盖：FR-002, FR-004, FR-006, FR-009, FR-010, FR-013, D-004@v1, D-005@v1

- [ ] task-03: 实现 Dashboard-first 页面结构
  - 文件路径：`ellectric/web/src/App.tsx`, `ellectric/web/src/styles.css`
  - 覆盖：FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, D-001@v1

- [ ] task-04: 迁移 Chat-first SSE UI 为右侧 Copilot
  - 文件路径：`ellectric/web/src/App.tsx`, `ellectric/web/src/api.ts`, `ellectric/web/src/types.ts`, `ellectric/web/src/styles.css`
  - 覆盖：FR-010, FR-013, D-001@v1, D-002@v2, D-004@v1, D-005@v1

- [ ] task-05: 落实非交易边界和风险文案
  - 文件路径：`ellectric/web/src/App.tsx`, `ellectric/web/src/styles.css`
  - 覆盖：FR-011, FR-012, D-003@v1

- [ ] task-06: 接入构建产物与 FastAPI 静态服务兼容验证
  - 文件路径：`ellectric/api/static/index.html`, `ellectric/api/server.py`, `tests/test_api_catalog.py`, `tests/test_web_static.py`
  - 覆盖：FR-008, FR-009, D-002@v2, D-005@v1

- [ ] task-07: 更新 WebUI 使用文档
  - 文件路径：`README.md`
  - 覆盖：FR-014, D-002@v2, D-005@v1

- [ ] task-08: 执行验证并记录结果
  - 文件路径：`ellectric/web/package.json`, `tests/test_api_catalog.py`, `tests/test_chat_streaming_events.py`, `tests/test_web_static.py`
  - 覆盖：FR-007, FR-008, FR-009, FR-010, FR-011, FR-013, D-002@v2, D-003@v1, D-004@v1, D-005@v1
