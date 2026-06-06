---
id: task-06
title: 创建 07_model_comparison_dashboard.ipynb — 3 Tab plotly 仪表板
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P0
estimated_hours: 4
depends_on: [task-05]
blocks: []
allowed_paths:
  - ellectric/notebooks/07_model_comparison_dashboard.ipynb
---

# task-06: 创建 `07_model_comparison_dashboard.ipynb` — 3 Tab plotly 仪表板

## 修改文件

| 操作 | 文件 |
|------|------|
| 新建 | `ellectric/notebooks/07_model_comparison_dashboard.ipynb` |

## 实现要求

1. **从现有管道加载数据**：从 task-03 的 `LEARForecaster` 输出加载预测结果，从 task-05 的 DM/GW 检验加载对比数据
2. **3 Tab plotly 仪表板**：使用 `plotly.subplots.make_subplots` + `plotly.graph_objects` + `plotly.io`，纯 plotly（不依赖 dash/streamlit）
3. **风格一致**：与 Phase 1 notebook（04_load_forecasting.ipynb）完全一致的风格 — `pio.renderers.default = 'notebook'`、`hovermode='x unified'`、中文标签、`make_subplots`
4. **Tab 组织**：使用 plotly 的 `make_subplots(figure=fig, ...)` 配合 `fig.update_layout(updatemenus=...)` 或纯 plotly tabs 方式实现三 Tab 切换
5. **交互性**：每个图表支持 hover 查看数据点详情
6. **教学性**：每个 Tab 开头有 Markdown 说明，结尾有 思考题
7. **容错**：如果某些数据缺失（如 DM/GW 检验未运行），Tab 3 显示友好提示而非崩掉

### Tab 1: 预测总览 (`figure1`)

- **LEAR vs 实际叠加图**：展示最近 7 天逐小时预测 vs 实际，使用 `go.Scatter`（实际实线 `line=dict(width=2)`，预测虚线 `line=dict(dash='dash')`）
- **误差分布直方图**：`go.Histogram(nbinsx=30)`，红色虚线标注误差中位数和 ±MAE 范围
- 标题：`"日前电价预测 — 实际 vs LEAR"`

### Tab 2: 误差分析 (`figure2`)

- **error-by-hour heatmap (24h × 7d)**：`go.Heatmap(z=error_matrix, x=hour_labels, y=day_labels, colorscale='RdBu_r')`，显示最近一周每天每小时的预测误差
  - x 轴：0-23 小时
  - y 轴：最近 7 天的日期
  - z 值：预测误差（实际 - 预测），正值为低估，负值为高估
- **error-by-weekday**：按星期分组的平均绝对误差（`go.Bar`），x=周一至周日，y=MAE
- **error-by-month**：按月份分组的平均绝对误差（`go.Bar`），x=1-12 月，y=MAE

### Tab 3: 模型对比 (`figure3`)

- **MAE 条状图**：LEAR vs 持续法 vs 外部基准（如果有）的 MAE 对比（`go.Bar`），不同颜色区分模型
- **DM 检验结果表**：`go.Table` 渲染 DM 统计量、p-value、显著性判断（来自 task-05）
- **GW 检验结果表**：`go.Table` 渲染 GW 统计量、p-value、显著性判断（来自 task-05）
- 如果 task-05 未运行或数据不可用，显示 `"⚠ DM/GW 检验数据不可用，请先运行 task-05 统计检验"`

## Cell 结构

```
Cell 1 (markdown):   标题 + 学习目标
Cell 2 (code):       导入 + renderer 配置
Cell 3 (code):       加载数据（LEAR 预测 + 持续法 + 基准 + DM/GW）
Cell 4 (markdown):   === Tab 1: 预测总览 ===
Cell 5 (code):       Tab 1 图表（叠加图 + 直方图）
Cell 6 (markdown):   Tab 1 思考题
Cell 7 (markdown):   === Tab 2: 误差分析 ===
Cell 8 (code):       Tab 2 图表（热力图 + 星期/月份 bar）
Cell 9 (markdown):   Tab 2 思考题
Cell 10 (markdown):  === Tab 3: 模型对比 ===
Cell 11 (code):      Tab 3 图表（MAE bar + DM/GW tables）
Cell 12 (markdown):  Tab 3 思考题
Cell 13 (markdown):  综合反思题
```

## 数据加载规范

