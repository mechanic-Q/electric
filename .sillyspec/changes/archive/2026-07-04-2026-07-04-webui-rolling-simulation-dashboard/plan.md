---
author: lmr
created_at: 2026-07-04 08:36:12
plan_level: full
---

# 实现计划

## Wave 1（后端契约与只读数据）

- [ ] task-01: 新增 rolling dashboard Pydantic schema（覆盖：FR-04, FR-06, D-003@v1, D-004@v1）
- [ ] task-02: 新增山东 rolling demo 只读 service（覆盖：FR-04, FR-05, FR-06, D-003@v1, D-004@v1）
- [ ] task-03: 添加后端 rolling demo 测试（覆盖：FR-04, FR-05, FR-06）

## Wave 2（API 路由与兼容性）

- [ ] task-04: 注册 `GET /dashboard/rolling-demo` API route（覆盖：FR-04, FR-05, FR-08, D-003@v1）
- [ ] task-05: 验证现有 API route 和 static mount 兼容（覆盖：FR-08, D-003@v1）

## Wave 3（前端数据剧场）

- [ ] task-06: 新增前端 rolling dashboard 类型和 fetch 方法（覆盖：FR-01, FR-04, FR-05, FR-06, D-001@v1, D-003@v1, D-004@v1）
- [ ] task-07: 重构 WebUI 首屏为 rolling data theater（覆盖：FR-02, FR-03, FR-05, FR-08, D-002@v1, D-003@v1）
- [ ] task-08: 实现原生 SVG/CSS 图表和响应式样式（覆盖：FR-02, FR-03, FR-07, D-002@v1, D-004@v1）

## Wave 4（端到端验证）

- [ ] task-09: 运行后端 rolling demo 测试和 API smoke check（覆盖：FR-04, FR-05, FR-06, FR-08）
- [ ] task-10: 运行 WebUI build 并确认首屏不调用重型端点（覆盖：FR-02, FR-03, FR-05, FR-07, FR-08, D-002@v1, D-003@v1, D-004@v1）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | 新增 rolling dashboard Pydantic schema | W1 | P0 | — | FR-04, FR-06, D-003@v1, D-004@v1 | 定义新增只读 payload 的请求/响应结构，不改变现有 schema 语义。 |
| task-02 | 新增山东 rolling demo 只读 service | W1 | P0 | task-01 | FR-04, FR-05, FR-06, D-003@v1, D-004@v1 | 从山东 15min 数据构建默认 30 天展示 payload，并提供 warnings 降级。 |
| task-03 | 添加后端 rolling demo 测试 | W1 | P0 | task-01, task-02 | FR-04, FR-05, FR-06 | 覆盖默认窗口、字段结构、days 上限和降级行为。 |
| task-04 | 注册 `GET /dashboard/rolling-demo` API route | W2 | P0 | task-01, task-02 | FR-04, FR-05, FR-08, D-003@v1 | 在 FastAPI 注册新只读路由，不重写现有路由。 |
| task-05 | 验证现有 API route 和 static mount 兼容 | W2 | P0 | task-04 | FR-08, D-003@v1 | 确认 `/predict`、`/simulate`、`/backtest`、`/chat/stream`、catalog route 和 `/` 静态页仍可达。 |
| task-06 | 新增前端 rolling dashboard 类型和 fetch 方法 | W3 | P0 | task-01, task-04 | FR-01, FR-04, FR-05, FR-06, D-001@v1, D-003@v1, D-004@v1 | WebUI 使用 WebUI/Dashboard 命名，通过单一 fetch 方法读取新 endpoint。 |
| task-07 | 重构 WebUI 首屏为 rolling data theater | W3 | P0 | task-06 | FR-02, FR-03, FR-05, FR-08, D-002@v1, D-003@v1 | 首屏以 rolling playback 和模块化面板为主，保留 Copilot sidebar。 |
| task-08 | 实现原生 SVG/CSS 图表和响应式样式 | W3 | P0 | task-07 | FR-02, FR-03, FR-07, D-002@v1, D-004@v1 | 用现有 React/Vite + SVG/CSS 展示线图、热力、面积、P&L/排名，不加图表库。 |
| task-09 | 运行后端 rolling demo 测试和 API smoke check | W4 | P0 | task-03, task-04, task-05 | FR-04, FR-05, FR-06, FR-08 | 以可执行测试证明只读 endpoint 和兼容 route 行为。 |
| task-10 | 运行 WebUI build 并确认首屏不调用重型端点 | W4 | P0 | task-06, task-07, task-08 | FR-02, FR-03, FR-05, FR-07, FR-08, D-002@v1, D-003@v1, D-004@v1 | TypeScript/Vite build 通过；首屏数据源限定为 rolling demo。 |

