---
author: lmr
created_at: 2026-06-06 19:00:00
---

# Requirements

## 角色

| 角色 | 说明 |
|------|------|
| 开发者 | Phase 2 学习者，已掌握 Phase 1 XGBoost 负荷预测 |
| 系统 | Ellectric 平台，Phase 2 新增电价预测和仿真能力 |
| 数据源 | ZionLuo 中国现货电价 xlsx |

## 功能需求

### FR-01: 中国电价数据加载

Given ZionLuo price data.xlsx 已下载到 `data/` 目录
When 运行 `price_loader.load_data()`
Then 返回 DataFrame，包含 timestamp, price_da, price_rt, load_mw, wind_mw, solar_mw, tie_line_mw 列
And 列名标准化，时区统一为 UTC，时间索引排序
And get_metadata() 返回数据源、行数、时间范围、频率信息

### FR-02: LEAR 电价预测

Given 中国电价数据已加载
When 使用 LEARForecaster 训练 sklearn Lasso 模型
Then 模型使用 TimeSeriesSplit(n_splits=5, gap=24) 评估
And scaler 仅在训练集上 fit（无 look-ahead bias）
And 输出 MAE 指标和 feature_importance

### FR-03: 预测可视化

Given LEAR 模型训练完成
When 调用 plot_price_forecast()
Then 显示预测 vs 实际叠加图 + 误差分布直方图
And 图表与 Phase 1 风格一致（plotly 交互式）

### FR-04: 预测 Notebook

Given 价格数据已加载
When 开发者运行 `06_price_forecasting.ipynb`
Then notebook 按：说明 → 加载数据 → 特征工程 → 训练 → 评估 → 思考题 顺序执行
And 所有 cell 从上到下顺序执行无报错

### FR-05: epftoolbox 基准对比

Given 独立 venv_epftoolbox 环境
When 运行 epftoolbox 的 5 个基准数据集（EPEX-BE/FR/DE, NordPool, PJM）
Then 输出各数据集的统计数据（均值、标准差、缺失率）
And 对比中国 LEAR 与各基准的 DM/GW 检验结果

### FR-06: 模型对比仪表板

Given LEAR 训练结果和 epftoolbox 基准数据
When 打开 `07_model_comparison_dashboard.ipynb`
Then 仪表板包含 3 个 Tab：
- 预测总览（LEAR overlay + 误差分布）
- 误差分析（按小时/星期/月份热力图）
- 模型对比（MAE 排名 + DM/GW 结果表）

### FR-07: ASSUME 仿真安装

Given 开发者使用 Python 3.11
When 运行 `pip install assume-framework`
Then ASSUME 成功安装并可导入
And 仿真可启动至少一次 7 天默认配置运行

### FR-08: 中国省间现货配置

Given ASSUME 已安装
When 加载 `assume_china_config.yaml`
Then 市场配置包含：报价上下限 (0-1500 元/MWh)、偏差考核、新能源优先调度
And 发电组合包含：煤/风/光/气/储能
And 启动仿真后 Grafana 显示出清价格

### FR-09: 发电组合修改

Given 中国省间仿真配置已运行
When 修改 YAML 中 wind.capacity_mw 从 20000 改为 30000
And coal.capacity_mw 从 50000 改为 40000
Then 再次运行仿真后出清价格降低、煤电调度减少、风电调度增加

## 非功能需求

| 属性 | 要求 |
|------|------|
| 兼容性 | Phase 1 代码无需任何修改，pip install 兼容 |
| 性能 | LEAR 训练 < 30 秒（2000 行数据） |
| 可维护性 | 模块文档字符串说明设计决策 |
| 可复现性 | random_state=42，TimeSeriesSplit 固定分割 |
| 教学性 | Notebook 含思考题和设计决策解释 |