```python
# 从之前 notebook 的输出或重算
from pipeline.price_forecaster import LEARForecaster
from price_loader import PriceDataLoader, create_price_loader
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = 'notebook'

# 加载原始数据
loader = create_price_loader()
df = loader.load_data()

# 训练 LEAR 模型并预测
lear = LEARForecaster(alpha=0.01)
df_feat = lear.add_price_features(df, tier='tier2')
result = lear.train_evaluate(df_feat, tier='tier2')

# 持续法预测（价格数据用 lag_24h）
persistence_pred = df['price_da'].shift(24).bfill()

# 加载 DM/GW 检验结果（如果存在）
try:
    from run_statistical_tests import run_statistical_tests
    dm_gw_results = run_statistical_tests(...)
except (ImportError, FileNotFoundError):
    dm_gw_results = None
    print("⚠ DM/GW 检验数据不可用，Tab 3 将显示提示信息")
```

## 边界处理

| # | 场景 | 处理方法 |
|---|------|----------|
| 1 | LEAR 模型未训练或预测值为空 | 显示提示信息 `"⚠ 请先运行 06_price_forecasting.ipynb 训练 LEAR 模型"`，不崩溃 |
| 2 | 数据量不足 7 天（<168 行） | Tab 1 叠加图显示全部可用数据而非截取 7 天，Tab 2 热力图按实际天数显示，`logger.info` 告知 |
| 3 | DM/GW 检验结果文件缺失或为空 | Tab 3 显示友好提示而非报错，继续渲染前两个 Tab |
| 4 | 误差序列全为零或常数 | Tab 2 热力图正常显示（全零色块），`logger.warning` 提示检查数据 |
| 5 | 星期/月份标签缺失（数据跨度过短） | Tab 2 error-by-month 直接跳过不渲染，error-by-weekday 按数据实际覆盖的天数显示 |
| 6 | 价格出现极端离群值（如 >5000 元/MWh） | 叠加图和热力图仍显示全部数据，不裁剪 — 保留异常值以便观察 |
| 7 | 无可用外部基准数据 | Tab 3 MAE 条状图仅显示 LEAR vs 持续法 2 条，不报错 |
| 8 | plotly 渲染失败（notebook 环境问题） | `try/except` 包裹 `fig.show()`，捕获后 `print(fig.to_html())` 回退 |

## 非目标

- ❌ 不依赖 dash/streamlit（纯 notebook plotly）
- ❌ 不修改 Phase 1 代码或数据
- ❌ 不训练任何模型（仅加载已训练的 LEAR 结果）
- ❌ 不做实时更新（静态展示历史预测结果）
- ❌ 不生成 PDF/HTML 报告（仅 notebook 内渲染）
- ❌ 不执行新的 DM/GW 检验（依赖 task-05 的结果）

## 参考

- Phase 1 `04_load_forecasting.ipynb`：plotly 可视化风格（`make_subplots` + `go.Scatter` + `go.Histogram`）、markdown 教学说明格式、思考题风格
- Phase 2 `design.md § Wave 2 详细设计 > 仪表板设计`：3 Tab 布局、每个 Tab 的内容说明
- Phase 2 `plan.md § Wave 2` 验收标准第 5 条："07 notebook 3 个 Tab 渲染正常，hover 交互可用"
- Phase 2 `tasks/task-05.md`：DM/GW 检验的输出格式和数据来源
- plotly 官方文档：`go.Heatmap`、`go.Table`、`make_subplots` 的 `specs` 参数
- 设计文档对照表：

| Tab | 设计文档要求 | 实现方式 |
|-----|-------------|---------|
| Tab 1 | LEAR vs 实际 overlay + 误差分布 | `make_subplots(rows=2)` 叠加 + 直方图 |
| Tab 2 | error-by-hour heatmap + weekday + month | `go.Heatmap(24h×7d)` + `go.Bar` ×2 |
| Tab 3 | MAE bar + DM/GW tables | `go.Bar(results)` + `go.Table` ×2 |

## TDD 步骤

```
 1. [CODE] Cell 1-2: notebook 标题 + 导入 + renderer 配置
 2. [VERIFY] `pio.renderers.default` 被设置为 'notebook'，plotly 可导入
 3. [CODE] Cell 3: 加载 LEAR 预测 + 持续法 + DM/GW 数据
 4. [VERIFY] 打印数据概览：行数、日期范围、MAE 值
 5. [CODE] Cell 4-5: Tab 1 — 叠加图 + 误差分布
 6. [VERIFY] fig.show() 输出含 2 个子图（叠加 + 直方图），hover 可用
 7. [CODE] Cell 7-8: Tab 2 — 热力图 + weekday + month bar
 8. [VERIFY] heatmap 为 24h×7d 矩阵，bar chart x 轴标签正确
 9. [CODE] Cell 10-11: Tab 3 — MAE bar + DM/GW tables
10. [VERIFY] bar chart 显示至少 2 个模型，table 含 DM/GW 数据（或缺失提示）
11. [SAVE] 全部 cell 顺序执行 `Restart & Run All` 无报错
12. [FINAL] 人工确认：每个 Tab 切换流畅、hover 交互正常、中文标签完整
```

