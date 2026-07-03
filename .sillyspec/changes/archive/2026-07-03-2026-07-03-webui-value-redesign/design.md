---
author: lmr
created_at: 2026-07-03 17:01:37
---

# Design — WebUI Value Redesign

## 背景

当前 WebUI 已经完成 FastAPI 静态页面、SSE Chat、能力目录、数据集目录和报告目录接入，但页面主体验仍像“聊天助手”。这弱化了项目最有价值的内容：山东 15min 真实数据、负荷/电价/风光预测、RL 策略评估、SHAP/Weather 解释和离线报告证据链。

用户以电力预测交易领域专家视角确认，本轮目标不是继续包装“AI 聊天”，而是把 WebUI 改造成能传达项目技术闭环价值的 Dashboard-first 界面：先展示可验证事实，再用 Copilot 辅助解释。

用户在方案选择中明确选择方案 C：前端框架化重构。仓库当前没有 Node/Vite/React 基础，因此本变更会新增最小前端构建链路，并保持后端 API 兼容。

## 设计目标

1. 将 WebUI 首页从 Chat-first 改为 Dashboard-first。
2. 首屏清楚展示“山东 15min 数据 → 预测 → 策略评估 → 解释 → 报告溯源”的端到端闭环。
3. 新增框架化前端源码目录 `ellectric/web/`，采用 Vite + React + TypeScript。
4. 前端构建产物输出到 `ellectric/api/static/`，FastAPI 继续通过 `GET /` 服务页面。
5. 复用现有 `/capabilities`、`/datasets`、`/reports`、`/chat/stream`、`/predict` 等端点，不改变其语义。
6. Chat 降级为右侧 Copilot，继续展示 SSE token、tool_call、tool_result 和结构化结果卡。
7. 所有指标、报告和 Copilot 答案必须标注来源，避免无来源数字和 LLM 编造。
8. 页面文案明确学习原型边界，不暗示真实交易、下单、准实时调度或收益承诺。

## 非目标

- 不做真实交易、真实下单、实盘接口或收益承诺。
- 不做准实时 T+15min 调度，不新增 cron/daemon/queue。
- 不做模型重训，不重新生成已有报告。
- 不做登录、权限、多用户或聊天记录持久化。
- 不新增数据库或后端状态表。
- 不新增 `/dashboard-summary` 聚合端点，除非实现阶段证明现有端点无法满足首屏加载。
- 不重写 FastAPI 业务层，不改变旧 REST/SSE API 响应语义。
- 不把完整 Grafana/Plotly 仪表盘迁入 WebUI。

## 拆分判断

本变更不拆分，也不走批量模式。

理由：虽然引入前端框架、静态资源挂载、Dashboard 组件和 Copilot 组件，但它们服务同一个用户入口和同一信息架构目标。如果拆成“前端脚手架”“Dashboard”“Copilot”“文案治理”等多个变更，容易造成 API 契约和页面叙事漂移。任务数量不会出现模板 × 大量实例的批量模式。

## 总体方案

### Wave 1: 前端构建骨架

新增 `ellectric/web/` 作为前端源代码根目录。最小栈为 Vite + React + TypeScript，不引入 UI 组件库，不引入状态管理库。前端构建产物输出到 `ellectric/api/static/`，让既有 FastAPI 静态挂载继续工作。

新增前端脚本：`npm run dev` 用于前端开发，`npm run build` 用于生成静态产物。构建输出必须包含 `index.html`，以替代当前单文件页面。旧 `ellectric/api/static/index.html` 可以由构建产物覆盖，但源码维护位置迁移到 `ellectric/web/src/`。

### Wave 2: Dashboard-first 信息架构

前端页面分为五个主区：

- Header：项目名、山东 15min 数据资产摘要、非交易声明。
- Value Chain：公开数据 → 预测 → 回测/RL 评估 → 解释 → 报告溯源。
- Forecast Lab：负荷、电价、风电、光伏能力卡和基线指标来源。
- Strategy Evaluation：PPO/SAC/TD3 与 persistence/mean/oracle 对比，展示 total_pnl、sharpe、drawdown、oracle_gap 等报告指标。
- Explainability + Reports/Data：SHAP、Weather Tier4、reports/datasets/capabilities 溯源卡。

