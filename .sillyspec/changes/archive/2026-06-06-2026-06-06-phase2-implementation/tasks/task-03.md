---
id: task-03
title: 创建 06_price_forecasting.ipynb — 端到端 LEAR 电价预测 notebook
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P0
estimated_hours: 3
depends_on: [task-01, task-02]
blocks: [task-04]
allowed_paths:
  - ellectric/notebooks/06_price_forecasting.ipynb
---

# Task-03: 创建 06_price_forecasting.ipynb — 端到端 LEAR 电价预测 notebook

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `ellectric/notebooks/06_price_forecasting.ipynb` | 新建 | 端到端 LEAR 电价预测教学 notebook |

## 实现要求

遵循 Phase 1 notebook 风格（与 `04_load_forecasting.ipynb` 一致）：

1. **Section 1 — 说明 + 导入**: Markdown 标题/学习目标/LEAR 原理说明，导入 `PriceDataLoader`、`LEARForecaster` 等模块
2. **Section 2 — 加载中国电价数据**: 调用 `PriceDataLoader().load_data()`，验证 `price_da` 目标列存在，输出基本统计摘要
3. **Section 3 — 特征工程 (Tier 1→2→3 progressive)**: 三步渐进展开，每步输出新增特征列表和形状，说明特征含义
4. **Section 4 — LEAR 模型训练与评估**: `LEARForecaster().train_evaluate()` + 对比持续法（以 `price_da[t-24]` 为持续预测），输出 MAE/RMSE/MAPE/R²
5. **Section 5 — 预测结果可视化**: plotly subplots — 实际 vs 预测叠加图 + 误差分布直方图
6. **Section 6 — 思考题**: 3 道反思题

## 接口定义

Notebook 消费的模块接口（由 task-01/task-02 提供）：

```python
# task-01: price_loader.py
from ellectric.pipeline.price_loader import PriceDataLoader
loader = PriceDataLoader()
df = loader.load_data()
# → DataFrame with columns: timestamp, price_da, price_rt, load_mw, wind_mw, solar_mw, tie_line_mw

# task-02: price_forecaster.py
from ellectric.pipeline.price_forecaster import LEARForecaster
model = LEARForecaster(alpha=0.01)
result = model.train_evaluate(df, target_col='price_da', n_splits=5, gap=24)
# → {'model': Lasso, 'metrics': {'mae': float, 'rmse': float, 'mape': float, 'r2': float},
#     'predictions': array, 'actuals': array, 'feature_importance': dict}

# 持续法对比
persist_mae = (df['price_da'].shift(24) - df['price_da']).abs().mean()
```

## 边界处理

1. **数据不足**: 如果 `len(df) < 168`（不足 7 天），raise `ValueError("电价数据不足 168 行，无法生成滞后 168h 特征")`
2. **缺失目标列**: 如果 `target_col` 不在 DataFrame 列中，在 notebook 中 `assert target_col in df.columns, f"目标列 {target_col} 不存在于数据中"` — 显示可用列列表帮助诊断
3. **时间连续性**: 加载后检查时间戳是否均匀间隔（期望 1h 间隔），如有 gap > 2h 打印警告 `"⚠ 数据存在 {gap_count} 处时间不连续"`（不阻断执行）
4. **负价格**: 中国电力现货可能出清负价格，`price_da` 含负值时不应报错，在统计摘要中标注 `"price_da: 含 {n_neg} 个负值，范围 [{min:.0f}, {max:.0f}]"`（正常现象，教学重点）
5. **持续法对标失效**: 如果 `shift(24)` 产生 NaN（如前 24 行无可参考的昨日值），计算时 `skipna=True`，输出 `"持续法基于 {valid_count}/{total_count} 个有效样本"` 防止无声失效
6. **TimeSeriesSplit gap 不足**: 如果 `n_splits * gap > len(train) * 0.3`，打印警告 `"⚠ 训练集 {n_splits} 折 × gap {gap} 可能占用过多训练数据"`（不阻断）

## 非目标

- 不涉及 epftoolbox 对比（归 task-05/task-06）
- 不涉及 ASSUME 仿真连接（归 Wave 3）
- 不修改 `04_load_forecasting.ipynb` 或任何 Phase 1 代码
- 不添加自定义 CSS 或 notebook 扩展
- 不包含模型持久化（超出 notebook 教学范围）
- 不涉及 GPU/加速器，全 CPU 执行

