# Phase 1: Data Foundation + Basic Prediction - Discussion Log

**Gathered:** 2026-05-20
**Mode:** interactive

## Areas Discussed

### Data Source Selection
Q: "你想用哪里的电力数据来学习？" → Selected: 中国电力数据（地方开放数据平台，小时级负荷）
- 用户明确表示想学中国电力市场的技术，优先使用中国数据而非美国PJM

### Environment Setup
Q: "环境搭建方式？" → Selected: pip + venv (Recommended)
- 最简单直接，30分钟内跑起来

### Notebook Structure
Q: "Notebook 结构怎么组织？" → Selected: 模块化（.py + notebook）
- 核心逻辑放.py模块，notebook只做探索和可视化

### End-to-End Baseline
Q: "端到端基线用什么方式？" → Selected: 持续法预测 + 简单P&L (Recommended)
- 先用最简单的方式证明管道连通

### Model Evaluation
Q: "模型评估用哪些指标？" → Selected: MAE
- 保持简单，只看平均绝对误差

### Feature Engineering
Q: "特征工程怎么组织？" → Selected: 渐进式（先少后多）(Recommended)
- 先3-5个基础特征跑通，再逐步添加

### Visualization
Q: "可视化用什么库？" → Selected: plotly
- 交互式图表，可以缩放/悬停查看数据点

## Key Changes from Previous Auto-Run

| Decision | Auto (之前的) | User (这次的) |
|----------|--------------|--------------|
| 数据源 | 美国PJM (PUDL) | 中国地方开放数据平台，小时级负荷 |
| 评估指标 | MAE + RMSE + MAPE + R² | 仅 MAE |
| 可视化 | matplotlib | plotly |

## Deferred Ideas
- 美国PJM作为备用数据源（降级方案）
- 天气数据集成（Phase 2）

---
*Discussion completed: 2026-05-20 (interactive mode)*