布局采用桌面双栏：主 Dashboard + 右侧 Copilot。移动端改为单列，Copilot 下沉或折叠。

### Wave 3: Data/Report/API 接入

Dashboard 首屏直接调用现有只读端点：

- `GET /capabilities`：渲染能力清单与可问问题。
- `GET /datasets`：渲染山东数据资产和辅助数据源。
- `GET /reports`：渲染最新报告卡和关键指标。
- `GET /reports/{report_id:path}`：按需读取详细报告。

预测、回测、解释类实时操作仍走既有端点，不改变语义。缺实时模型时，UI 使用现有 tool/report fallback 信息展示离线报告来源。

### Wave 4: Copilot 迁移

把当前单文件 Web Chat 的 SSE 行为迁移到 React 组件：用户输入、history、streaming token、tool_call 状态、tool_result 结构化卡片、error/done 状态。事件字段沿用现有协议：`type`、`name`、`args`、`content`、`payload`、`message`。

Copilot 的角色是解释 Dashboard 上的指标和读取报告，不作为唯一入口。欢迎问题优先围绕山东数据、Weather Tier4、RL 评估、预测基线和报告目录。

### Wave 5: 风险文案与兼容验证

所有“交易建议 / 自动交易 / 下单 / 实盘 / 收益保证”类表达改为“策略评估 / 回测 / 假设分析 / 学习原型 / 非交易建议”。

验证重点：前端构建成功；FastAPI 仍能服务页面；旧 API 路由仍注册；Dashboard 能在缺少部分报告或模型时降级显示；移动端可读；Copilot SSE 基础协议不破坏。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/web/package.json` | 前端 package 脚本和依赖声明。 |
| 新增 | `ellectric/web/vite.config.ts` | Vite 构建配置，输出到 `../api/static`。 |
| 新增 | `ellectric/web/tsconfig.json` | TypeScript 配置。 |
| 新增 | `ellectric/web/index.html` | Vite HTML 入口。 |
| 新增 | `ellectric/web/src/main.tsx` | React 入口。 |
| 新增 | `ellectric/web/src/App.tsx` | Dashboard-first 页面组合。 |
| 新增 | `ellectric/web/src/api.ts` | 对现有 FastAPI 端点的 fetch client。 |
| 新增 | `ellectric/web/src/types.ts` | 前端使用的 API/SSE 类型。 |
| 新增 | `ellectric/web/src/styles.css` | 页面样式和响应式布局。 |
| 修改 | `ellectric/api/static/index.html` | 改为构建产物；实现时由 Vite build 生成或替换。 |
| 修改 | `ellectric/api/server.py` | 如必要，调整 StaticFiles 挂载以兼容构建产物；不改业务 API 语义。 |
| 修改 | `tests/test_api_catalog.py` | 保留 legacy route 测试，必要时补充 `GET /` 静态页面 smoke。 |
| 新增 | `tests/test_web_static.py` | 可选：验证构建后静态页面存在并由 FastAPI 返回。 |
| 修改 | `README.md` | 更新 WebUI 启动/构建说明与 Dashboard-first 说明。 |
| 新增 | `.sillyspec/changes/2026-07-03-webui-value-redesign/prototype-dashboard-first.html` | 已生成的线框原型。 |

## 接口定义

本变更不新增后端业务 API。前端 TypeScript 类型镜像现有响应结构，字段必须保持宽松，以兼容后端扩展。

### 前端 fetch client（新增）

```ts
type SourceStatus = "api" | "offline_report" | "fallback" | "missing" | "error";

interface CapabilityItem {
  id: string;
  title: string;
  category: string;
  description: string;
  example_questions: string[];
  endpoint?: string | null;
  tool_name?: string | null;
  supports_offline_fallback?: boolean;
  available?: boolean;
}

