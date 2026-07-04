---
author: lmr
created_at: 2026-07-04 08:27:15
---

# Design — WebUI Rolling Simulation Dashboard

## 背景

项目已经有山东 15min 历史数据、预测/回测/解释性能力和 React + Vite WebUI，但当前 WebUI 更像能力目录和报告索引，缺少一个能直观看到“公开数据 → 预测 → 仿真/策略 → 解释性证据”闭环的主舞台。

用户明确不追求靠近当前日期，而是要使用山东数据最丰富、最扎实的历史窗口做滚动预测/模拟展示。用户也确认 `VVB` 是误写，实际目标是 WebUI；首屏应优先做“数据剧场展示”，不是复杂分析工作台。

## 设计目标

- FR-001: 新增只读 dashboard rolling demo 能力，默认使用山东 `2025-10-01` 起 30 天、15min 粒度窗口。
- FR-002: WebUI 首屏改为数据剧场，页面加载后自动滚动展示历史窗口。
- FR-003: 以独立模块展示数据基座、负荷预测、电价形态、风光出力、策略回放、解释性证据。
- FR-004: 首页展示必须稳定，不能触发训练、准实时交易或重型 ASSUME 仿真。
- FR-005: 数据/模型/报告字段缺失时可降级并通过 warnings 暴露，页面不能崩。
- FR-006: 不新增前端图表依赖，使用 React + TypeScript + SVG/CSS 实现展示图。
- FR-007: 保留现有 `/predict`、`/simulate`、`/backtest`、chat、capabilities、datasets、reports 能力，不破坏现有 API。

## 非目标

- 不做准实时 T+15min 调度或实时交易下单。
- 不在首页触发模型训练、RL 训练或 ASSUME 深度仿真。
- 不把 WebUI 改成复杂筛选/表格/指标分析工作台。
- 不引入 Plotly、ECharts、Recharts 等新前端图表库。
- 不重写现有 `/predict`、`/simulate`、`/backtest` API 语义。
- 不修复无关 SillySpec 孤儿目录、`.sillyspec/STACK.md` 或 `renewable-forecaster` 模块卡片缺失问题。

## 拆分判断

本变更不拆分，也不走批量模式。

理由：虽然页面包含 5+ 个展示面板，但它们共享同一个山东 15min rolling window、同一个只读展示接口、同一套播放状态和同一首屏目标。它是一个纵向 WebUI slice，而不是多个低耦合功能。没有多角色权限、跨页面审批流，也不是“模板 × 大量实例”的批量生成任务。

## 总体方案

### Wave 1: 后端只读展示接口

新增 `ellectric/service/dashboard.py`，提供一个无训练、无副作用的 rolling demo builder。它从山东数据加载器读取指定窗口，默认 `start=2025-10-01`、`days=30`，上限 30 天。返回结构化 payload：`meta`、`series`、`panels`、`strategy`、`reports`、`warnings`。

新增/扩展 schema，定义请求和响应 DTO。FastAPI 在 `ellectric/api/server.py` 暴露 `GET /dashboard/rolling-demo`。该接口只做读取、筛选、轻量派生和降级标记，不调用训练器或重型仿真。

### Wave 2: 前端数据剧场

扩展 `ellectric/web/src/types.ts` 和 `ellectric/web/src/api.ts`，新增 rolling demo fetch 类型和方法。重构 `ellectric/web/src/App.tsx` 为数据剧场首屏：顶部声明学习原型/非真实交易；主区域为 rolling stage；模块面板展示负荷、电价、风光、策略、证据；右侧保留 Copilot sidebar。

图表用原生 SVG/CSS 组件或局部函数实现，不新增依赖。播放状态只存在于前端：play/pause、速度、当前 tick、窗口进度。所有面板由同一个 current index 驱动。

### Wave 3: 验证与静态构建

