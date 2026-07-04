---
author: lmr
created_at: 2026-07-04 08:27:15
---

# Proposal

## 动机

当前 WebUI 已能展示能力目录、数据集和报告，但还没有一个首屏能直观看到“山东公开历史数据 → 预测 → 仿真/策略回放 → 解释性证据”的完整闭环。用户的数据是有限历史数据，核心价值不是追逐最新日期，而是选择山东 15min 数据最扎实的窗口做滚动模拟展示。

本变更将 WebUI 首屏改造成“数据剧场”：默认播放 2025-10 月 30 天、2880 个 15min 点，让访客一眼看到数据如何驱动预测、价格形态、风光出力、策略表现和报告证据。

## 关键问题

1. 现有 WebUI 更像目录页，缺少强主线。用户需要的是展示端到端技术闭环，而不是只列 capabilities、datasets、reports。
2. 现有 `/predict`、`/simulate`、`/backtest` 是按需计算接口，不适合首页自动循环播放。直接在首屏调用它们会带来延迟、不稳定和误触发重型计算风险。
3. 页面缺少真实山东 15min 数据驱动的可视化。静态报告或样例图不能体现“最丰富、最扎实数据窗口”的项目判断。

## 变更范围

- 新增只读 rolling demo 后端能力，默认返回山东 `2025-10-01` 起 30 天、15min 粒度的展示 payload。
- 新增 `GET /dashboard/rolling-demo`，返回 `meta`、`series`、`panels`、`strategy`、`reports`、`warnings`。
- 重构 WebUI 首屏为数据剧场，展示数据基座、负荷预测、电价热力、风光出力、策略回放、解释性证据。
- 使用现有 React/Vite/TypeScript 和原生 SVG/CSS 图表，不新增图表库。
- 保留右侧 Copilot sidebar，保持现有 chat 能力入口。
- 增加后端测试和前端 build 验证。

## 不在范围内（显式清单）

- 不做准实时 T+15min 调度。
- 不做真实交易、下单或资金相关能力。
- 不在首页训练模型、训练 RL agent 或运行重型 ASSUME 仿真。
- 不把首屏改成复杂筛选/表格/多条件分析工作台。
- 不引入 Plotly、ECharts、Recharts 等前端图表库。
- 不重写现有 `/predict`、`/simulate`、`/backtest`、`/chat`、`/reports` API 语义。
- 不处理无关 SillySpec 健康问题，例如孤儿目录、`.sillyspec/STACK.md` 缺失或 `renewable-forecaster` 模块卡片缺失。

## 成功标准（可验证）

- `GET /dashboard/rolling-demo` 默认返回山东数据窗口，`rows=2880`，`points_per_day=96`，时间范围为 2025-10-01 至 2025-10-30 UTC 对齐时间戳。
- 返回 payload 包含 `meta`、`series`、`panels`、`strategy`、`reports`、`warnings` 顶层字段。
- 页面加载后真实请求 `/dashboard/rolling-demo`，不调用 `/predict`、`/simulate`、`/backtest` 作为首屏自动播放数据源。
- WebUI 展示负荷线图、电价热力、风光面积、策略 P&L/排名、报告证据，并可 play/pause。
- 数据、模型或报告缺失时通过 warnings 和面板降级展示，页面不崩溃。
- 现有 `/predict`、`/simulate`、`/backtest`、`/chat/stream`、`/capabilities`、`/datasets`、`/reports` 行为不变。
- 后端测试通过，前端 `npm run build` 通过。
