---
author: lmr
created_at: 2026-06-06T00:00:00+08:00
---

# ARCHITECTURE: Ellectric Pipeline

## 技术栈

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Runtime | Python | 3.11+ | 核心执行环境 |
| Data I/O | pandas + pyarrow | 3.0.3 / 22.0.0 | DataFrame 操作，Arrow 后端，Parquet/CSV/Excel 读写 |
| Data Fetch | urllib + csv (stdlib) | — | OWID GitHub raw CSV 拉取 |
| Math | numpy | >=2.0.0 | 数值计算，数组操作 |
| ML | scikit-learn + xgboost | 1.8.0 / 3.2.0 | TimeSeriesSplit 分割，StandardScaler，XGBoost 回归器 |
| Viz | plotly | 6.7.0 | 交互式图表（负荷叠加、误差直方图、P&L 曲线） |
| Notebooks | jupyter + nbformat | 1.1.1 / >=5.0.0 | 5 个渐进式学习 notebook |
| Data Storage | Parquet | — | 清洗后数据持久化 (`data/*.parquet`) |
| Container | Docker Compose | — | Phase 2 TimescaleDB + Grafana（已预留） |

## 架构概览

### Pipeline 拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                       Jupyter Notebooks                       │
│  01_data_ingestion → 02_cleaning → 03_features →              │
│  04_forecasting → 05_end_to_end_baseline                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  ellectric.pipeline (5 modules)               │
│                                                               │
│  ┌──────────────┐    ┌──────────┐    ┌───────────────┐       │
│  │ data_loader  │───▶│ cleaner  │───▶│   features    │       │
│  │   (390 loc)  │    │ (178 loc)│    │   (224 loc)   │       │
│  └──────────────┘    └──────────┘    └───────┬───────┘       │
│                                              │               │
│                                              ▼               │
│                                    ┌──────────────────┐      │
│                                    │    forecaster    │      │
│                                    │    (431 loc)     │      │
│                                    └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 模块职责

#### 1. `data_loader.py` — 数据接入层

**抽象基类 + 工厂模式：**

```
DataLoader (ABC)
  │  load_data(start, end) → pd.DataFrame[timestamp, load_mw]
  │
  ├── OWIDChinaLoader      — 自动拉取 Our World in Data GitHub raw CSV
  │    · 年级数据 (TWh) → 日均 MW 换算 (_twh_to_daily_mw)
  │    · 无外部依赖，直接 HTTP GET
  │
  └── ChineseDataLoader    — 加载手动下载的本地 CSV/Excel/Parquet
       · 自动检测格式 (suffix: .csv / .xlsx / .parquet)
       · 列名标准化 (_standardize_columns): 中英文 → timestamp/load_mw
       · 支持 start/end 时间过滤
       · 时区: 强制 UTC
```

**工厂函数:** `create_loader(source="owid" | "manual" | "file", **kwargs) → DataLoader`

**数据合约 (Data Contract):**
- `timestamp`: datetime64[ns, UTC]
- `load_mw`: float64, 单位 MW

#### 2. `cleaner.py` — 数据清洗层

**纯函数管道：**

```
clean_data(df) → df
  ├── 列验证: 检查 REQUIRED_COLUMNS = {timestamp, load_mw}
  ├── 缺失值: ffill + bfill (保留时序连续性)
  ├── IQR 异常值检测: 报告不删除 ("spikes are signal")
  └── 时区标准化: 无时区 → UTC，非 UTC → 转 UTC

validate_schema(df) → dict
  ├── 列存在性检查
  ├── 类型检查 (datetime, numeric)
  ├── 时区检查
  └── 返回: {valid, issues, stats}
```

设计原则：异常值仅报告不删除 — 电力负荷尖峰是有效信号（极端天气、事件等），不应自动剔除。

#### 3. `features.py` — 特征工程层

**FeatureEngineer 类 — 渐进式 3 级特征：**

| Tier | 特征 | 含义 |
|------|------|------|
| Tier 1 | hour, day_of_week, month, is_weekend, lag_24h | 基础时间 + 日内滞后 |
| Tier 2 | is_holiday, lag_168h | 节假日标志 + 周滞后 |
| Tier 3 | rolling_mean_24h, rolling_std_24h, hour_sin, hour_cos | 滚动统计 + 循环编码 |