新增后端测试，覆盖默认窗口、点数、字段、warnings 降级和非法 days 上限。运行可用的 pytest 目标。前端运行 `npm run build`，确保 TypeScript/Vite 编译通过。必要时启动 FastAPI 做 smoke check，确认静态页面可加载并请求新 endpoint。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/service/dashboard.py` | 只读 rolling demo payload builder；读取山东历史窗口，生成 series/panels/strategy/reports/warnings。 |
| 修改 | `ellectric/service/schemas.py` | 新增 rolling dashboard 请求/响应 Pydantic schema。 |
| 修改 | `ellectric/api/server.py` | 新增 `GET /dashboard/rolling-demo` 路由，不影响现有路由。 |
| 修改 | `ellectric/web/src/types.ts` | 新增 rolling dashboard TypeScript 类型。 |
| 修改 | `ellectric/web/src/api.ts` | 新增 `fetchRollingDemo()`。 |
| 修改 | `ellectric/web/src/App.tsx` | 重构首屏为数据剧场，保留 Copilot sidebar。 |
| 修改 | `ellectric/web/src/styles.css` | 新增数据剧场、SVG/CSS 图表、响应式布局样式。 |
| 新增 | `tests/test_dashboard_rolling_demo.py` | 后端只读接口/服务测试。 |
| 已新增 | `.sillyspec/changes/2026-07-04-webui-rolling-simulation-dashboard/prototype-rolling-dashboard.html` | 线框 HTML 原型，仅用于设计确认。 |

## 接口定义

### HTTP Endpoint

```http
GET /dashboard/rolling-demo?start=2025-10-01&days=30
```

Rules:

- `start` optional, default `2025-10-01`.
- `days` optional, default `30`, allowed range `1..30`.
- Response is read-only and deterministic for same data files.
- Endpoint must not train models, mutate files, or launch heavy simulation.

### Proposed Python Service API

```python
def build_rolling_demo(start: str | None = None, days: int = 30) -> RollingDemoResponse:
    """Build read-only dashboard payload from Shandong historical data."""