## 参考

- Phase 1 风格: `04_load_forecasting.ipynb` — 六段式结构 (说明→数据→特征→训练→可视化→思考题)
- LEAR 特征设计: design.md 第 60-66 行 (Tier 1/2/3 特征分类)
- LEAR 模型参数: `Lasso(alpha=0.01, max_iter=10000, random_state=42)` — design.md 第 72 行
- 数据列: `timestamp, price_da, price_rt, load_mw, wind_mw, solar_mw, tie_line_mw` — design.md 第 84 行
- 评估指标: MAE 统一 — design.md 第 75 行
- 架构决策: sklearn Lasso（非 epftoolbox 的 TF/DNN）— design.md 第 187 行

## TDD 步骤

```
1. [验证 task-01/task-02 就绪] → python -c "from ellectric.pipeline.price_loader import PriceDataLoader; from ellectric.pipeline.price_forecaster import LEARForecaster" 不报错
2. [创建 notebook 骨架] → 写入 6 个 Section 的 markdown cells + 空白 code cells
3. [实现 Section 1-2] → 导入 + 数据加载 cell, 运行验证 DataFrame 含 7 列且 price_da 无全 NaN
4. [实现 Section 3] → Tier 1→2→3 渐进特征工程 cells, 运行检查特征列数递增
5. [实现 Section 4] → train_evaluate + 持续法对比 cell, 运行检查 metrics 字典包含'mae'
6. [实现 Section 5] → plotly 可视化 cell, 运行检查 fig 对象正常生成
7. [实现 Section 6] → 思考题 markdown
8. [验证全 notebook] → jupyter nbconvert --to script --stdout 06_price_forecasting.ipynb | python 全部 cell 顺序执行无报错
```

## 验收标准

### 功能验收

| # | 验收条件 | 验证方法 |
|---|---------|---------|
| 1 | notebook 包含 6 个 Section，结构清晰 | 肉眼检查 markdown 标题 |
| 2 | Section 2 加载后输出 DataFrame 统计摘要 (行数/列数/缺失值/null 值) | 运行 cell 检查输出 |
| 3 | Section 3 三级特征逐步展开，每级打印新增特征名和维度 | 运行 cell 检查输出 |
| 4 | Section 4 输出 MAE/RMSE/MAPE/R² 四项指标，含持续法对比 | 运行 cell 检查数值输出 |
| 5 | Section 4 Lasso 系数 `alpha=0.01`, `max_iter=10000`, `random_state=42` | 检查 cell 参数匹配 design.md |
| 6 | Section 5 渲染 2 个子图：叠加图 + 直方图 | 运行 cell 检查 fig object 类型 |
| 7 | 所有 code cell 顺序执行无报错 | nbconvert + python 执行 |

### 边界处理验收

| # | 条件 | 预期行为 | 验证方法 |
|---|------|---------|---------|
| 1 | 数据 < 168 行 | 抛 ValueError | 注入 100 行 DataFrame 测试 |
| 2 | 目标列缺失 | assert 提示可用列名 | 传入错误列名测试 |
| 3 | 时间间断 > 2h | 打印警告，不阻断 | mock 数据含 3h gap 测试 |
| 4 | price_da 含负值 | 统计标注负值数量 | 注入含 -50 的数据测试 |
| 5 | 前 24 行 NaN (shift) | skipna=True + 有效样本计数 | 检查第 1 行持续法逻辑 |
| 6 | n_splits×gap 过大 | 打印训练数据比例警告 | 小数据集 + gap=24 测试 |

### 风格验收

| # | 条件 | 标准 |
|---|------|------|
| 1 | Markdown 教学风格 | 含类比/图表/公式 |
| 2 | 代码注释风格 | `# ── 标题 ──` 格式（Phase 1 风格） |
| 3 | 可视化风格 | plotly, 同 Phase 1 配色方案 |
| 4 | 思考题 | 3 道，覆盖特征/模型/评估维度，有启发性 |

---

*Task blueprint 创建日期: 2026-06-06*
*关联模块: price_loader.py (task-01), price_forecaster.py (task-02)*
