---
schema_version: 1
doc_type: module-card
module_id: notebooks
---
# notebooks
## 定位
学习入口 — 5 个交互式 Jupyter Notebook，按数据管道顺序由上到下渐进编排：数据获取 → 清洗 → 特征工程 → 预测 → 端到端验证。每个 notebook 包含 Markdown 讲解 + 代码 Cell + 内联可视化 + 思考题，可独立运行（产出 parquet 接力）。
## 契约摘要
- `01_data_ingestion` — OWID 中国电力数据自动拉取，展示 DataLoader 统一接口用法，初识 data cleaning 管道
- `02_data_cleaning` — 深入清洗：缺失值填充策略选择、IQR 异常值检测、UTC 时区标准化、输出 `cleaned_load.parquet`
- `03_feature_engineering` — Tier 1/2/3 渐进式特征构建（日历特征、lag-24h/lag-168h、滚动统计），Fit-on-train-only 缩放器使用演示
- `04_load_forecasting` — XGBoost 训练 + TimeSeriesSplit(n_splits=5, gap=24) 交叉验证，实际 vs 预测叠加图 + 误差分布直方图
- `05_end_to_end_baseline` — 持续法预测 → 简易模拟出清 → 累计 P&L 图表，证明五层管道可端到端跑通
## 关键逻辑
```
01 数据获取 ──parquet──▶ 02 清洗 ──parquet──▶ 03 特征工程 ──parquet──▶ 04 预测 ──model──▶ 05 验证
```
每个 notebook 读取上一阶段产出的 parquet 文件，独立运行但顺序依赖数据接力。Notebook 05 是 walking-skeleton 验证节点：用简单逻辑跑通整条管道以发现集成问题。
## 注意事项
- 所有 notebook 共享同一个虚拟环境，依赖由 `ellectric/` 下的模块提供（data-loader, cleaner, feature-engineer, forecaster）
- 数据 parquet 产出路径硬编码在 notebook cell 内，若目录结构变更需同步更新
- 不含单元测试；验证方式为逐 cell 执行通过 + 图表肉眼检查
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