## 关键路径

task-01 → task-02 → task-04 → task-06 → task-07 → task-08 → task-10

## 调用点搜索记录

- `rtk grep -n "(app\.(get|post)|ForecastRequest|BacktestRequest|SimulationRequest|fetch[A-Z]|/dashboard|capabilities|datasets|reports|chat|apiFetch)" ellectric/api ellectric/service ellectric/web/src tests`
- `rtk grep -n "(Rolling|Dashboard|Demo|rolling-demo|dashboard)" ellectric/api ellectric/service ellectric/web/src tests .sillyspec/changes/2026-07-04-webui-rolling-simulation-dashboard`
- 结论：现有 API route 集中在 `ellectric/api/server.py`；service schema/handlers 调用点集中在 `ellectric/service/schemas.py` 和 `ellectric/service/handlers.py`；前端 API 入口集中在 `ellectric/web/src/api.ts`；首屏入口集中在 `ellectric/web/src/App.tsx`；`ellectric/api/static/assets/*` 为构建产物，本计划不手改。

## 全局验收标准

- [ ] `GET /dashboard/rolling-demo` 默认返回山东 2025-10-01 起 30 天、2880 点、96 点/日 payload。
- [ ] payload 顶层包含 `meta`、`series`、`panels`、`strategy`、`reports`、`warnings`。
- [ ] 数据/模型/报告缺失时通过 warnings 或面板降级展示，不让 API 或 WebUI 崩溃。
- [ ] WebUI 首屏只自动请求 rolling demo，不自动调用 `/predict`、`/simulate`、`/backtest`。
- [ ] 现有 `/predict`、`/simulate`、`/backtest`、`/chat/stream`、`/capabilities`、`/datasets`、`/reports` 和静态首页行为保持兼容。
- [ ] 不新增 Plotly、ECharts、Recharts 等前端图表依赖。
- [ ] 后端 rolling demo 测试通过。
- [ ] `npm run build` 在 `ellectric/web/` 通过。
- [ ] 移动端布局可读，Copilot 在窄屏下不遮挡主舞台。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-06 | 类型、fetch、UI 文案使用 WebUI/Dashboard 命名，无 VVB 概念。 |
| D-002@v1 | task-07, task-08, task-10 | 首屏为 rolling data theater，有 play/pause、速度和模块化图表。 |
| D-003@v1 | task-01, task-02, task-04, task-05, task-06, task-07, task-09, task-10 | 新 endpoint 只读，首屏不触发训练、回测或重型仿真，现有端点兼容。 |
| D-004@v1 | task-01, task-02, task-06, task-08, task-10 | 后端 read-only endpoint + 前端原生 SVG/CSS；package 依赖无新增图表库。 |
| FR-01 | task-06 | WebUI/Dashboard canonical term。 |
| FR-02 | task-07, task-08, task-10 | WebUI 根页面展示数据剧场。 |
| FR-03 | task-07, task-08, task-10 | rolling playback 控制同步驱动面板。 |
| FR-04 | task-01, task-02, task-03, task-04, task-09 | endpoint 默认窗口、rows、points_per_day 和 days 上限可测试。 |
| FR-05 | task-02, task-04, task-06, task-07, task-09, task-10 | 首页不自动调用重型端点。 |
| FR-06 | task-01, task-02, task-03, task-06, task-09 | warnings 和前端降级可见。 |
| FR-07 | task-08, task-10 | 原生 SVG/CSS 图表，未新增图表库。 |
| FR-08 | task-04, task-05, task-07, task-09, task-10 | 现有 API 和 Copilot sidebar 保持可用。 |

## 自检结果

- [x] 每个 task 有编号（task-01、task-02 ...）
- [x] 每个 task 在 Wave 下有 checkbox（`- [ ] task-XX:` 格式）
- [x] 已标注 Wave 分组和依赖关系
- [x] 有任务总表（含优先级、依赖列，无估时列）
- [x] 有关键路径标注
- [x] 有全局验收标准
- [x] 覆盖矩阵覆盖全部当前版本 D-xxx@v1 和 FR-xx
- [x] 不存在 P0/P1 unresolved blocker
- [x] brownfield 兼容性条款已纳入全局验收
- [x] 未放接口定义或代码示例等实现细节
- [x] plan.md 与 design.md 的文件变更清单一致
- [x] DTO/client/API 方法变更已搜索调用点并纳入任务范围
- [x] 调用点搜索命令和结论已记录
- [x] 依赖关系非平凡但文字关键路径足够，未生成 Mermaid 图
- [x] 没有泛泛风险分析