- `get_feature_columns(tier)` 返回该级别特征列名列表 — 模型训练时只用特征列，排除 timestamp/load_mw
- 循环编码 (hour_sin/cos): 将 0-23 小时映射到单位圆，保持 "23 和 0 相邻" 的拓扑关系

**便捷函数:** `prepare_features(df, tier="tier3")` — 一键执行全部 3 级特征

#### 4. `forecaster.py` — 预测与评估层

**两类预测器：**

```
模块级函数:
  persistence_forecast(df) → pd.Series     # t-24h 朴素基线
  calculate_pnl(df, forecast) → pd.Series  # P&L 计算
  plot_pnl(df, forecast) → go.Figure       # 累积利润曲线

XGBoostForecaster 类:
  __init__(n_splits=5, gap=24, **xgb_kwargs)
    └── TimeSeriesSplit(n_splits, test_size=168, gap=24)
  train_evaluate(X, y) → dict
    ├── 特征缩放: StandardScaler.fit(train) → transform(test)
    ├── 交叉验证: 5-fold 时序分割
    └── 指标: MAE, RMSE, MAPE
  predict(X) → np.ndarray
    └── 需先调用 train_evaluate()
```

**防泄漏保证:**
- TimeSeriesSplit 带 `gap=24` — 训练/测试间隔 24h，杜绝时序泄露
- StandardScaler 仅在训练集 fit，严格避免 look-ahead bias

### 数据流向

```
OWID GitHub (raw CSV)             本地文件 (CSV/Excel/Parquet)
        │                                    │
        ▼                                    ▼
  OWIDChinaLoader                   ChineseDataLoader
        │                                    │
        └────────────┬───────────────────────┘
                     ▼
            pd.DataFrame[timestamp, load_mw]
                     │
                     ▼
              clean_data(df)
              · 缺失值 ffill/bfill
              · IQR 异常值报告
              · UTC 时区标准化
                     │
                     ▼
           FeatureEngineer.add_tier1/2/3(df)
              · Tier 1: 基础时间特征
              · Tier 2: 节假日 + 周滞后
              · Tier 3: 滚动统计 + 循环编码
                     │
                     ▼
            XGBoostForecaster.train_evaluate(X, y)
              · TimeSeriesSplit (gap=24)
              · StandardScaler (fit on train only)
                     │
                     ▼
              {MAE, RMSE, MAPE} + 预测结果 + Plotly 图表
```

### 文件布局

```
ellectric/
├── pipeline/                      # Python 包 (5 modules, 1225 loc)
│   ├── __init__.py                # 1 loc
│   ├── data_loader.py             # 390 loc — DataLoader ABC, OWID/Chinese loaders
│   ├── cleaner.py                 # 178 loc — clean_data, validate_schema
│   ├── features.py                # 224 loc — FeatureEngineer, prepare_features
│   └── forecaster.py              # 431 loc — persistence, P&L, XGBoostForecaster
├── notebooks/                     # 5 个渐进式 Jupyter notebook
│   ├── 01_data_ingestion.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_load_forecasting.ipynb
│   └── 05_end_to_end_baseline.ipynb
├── data/                          # 数据目录
│   ├── .gitkeep
│   └── electricity_load_hourly.parquet
├── requirements.txt               # 依赖声明
├── setup.sh                       # 一键安装脚本
├── docker-compose.yml             # Phase 2 预留 (TimescaleDB + Grafana)
└── README.md
```

### 设计原则

1. **时序安全性:** 所有操作禁止未来信息泄露 — TimeSeriesSplit(gap=24), Scaler 仅在训练集 fit
2. **异常值保留:** IQR 检测但仅报告 — 电力尖峰是有效信号，不自动剔除
3. **渐进式学习:** 特征分 3 个 Tier，notebook 按 pipeline 顺序逐步推进
4. **工厂模式:** `create_loader()` 统一数据源接入，未来扩展新 loader 只需新增子类
5. **命名单一标准化:** 中英文列名统一映射到 `timestamp` / `load_mw`，所有模块依赖同一份数据合约