interface DatasetInfo {
  id: string;
  title: string;
  description: string;
  source: string;
  frequency?: string | null;
  rows?: number | null;
  start?: string | null;
  end?: string | null;
  columns?: string[];
  available?: boolean;
}

interface ReportSummary {
  id: string;
  title: string;
  report_type: string;
  status: "ok" | "missing" | "error" | "degraded";
  generated_at?: string | null;
  summary: string;
  metrics?: Record<string, number | string | boolean | null>;
  paths?: Record<string, string>;
}
```

### SSE 事件（沿用）

```ts
type ChatEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; name?: string; args?: unknown }
  | { type: "tool_result"; name?: string; content?: string; payload?: unknown }
  | { type: "error"; message?: string; content?: string }
  | { type: "done" };
```

## 数据模型

不新增数据库表，不改变报告文件格式，不改变后端 Pydantic schema。前端只消费现有 JSON 响应和报告文件摘要。

Dashboard 卡片内部数据模型按来源区分：

- `api`: 实时 API 结果。
- `offline_report`: 离线报告结果。
- `fallback`: 实时失败后使用报告 fallback。
- `missing`: 报告或模型缺失，UI 显示不可用而非报错崩溃。
- `error`: API 请求失败，UI 显示错误卡。

## 兼容策略

- 旧 FastAPI 端点继续注册，不改请求/响应语义。
- `GET /` 仍返回 Web 页面；只是页面产物来自 Vite build。
- 未执行前端 build 时，开发者可通过 `ellectric/web` 的 dev server 调试；生产/演示使用构建产物。
- 缺 `DEEPSEEK_API_KEY` 时，Dashboard 仍能展示数据/报告；只有 Copilot 显示配置错误。
- 缺模型文件时，不改变 `/predict` 原错误语义；UI/Copilot 显示离线报告 fallback 或 unavailable。
- 缺报告时，Report card 显示 missing/error，不阻断整个页面。
- 不删除 catalog/report 相关后端能力。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 新增 Node/Vite 使项目从纯 Python 变为双栈 | P1 | 前端隔离在 `ellectric/web/`；README 明确可选构建步骤；后端 API 不依赖 Node 运行时。 |
| R-02 | 构建产物覆盖现有 `api/static/index.html` 导致回退困难 | P1 | 源码迁移到 `ellectric/web/src/`，保留 git diff；构建输出只作为产物，必要时可重新 build。 |
| R-03 | 前端类型与后端 schema 漂移 | P1 | 类型保持宽松；API smoke 测试保留 legacy routes；前端 client 对缺字段降级。 |
| R-04 | Dashboard 首屏请求多个端点导致加载慢或部分失败 | P2 | 并行请求，单卡片错误隔离；不因一个 report 缺失阻断页面。 |
| R-05 | 交易文案误导用户以为可实盘交易 | P0 | Guardrail 文案与测试/审查要求：只用“策略评估/回测/假设分析/非交易建议”。 |
| R-06 | Copilot 迁移破坏 SSE tool_result 展示 | P1 | 保留 SSE 事件字段协议；新增或复用 streaming event 测试；前端兼容 `message/content`。 |
| R-07 | 引入前端框架超出原本最小改动路线 | P1 | 这是用户明确选择的方案 C；控制依赖，不引入 UI 库和状态管理库。 |

## 决策追踪

- D-001@v1 覆盖：设计目标 1-2，总体方案 Wave 2。结论：Dashboard-first 是页面主定位。
- D-002@v2 覆盖：设计目标 3-4，总体方案 Wave 1，文件变更清单。结论：允许 Vite + React + TypeScript 框架化重构。
- D-003@v1 覆盖：非目标、总体方案 Wave 5、风险 R-05。结论：交易能力只展示为学习用策略评估。
- D-004@v1 覆盖：设计目标 7、Wave 3、数据模型、兼容策略。结论：指标和回答必须可溯源。
- D-005@v1 覆盖：设计目标 5、接口定义、兼容策略。结论：后端业务 API 保持兼容。

## 自审

| 检查项 | 结论 |
|---|---|
| 需求覆盖 | 通过：覆盖 Dashboard-first、方案 C、Copilot、非交易边界和来源标注。 |
| Grill 覆盖 | 通过：design 引用 D-001@v1、D-002@v2、D-003@v1、D-004@v1、D-005@v1。 |
| 约束一致性 | 通过：后端 API 兼容；新增前端栈是用户明确选择；不新增真实交易/调度。 |
| 真实性 | 通过：现有 API 来自当前 FastAPI/catalog 设计；新文件均标注为新增。 |
| YAGNI | 通过：不新增 UI 库、状态管理、dashboard-summary、认证、多用户。 |
| 验收标准 | 通过：构建、静态服务、legacy routes、Dashboard 信息架构和风险文案均可验证。 |
| 非目标 | 通过：明确排除真实交易、调度、重训、认证、数据库。 |
| 兼容策略 | 通过：旧 REST/SSE API 不改；缺 key/模型/报告都有降级口径。 |
| 风险识别 | 通过：识别双栈、构建产物、schema 漂移、误导性文案和 SSE 迁移风险。 |
| 生命周期契约表 | 不适用：本变更不新增 session/lease/daemon/heartbeat 状态机；Copilot 沿用现有 SSE 请求生命周期。 |

## Design Grill Result

status: passed

### Cross-Check Matrix

| ID | 层级 | 交叉点 | 证据 A | 证据 B | 结论 | 决策 |
|---|---|---|---|---|---|---|
| X-001 | consistency | 前端 `ReportSummary.status` vs 后端 schema | design.md 接口定义 | `ellectric/service/schemas.py` `ReportStatus = Literal["ok", "missing", "error", "degraded"]` | conflict fixed: 前端类型加入 `degraded` | D-004@v1 |
| X-002 | consistency | Dashboard report 来源标注 vs catalog 真实字段 | design.md 目标 7 / Wave 3 | `ReportSummary` 提供 `generated_at`、`metrics`、`metrics_meta`、`paths` | passed: 可由现有字段支持 | D-004@v1 |
| X-003 | consistency | 旧 API 兼容 vs FastAPI 路由注册 | design.md 兼容策略 | `ellectric/api/server.py` 在 `app.mount("/")` 前注册 catalog/legacy routes；`tests/test_api_catalog.py` 覆盖注册顺序 | passed: 只需保留注册顺序 | D-005@v1 |
| X-004 | feasibility | Vite 构建产物挂载 vs 当前静态目录 | design.md Wave 1 | `ellectric/api/static/index.html` 已存在，`server.py` 使用 `StaticFiles(directory=_STATIC_DIR, html=True)` | passed: 输出到该目录可继续服务 `GET /`；禁止引入多路由 SPA 依赖 | D-002@v2 |
| X-005 | consistency | Copilot SSE 迁移 vs 当前事件协议 | design.md Wave 4 | `tests/test_chat_streaming_events.py` 覆盖 `token/tool_call/tool_result/error/done` | passed: React 端按现有事件兼容实现 | D-005@v1 |
| X-006 | feasibility | RL 策略评估卡 vs 真实评估模块 | design.md Wave 2 | `rl-evaluation.md` 定义 `total_pnl/sharpe/win_rate/max_drawdown/profit_factor/volatility/oracle_gap/baseline_delta/rank/status` | passed: 卡片指标来自离线报告，不需重训 | D-001@v1 |
| X-007 | boundary | 交易展示 vs 项目排除项 | design.md 非目标 / Wave 5 | ROADMAP 排除真实交易、准实时调度；D-003@v1 | passed: UI 文案必须保持学习/回测/评估口径 | D-003@v1 |

### Question Distribution

| 分类 | 数量 | 含义 |
|---|---:|---|
| immediately_answered | 1 | `degraded` 状态由代码确认并已修正。 |
| needs_thinking | 0 | 无需用户继续判断。 |
| unresolved | 0 | 无 P0/P1 未决设计漏洞。 |

### Unresolved Blockers

| ID | priority | 问题 | 阻塞原因 | 下一步 |
|---|---|---|---|---|
| — | — | 无 | — | 进入 requirements/tasks/plan。 |
