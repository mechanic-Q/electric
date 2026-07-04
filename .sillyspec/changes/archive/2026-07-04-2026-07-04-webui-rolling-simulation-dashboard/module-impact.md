---
author: lmr
created_at: 2026-07-04 20:40:59
---

# 模块影响分析

## 三重交叉验证

### 声明范围（design.md 文件变更清单）

| 类型 | 文件 | 操作 |
|---|---|---|
| schema | `ellectric/service/schemas.py` | 修改：追加 RollingDemo* DTO |
| service | `ellectric/service/dashboard.py` | 新增：只读滚动展示服务 |
| route | `ellectric/api/server.py` | 修改：注册 GET /dashboard/rolling-demo |
| 测试 | `tests/test_dashboard_rolling_demo.py` | 新增：28 个测试 |
| 前端类型 | `ellectric/web/src/types.ts` | 修改：追加 RollingDemo* TS 类型 |
| 前端 fetch | `ellectric/web/src/api.ts` | 修改：追加 fetchRollingDemo |
| 前端首屏 | `ellectric/web/src/App.tsx` | 修改：替换为数据剧场 |
| 前端样式 | `ellectric/web/src/styles.css` | 修改：追加 dashboard + SVG 样式 |

### 任务范围（tasks.md）

与声明范围完全一致，新增文件为 task-02 （dashboard.py）和 task-04 （test_dashboard_rolling_demo.py）。

### 真实变更（git diff HEAD~1）

| 观察 | 说明 |
|---|---|
| 8 个核心变更文件 | 与声明范围一致（schemas.py， dashboard.py， server.py， test_dashboard_rolling_demo.py， types.ts， api.ts， App.tsx， styles.css） |
| 构建产物 | `ellectric/api/static/index.html` — npm run build 输出，非手写源码 |
| 非本变更 dirty 文件 | `ellectric/chat/streaming.py`， `ellectric/llm/tools.py`， `ellectric/service/handlers.py`， `tests/test_chat_streaming_events.py`, `tests/test_recommend_handler.py`， `ellectric/reports/weather_tier4/*` 等 — 工作区已有脏状态，不属于本变更影响范围 |

**结论：以 git diff 中可归属于本变更的 8 个文件为真实变更清单，与声明范围一致。**

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|---|---|---|---|---|
| service-api | 数据结构变更 | `ellectric/service/schemas.py`, `ellectric/service/dashboard.py` (新增) | 新增 7 个 RollingDemo Pydantic DTO，新增只读 build_rolling_demo 服务方法，接口签名不向后兼容风险 | false |
| service-api | 接口变更 | `ellectric/api/server.py` | 注册 GET /dashboard/rolling-demo 路由，位于 static mount 前，按 design.md 非目标不替换现有 /predict/simulate/backtest | false |
| service-api | 新增 | `tests/test_dashboard_rolling_demo.py` (新增) | 28 个后端测试覆盖 schema/service/endpoint | false |
| (unmatched) | 新增 | `ellectric/web/src/types.ts` | 追加 RollingDemoResponse/Meta/Series/Panel/Strategy/ReportEvidence 接口 | false |
| (unmatched) | 新增 | `ellectric/web/src/api.ts` | 追加 fetchRollingDemo() | false |
| (unmatched) | 逻辑变更 | `ellectric/web/src/App.tsx` | 首屏替换为数据剧场，保留 CopilotPanel，追加 play/pause/speed/tick 播放状态 | false |
| (unmatched) | 新增 | `ellectric/web/src/styles.css` | 追加 .dashboard-main， .chart-svg， .bars-list， .evidence-card， 响应式布局样式 | false |

## 影响类型统计

| 类型 | 计数 | 说明 |
|---|---|---|
| 数据结构变更 | 1 | service-api: RollingDemo* DTO |
| 接口变更 | 1 | service-api: 新增 GET /dashboard/rolling-demo |
| 逻辑变更 | 1 | web frontend: App.tsx data theater |
| 新增 | 5 | dashboard.py, test file, types.ts, api.ts, styles.css |

## 未匹配文件

以下文件未匹配到 `_module-map.yaml` 中的任何模块，因为项目模块映射尚未包含 frontend/web-ui 模块：

| 文件 | 说明 | 建议动作 |
|---|---|---|
| `ellectric/web/src/types.ts` | 前端类型定义 | 新增 web-ui 模块 |
| `ellectric/web/src/api.ts` | 前端 API 调用层 | 新增 web-ui 模块 |
| `ellectric/web/src/App.tsx` | 根 React 组件 | 新增 web-ui 模块 |
| `ellectric/web/src/styles.css` | 全局样式 | 新增 web-ui 模块 |

## 决策追踪验证

| D-xxx@vN | FR | 下游覆盖率 | 模块证据 | 状态 |
|---|---|---|---|---|
| D-001@v1 | FR-01 | task-06(taskCard), task-07 | types.ts, api.ts 使用 RollingDemo 命名，无 VVB 路由/模块 | PASS |
| D-002@v1 | FR-02, FR-03 | task-07, task-08, task-10 | App.tsx 数据剧场 + play/pause/speed + SVG panels | PASS |
| D-003@v1 | FR-04, FR-05, FR-06 | task-01..task-10 | 只读 endpoint，首屏仅 fetchRollingDemo，兼容性测试通过 | PASS |
| D-004@v1 | FR-04, FR-06, FR-07 | task-01, task-02, task-08 | DTO + service + 原生 SVG/CSS，无图表库依赖 | PASS |
