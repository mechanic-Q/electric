---
author: lmr
created_at: 2026-07-04 08:27:15
---

# Tasks

## Task List

| ID | 任务 | 文件路径 | 覆盖 |
|---|---|---|---|
| T-01 | 新增 rolling dashboard schema | `ellectric/service/schemas.py` | FR-04, FR-06, D-003@v1, D-004@v1 |
| T-02 | 新增只读 rolling demo service | `ellectric/service/dashboard.py` | FR-04, FR-05, FR-06, D-003@v1, D-004@v1 |
| T-03 | 注册 dashboard API route | `ellectric/api/server.py` | FR-04, FR-05, FR-08, D-003@v1 |
| T-04 | 添加后端 rolling demo 测试 | `tests/test_dashboard_rolling_demo.py` | FR-04, FR-05, FR-06 |
| T-05 | 新增前端 rolling dashboard 类型 | `ellectric/web/src/types.ts` | FR-01, FR-04, FR-06, D-001@v1, D-004@v1 |
| T-06 | 新增前端 rolling demo fetch 方法 | `ellectric/web/src/api.ts` | FR-04, FR-05, FR-08, D-003@v1 |
| T-07 | 重构 WebUI 为数据剧场首屏 | `ellectric/web/src/App.tsx` | FR-02, FR-03, FR-05, FR-08, D-002@v1, D-003@v1 |
| T-08 | 实现原生 SVG/CSS 图表与响应式样式 | `ellectric/web/src/App.tsx`, `ellectric/web/src/styles.css` | FR-02, FR-03, FR-07, D-002@v1, D-004@v1 |
| T-09 | 保留 Copilot sidebar 和现有能力入口兼容 | `ellectric/web/src/App.tsx`, `ellectric/api/server.py` | FR-08, D-001@v1, D-003@v1 |
| T-10 | 执行验证 | `tests/test_dashboard_rolling_demo.py`, `ellectric/web/package.json` | 全部 FR |

## Plan 阶段说明

本文件只列任务名、路径和覆盖关系。具体 Wave 分组、每个任务的验收命令、依赖顺序和实现步骤在 `sillyspec run plan` 阶段展开。