## 验收标准

**Tab 1 预测总览**：

```
┌─────────────────────────────────────────────────────────┐
│  📊 日前电价预测 — 实际 vs LEAR                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  实际 ──────  LEAR - - - - - - -               │   │
│  │  ───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬────   │   │
│  │     │   │   │   │   │   │   │   │   │   │        │   │
│  │     │   │   │   │   │   │   │   │   │   │        │   │
│  │     └───┴───┴───┴───┴───┴───┴───┴───┴───┴────   │   │
│  │  06/01   06/02   06/03   06/04   06/05   06/06    │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  频次│  ████                                    │   │
│  │       │  ████████                               │   │
│  │       │  ████████████  ← 误差中位数线            │   │
│  │       │  ████████████████                       │   │
│  │       └─────────────────                        │   │
│  │          误差 (元/MWh)                          │   │
│  └─────────────────────────────────────────────────┘   │
│  MAE: X,XXX 元/MWh │ RMSE: X,XXX 元/MWh               │
└─────────────────────────────────────────────────────────┘
```

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | 叠加图显示最近 7 天 | 目测 x 轴日期跨度约 7 天 |
| 2 | 预测为虚线，实际为实线 | 目测确认线型区别 |
| 3 | 直方图含 30 个 bins | `len(fig.data[1].xbins)` ≈ 30 |
| 4 | 直方图有误差中位数竖线 | `fig.layout.shapes` 含竖线定义 |
| 5 | hover 显示数值 | 鼠标悬停显示 tooltip |

**Tab 2 误差分析**：

```
┌─────────────────────────────────────────────────────────┐
│  📊 误差分析                                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │  日│  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●          │   │
│  │  期│  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●          │   │
│  │     │  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●  热力图  │   │
│  │     │  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●  (RdBu) │   │
│  │     └─────────────────────────────────           │   │
│  │      0 3 6 9 12 15 18 21  小时                    │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  MAE│  ██  ██  ████  ██████  ██  ██             │   │
│  │     └───────────────────────                    │   │
│  │      一  二  三  四  五  六  日                    │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  MAE│  ██  ██  ██  ██  ██  ██                   │   │
│  │     └───────────────────────                    │   │
│  │      1   2   3   4   5   6  ...  月               │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | 热力图为 24 列 × 7 行 | `z_matrix.shape == (7, 24)` |
| 2 | 热力图的 colorscale 为 RdBu_r | `heatmap.colorscale` 配置正确 |
| 3 | error-by-weekday 的 x 轴为 7 个标签 | `len(fig.data[x].x) == 7` |
| 4 | error-by-month 的 x 轴为 1-12（或数据跨度） | 标签正确显示中文月份 |
| 5 | 三个子图在一个 figure 中 | `make_subplots(rows=3, cols=1)` |

**Tab 3 模型对比**：

```
┌─────────────────────────────────────────────────────────┐
│  📊 模型对比                                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │  MAE│  ████████████████████                     │   │
│  │  (元)│  ████████████████                        │   │
│  │      │  ████████████                            │   │
│  │      └──────────────────                        │   │
│  │       LEAR   持续法   基准(如果有)               │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  ┌──────────────────────────────────────┐       │   │
│  │  │  DM 检验结果                          │       │   │
│  │  │  数据集    │  DM     │ p-value │ 显著? │       │   │
│  │  │  EPEX-BE   │  1.23   │  0.218  │  No   │       │   │
│  │  │  ...       │  ...    │  ...    │  ...  │       │   │
│  │  └──────────────────────────────────────┘       │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  ┌──────────────────────────────────────┐       │   │
│  │  │  GW 检验结果                          │       │   │
│  │  │  ...                                 │       │   │
│  │  └──────────────────────────────────────┘       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | MAE 条状图至少含 2 个模型 | `len(fig.data[x].x) >= 2` |
| 2 | 各模型条状图颜色不同 | 目测颜色区分 |
| 3 | DM 检验表渲染为 `go.Table` | 含统计量、p-value、显著性列 |
| 4 | GW 检验表渲染为 `go.Table` | 含统计量、p-value、显著性列 |
| 5 | 数据缺失时显示友好提示 | 注入 None 验证提示文本 |

**整体仪表板**：

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | 全部 cell `Restart & Run All` 无报错 | 顺序执行不抛异常 |
| 2 | 所有标签为中文 | 目测扫描 |
| 3 | hover 交互在所有图表上可用 | 鼠标悬停各图表验证 |
| 4 | notebook 含 思考题 section（每个 Tab 后 + 综合） | 不少于 4 道思考题 |
| 5 | 首个 cell 为 Markdown 标题 + 学习目标 | 目测验证 |