```

### Response Shape

```json
{
  "meta": {
    "source": "shandong",
    "start": "2025-10-01T00:00:00Z",
    "end": "2025-10-30T23:45:00Z",
    "frequency": "15min",
    "points_per_day": 96,
    "rows": 2880
  },
  "series": {
    "timestamps": [],
    "load_actual": [],
    "load_forecast": [],
    "price_rt": [],
    "price_da": [],
    "wind_actual": [],
    "solar_actual": [],
    "tie_line": [],
    "pumped_storage": []
  },
  "panels": [],
  "strategy": {
    "ranking": [],
    "pnl_curves": {}
  },
  "reports": [],
  "warnings": []
}
```

## 数据模型

No database schema changes.

Data model is response DTO only:

- `RollingDemoMeta`: source, start, end, frequency, points_per_day, rows.
- `RollingDemoSeries`: aligned arrays by timestamp.
- `RollingDemoPanel`: id, title, chart_type, summary metrics, warning ids.
- `RollingDemoStrategy`: strategy ranking and optional cumulative P&L curves.
- `RollingDemoReportEvidence`: report id/title/status/summary/metrics.
- `warnings: list[str]`: visible degradations.

Implementation must align arrays by timestamp and keep all numeric values JSON-serializable.

## 兼容策略

- Existing endpoints remain unchanged: `/predict`, `/simulate`, `/backtest`, `/explain`, `/recommend`, `/chat`, `/capabilities`, `/datasets`, `/reports`.
- If the new endpoint fails, existing API behavior remains unchanged.
- If optional model/report artifacts are missing, response includes warnings and falls back to raw series / simple baselines instead of raising homepage-breaking errors.
- Frontend can render partial data: each panel checks series availability and shows warning state instead of throwing.
- No new npm dependency, so existing Vite build pipeline remains unchanged.

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 山东 loader column names differ from planned response fields. | P1 | Implement explicit field detection/fallback mapping and warnings; test required fields. |
| R-02 | 30 days × 96 arrays are too large for initial page load. | P2 | Cap `days <= 30`; 2880 points is acceptable for JSON and SVG downsampling; render charts with sampled points where needed. |
| R-03 | Existing reports contain degraded or stale evidence. | P1 | Surface report status and warnings; do not claim metrics are fresh unless loaded from specific report metadata. |
| R-04 | Frontend SVG chart logic becomes too complex. | P2 | Keep chart primitives minimal: line, heatmap, area, bars; defer advanced tooltip/zoom. |
| R-05 | Homepage accidentally calls heavy endpoints. | P1 | Use only `fetchRollingDemo()` for first-screen payload; keep predict/simulate/backtest out of initial render path. |
| R-06 | Mobile layout becomes unreadable. | P2 | Use responsive grid collapse and keep Copilot below main content on narrow screens. |

## 决策追踪

- D-001@v1 covered by naming and non-goals: implementation uses WebUI/Dashboard terms only.
- D-002@v1 covered by FR-002/FR-003 and Wave 2: first screen is data theater.
- D-003@v1 covered by FR-004/FR-005, interface rules, and R-05: homepage simulation is historical replay, not live training/heavy ASSUME.
- D-004@v1 covered by Wave 1/Wave 2 and file change list: read-only endpoint + native SVG/CSS.

No unresolved P0 decisions remain.

## 自审

- 需求覆盖: PASS. Covers Shandong richest-window playback, modular panels, cyclic animation, mixed chart types, data theater goal, non-real-time boundary.
- Grill/decision coverage: PASS. All current `D-xxx@v1` decisions in `decisions.md` are referenced.
- 约束一致性: PASS. Preserves learning-platform constraints, public data, lightweight models, no new frontend dependency.
- 真实性: PASS. Existing files are real: `ellectric/api/server.py`, `ellectric/service/schemas.py`, `ellectric/web/src/App.tsx`, `types.ts`, `api.ts`, `styles.css`; new files are marked as new.
- YAGNI: PASS. No chart library, no live training, no dashboard workbench scope.
- 验收标准: PASS. Tests and build checks are concrete.
- 非目标清晰: PASS. Scope creep boundaries explicit.
- 兼容策略: PASS. Existing endpoints unchanged, missing artifacts degrade via warnings.
- 生命周期契约表: N/A. This change only adds a stateless read-only HTTP endpoint and frontend playback state; no long-running ownership protocol is introduced.

## Design Grill Result

status: passed

### Cross-Check Matrix

| ID | 层级 | 交叉点 | 证据 A | 证据 B | 结论 | 决策 |
|---|---|---|---|---|---|---|
| X-001 | consistency | Response timestamp timezone | design response shape | `ShandongDataLoader.load_data()` constructs `pd.to_datetime(..., utc=True)` | fixed: examples use `Z` UTC timestamps | no new decision |
| X-002 | consistency | Homepage heavy compute boundary | design non-goals / FR-004 | existing `/simulate` and `/backtest` endpoints in `ellectric/api/server.py` | passed: new dashboard uses a separate read-only endpoint and does not replace existing endpoints | D-003@v1 |
| X-003 | feasibility | Required Shandong series fields | design series fields | `ellectric/pipeline/shandong_loader.py` maps load, price, wind, solar, tie line, pumped storage and optional forecasts | passed: fields are available when loader uses `include_forecasts=True`; warnings cover missing optional fields | D-004@v1 |
| X-004 | consistency | Frontend dependency constraint | design non-goal no chart dependency | existing `ellectric/web/src` uses React/Vite without chart library-specific types | passed: native SVG/CSS plan is compatible | D-004@v1 |
| X-005 | definition | Lifecycle table trigger | design self-review wording | SillySpec Step 11 lifecycle keyword rule | fixed: self-review now states stateless read-only endpoint without enumerating trigger terms | no new decision |

### Question Distribution

| 分类 | 数量 | 含义 |
|---|---:|---|
| immediately_answered | 2 | Timestamp timezone and lifecycle wording were corrected from code/workflow evidence. |
| needs_thinking | 0 | No remaining business choice needs user input. |
| unresolved | 0 | No P0/P1 blocker remains. |

### Unresolved Blockers

None.
