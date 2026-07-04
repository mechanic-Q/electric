---
author: lmr
created_at: 2026-07-04 08:27:15
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 开发者 | 使用项目学习 AI + 电力交易技术闭环，需要看到数据、预测、策略和解释性如何连接。 |
| 演示观看者 | 首次打开 WebUI，希望快速理解项目价值，不应被复杂表格或参数阻塞。 |
| 维护者 | 需要稳定、可测试、低依赖的 WebUI，不希望首页触发训练或重型仿真。 |
| Copilot 用户 | 在观看 rolling dashboard 时，通过右侧 Copilot 查询当前窗口、策略和报告含义。 |

## 功能需求

### FR-01: WebUI/Dashboard 命名与范围

覆盖决策：D-001@v1

Given 用户曾将 WebUI 写成 VVB
When 本变更生成文档、类型、文件和 UI 文案
Then 使用 WebUI/Dashboard 作为 canonical term，不新增 VVB 模块、路由或概念

### FR-02: 数据剧场首屏

覆盖决策：D-002@v1

Given 用户打开 WebUI 根页面
When 页面初始加载完成
Then 首屏展示山东 15min rolling data theater，而不是能力目录或复杂分析工作台

Given 首屏展示数据剧场
When 用户观察页面
Then 看到数据基座、负荷预测、电价形态、风光出力、策略回放、解释性证据这些模块化面板

### FR-03: Rolling playback 控制

覆盖决策：D-002@v1

Given rolling demo payload 加载成功
When 页面进入播放状态
Then 当前 tick 按 15min 点推进，并同步驱动所有面板展示

Given 页面正在播放
When 用户点击 pause/play 或调整速度
Then 播放状态、速度和当前时间显示同步更新

### FR-04: 只读 rolling demo 后端接口

覆盖决策：D-003@v1, D-004@v1

Given API 服务运行
When 客户端请求 `GET /dashboard/rolling-demo` 且不传参数
Then 返回默认山东 `2025-10-01` 起 30 天窗口，`rows=2880`，`points_per_day=96`

Given 客户端传入 `days` 参数
When `days` 在 1 到 30 范围内
Then 返回对应天数窗口

Given 客户端传入 `days` 超过上限
When API 校验请求
Then 请求被拒绝或被明确限制到 30 天，避免首页加载过大 payload

### FR-05: 首页不触发重型计算

覆盖决策：D-003@v1

Given WebUI 首屏初始化
When 页面请求展示数据
Then 只调用 rolling demo 只读接口，不自动调用 `/predict`、`/simulate`、`/backtest` 触发训练、回测或重型仿真

### FR-06: 降级和 warnings 可见

覆盖决策：D-003@v1, D-004@v1

Given 山东数据某些可选字段、模型或报告缺失
When 后端生成 rolling demo payload
Then 响应包含 `warnings`，可用字段仍返回，页面展示降级状态而不崩溃

Given 前端收到带 warnings 的 payload
When 对应面板数据不完整
Then 面板显示 warning 或 fallback 状态，不抛出未处理异常

### FR-07: 原生 SVG/CSS 图表

覆盖决策：D-004@v1

Given 前端实现 rolling dashboard
When 构建依赖和 package 配置被检查
Then 不新增 Plotly、ECharts、Recharts 等图表库

Given dashboard payload 加载成功
When 页面渲染图表
Then 使用 React + TypeScript + SVG/CSS 渲染负荷线图、电价热力、风光面积、策略 P&L/排名

### FR-08: 兼容现有 API 和 Copilot

覆盖决策：D-001@v1, D-003@v1

Given 现有 API 已提供 `/predict`、`/simulate`、`/backtest`、`/chat/stream`、`/capabilities`、`/datasets`、`/reports`
When 本变更完成
Then 这些端点保持现有语义，不因 rolling dashboard 被重写或删除

Given WebUI 首屏被重构
When 用户需要自然语言查询
Then 右侧 Copilot sidebar 仍可用

## 非功能需求

- 兼容性：新增 endpoint 和前端数据剧场不得破坏现有 API route 和 static mount 顺序。
- 可回退：数据/模型/报告缺失时返回 warnings 和部分 payload，不让首页崩溃。
- 可测试：后端必须有测试覆盖默认窗口、字段结构、days 上限和 warnings 降级；前端必须通过 `npm run build`。
- 性能：默认 payload 限制为最多 30 天、2880 点；图表可采样展示，避免 DOM/SVG 过重。
- 依赖控制：不新增前端图表依赖；优先使用已有 React/Vite/TypeScript。
- 响应式：移动端布局可读，Copilot 在窄屏下可下移或折叠到主内容后方。
- 真实性：首屏数据来自山东 15min 历史数据，不使用纯静态假数据作为最终实现。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-08 | VVB 纠正为 WebUI/Dashboard，不新增概念。 |
| D-002@v1 | FR-02, FR-03 | 首屏目标为数据剧场和 rolling playback。 |
| D-003@v1 | FR-04, FR-05, FR-06, FR-08 | 首页仿真语义限定为历史回放，不触发重型计算。 |
| D-004@v1 | FR-04, FR-06, FR-07 | 方案 A：只读 endpoint + 原生 SVG/CSS。 |
