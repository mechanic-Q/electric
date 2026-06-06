# Phase 2 设计 — 中国电力市场预测与仿真

author: lmr
created_at: 2026-06-06T19:00:00+08:00

## 背景

Phase 1 已建立中国电力负荷预测管道（OWID 年数据 + XGBoost 日负荷预测）。
Phase 2 在此基础上前进两步：

1. **电价预测**：使用中国省级现货电价数据训练 LEAR 模型（sklearn Lasso）
2. **市场仿真**：配置 ASSUME 运行中国省间现货市场仿真

Phase 2 不依赖 Phase 1 代码，但复用其设计模式（DataLoader 抽象、模块化管道、
plotly 可视化、Jupyter notebook 教学风格）。

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Phase 2 管道                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Wave 1       │    │  Wave 2       │    │  Wave 3       │      │
│  │  数据+预测     │ →  │  对比+仪表板   │ →  │  ASSUME仿真   │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │price_loader  │    │epftoolbox    │    │ASSUME        │      │
│  │price_predict │    │DM/GW 检验    │    │中国省间YAML  │      │
│  │LEAR notebook │    │plotly仪表板  │    │Grafana       │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Wave 1 详细设计：数据接入 + LEAR 电价预测

### 新增模块：price_loader.py

```
price_loader.py
  ├── PriceDataLoader          — 加载 ZionLuo xlsx 电价数据
  │     load_data() → DataFrame (timestamp, price, load, wind, solar, tie_line)
  │     get_metadata() → dict
  └── create_price_loader()    — 工厂函数
```

### 新增模块：price_forecaster.py

```
price_forecaster.py
  └── LEARForecaster           — sklearn Lasso 实现的 LEAR 电价预测
        ├── add_price_features()     — 日历特征 + 滞后特征 + 滚动统计
        ├── train_evaluate()         — TimeSeriesSplit + LEAR 训练
        └── plot_price_forecast()    — 预测 vs 实际叠加图 + 误差分布
```

### LEAR 模型设计

LEAR = Lasso + 滞后特征 + 日历特征 + 滚动统计

```
特征工程:
  Tier 1 (核心): hour, day_of_week, month, is_weekend
                  lag_24h_price, lag_168h_price
  Tier 2 (中级): lag_24h_load, lag_24h_wind, lag_24h_solar
                  rolling_mean_24h_price, rolling_std_24h_price
  Tier 3 (高级): hour_sin, hour_cos, price_trend_7d

模型: sklearn.linear_model.Lasso(alpha=0.01, max_iter=10000, random_state=42)

评估: TimeSeriesSplit(n_splits=5, gap=24)
      指标: MAE (与 Phase 1 统一)
```

### 数据流

```
ZionLuo xlsx
    │  price_loader.load_data()
    ▼
DataFrame [timestamp, price_da, price_rt, load_mw, wind_mw, solar_mw, tie_line_mw]
    │  price_forecaster.add_price_features()
    ▼
DataFrame + 特征列
    │  LEARForecaster.train_evaluate()  (内部 TimeSeriesSplit + scaler)
    ▼
训练结果: predictions, actuals, metrics (MAE), model, feature_importance
    │  plot_price_forecast()
    ▼
可视化: overlay + error histogram
```

## Wave 2 详细设计：epftoolbox 基准对比 + 仪表板

### epftoolbox 用法

epftoolbox 在本项目中**不作为预测框架使用**，仅用于：
1. **基准数据集** — 5 个标准数据集（EPEX-BE/FR/DE, NordPool, PJM）
2. **统计检验** — Diebold-Mariano 检验 + Giacomini-White 检验

```
epftoolbox 安装策略:
  - 独立虚拟环境 (venv_epftoolbox)
  - 安装命令: pip install tensorflow && pip install git+https://github.com/jeslago/epftoolbox.git
  - 只使用 datasets 模块和 benchmark.evaluation 模块
  - 不训练 epftoolbox 模型
```

### 仪表板设计

```
plotly 交互式仪表板（Phase2_Dashboard.ipynb）:
  ├── Tab 1: 预测总览
  │     ├── LEAR vs 实际 (叠加图, 过去7天)
  │     └── 误差分布直方图
  ├── Tab 2: 误差分析
  │     ├── 误差按小时热力图 (24h × 7d)
  │     ├── 误差按星期热力图
  │     └── 误差按月份热力图
  └── Tab 3: 模型对比
        ├── LEAR vs 持续法 vs 基准 (MAE 条状图)
        ├── DM 检验结果表
        └── GW 检验结果表
```

## Wave 3 详细设计：ASSUME 中国省间现货仿真

### 中国省间现货规则配置

```
ASSUME YAML 配置 (assume_china_config.yaml):
  market:
    type: "zonal"                    # 省间为分区定价
    clearing_mechanism: "pay_as_clear"
    price_limits:
      min: 0                         # 中国省间报价下限 0 元/MWh
      max: 1500                      # 中国省间报价上限 1500 元/MWh
    deviation_penalty: 0.1           # 偏差考核系数

  generation_mix:
    coal:
      capacity_mw: 50000
      marginal_cost: 300             # 元/MWh
    wind:
      capacity_mw: 20000
      marginal_cost: 50
    solar:
      capacity_mw: 15000
      marginal_cost: 30
    gas:
      capacity_mw: 10000
      marginal_cost: 600
    storage:
      capacity_mw: 5000
      marginal_cost: 100

  demand:
    profile: "china_summer_peak"
    total_demand_mw: 80000

  agents:
    - type: "learning"               # RL 智能体
      algorithm: "PPO"
    - type: "naive"                  # 边际成本报价
    - type: "strategic"              # 策略性报价
```

### Grafana 仪表板

```
数据源: TimescaleDB (通过 ASSUME Docker Compose)
面板:
  ├── 出清价格时序 (元/MWh, 逐小时)
  ├── 各机组调度量 (MW, 堆叠面积图)
  ├── 省间联络线功率 (MW)
  ├── 各智能体累计利润 (元)
  └── 新能源消纳率 (%)
```

## 架构决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 预测框架 | sklearn Lasso | epftoolbox 依赖 TF/Keras 冲突，Lasso 足够验证 LEAR 方法 |
| 数据加载 | 独立 price_loader.py | 电价数据格式与负荷数据差异大（多列、多 sheet），不适合复用 DataLoader |
| 数据存储 | data/ 目录 xlsx 原文件 | 数据量小（~2000行），不需要数据库 |
| 可视化 | plotly + Grafana | plotly 用于 notebook 交互，Grafana 用于仿真仪表板 |
| epftoolbox | 独立 venv | TF/Keras 与 PyTorch 冲突，仅在对比阶段需要 |
| ASSUME 仿真 | 中国省间 YAML 配置 | 替换默认德国 EPEX 配置，适配中国规则 |

## 不变的内容

- Phase 1 所有文件不变
- requirements.txt 不变（epftoolbox 和 ASSUME 各自独立 venv）
- DataLoader 抽象基类不变（price_loader 独立实现）
- plotly 可视化风格不变
- Jupyter notebook 教学风格不变
