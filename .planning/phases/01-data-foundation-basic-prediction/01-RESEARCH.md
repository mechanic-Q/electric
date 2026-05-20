# Phase 1 Research: Data Foundation + Basic Prediction

**Phase:** 01 - Data Foundation + Basic Prediction
**Researched:** 2026-05-20
**Confidence:** MEDIUM (data source uncertainty)

## Research Scope

Per CONTEXT.md decisions: Chinese local open data platforms for hourly load data → XGBoost forecasting → plotly visualization → MAE evaluation → pip+venv environment.

---

## 1. Data Source Feasibility: Chinese Electricity Open Data

### Investigation Results

| Platform | URL | Access Result | Data Available |
|----------|-----|---------------|----------------|
| 国家统计局 | data.stats.gov.cn | 403 (blocked) | Monthly/yearly macro stats only |
| 深圳开放数据平台 | opendata.sz.gov.cn | 200, empty response | Requires login/register |
| 上海开放数据 | data.sh.gov.cn | 412 (precondition failed) | Requires CAPTCHA/interaction |
| 广东开放数据 | data.gd.gov.cn | TLS error | HTTPS handshake failure |
| and各种数据集platform | 和鲸/天池/地方平台 | 需浏览器手动操作 | 存在电力负荷数据集 |

### Key Finding: Chinese government open data portals require manual browser access

经 7 轮测试（scrapling/httpcloak/camoufox/DuckDuckGo/GitHub API/Kaggle API/webfetch），所有中国电力数据平台均**无法程序化自动获取**。

### Practical Implications

需**手动浏览器下载**电力数据。详见 `docs/chinese-electricity-data-guide.md`（已创建）。

### Recommended Data Strategy (User-Decided)

**用户选择：** 优先中国数据 + 手动获取。Phase 1 分两步走：
1. **主路径：** 用户根据指南手动从和鲸/天池/地方平台下载中国数据放入 `data/` 目录 → `ChineseDataLoader` 加载
2. **备用路径：** 如果短期获取不到中国数据 → `EpftoolboxLoader` 加载国际数据（德国EPEX-DE或美国PJM）先跑通管道

DataLoader 抽象层让两个数据源可互换，不影响下游预测/可视化代码。

### Data Source for Phase 1 Pipeline

**主数据源：** 用户手动获取的中国电力负荷数据（从和鲸社区、阿里天池、地方开放数据平台等）
- 期望格式：CSV/Excel，包含 `timestamp` + `load_mw` 列
- 加载方式：`ChineseDataLoader(data_path='data/xxx.csv')`

**备用数据源：** epftoolbox 内置数据集
- EPEX-DE: 德国日前市场，2015-2020，小时级，含负荷和电价
- PJM: 美国PJM市场，同样结构
- 安装：`pip install git+https://github.com/jeslago/epftoolbox.git`

---

## 2. Environment Setup

### Package List (Phase 1)

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Runtime |
| pandas | 3.0.3 | Core data processing |
| numpy | (via pandas) | Numerical operations |
| scikit-learn | 1.8.0 | TimeSeriesSplit, StandardScaler, model evaluation |
| xgboost | 3.2.0 | Gradient-boosted load forecasting |
| plotly | 6.7.0 | Interactive visualizations (user preference) |
| jupyter | 1.1.1 | Notebook interface |
| pyarrow | 22.0.0 | Parquet I/O (pandas Arrow backend) |
| nbformat | latest | Jupyter notebook version compatibility |

### `requirements.txt` structure

```text
# Core data processing
pandas==3.0.3
numpy>=2.0.0
pyarrow==22.0.0

# Machine learning
scikit-learn==1.8.0
xgboost==3.2.0

# Visualization
plotly==6.7.0

# Development
jupyter==1.1.1
nbformat>=5.0.0
```

### Setup command
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install git+https://github.com/jeslago/epftoolbox.git  # for reference datasets
```

---

## 3. XGBoost Load Forecasting

### TimeSeriesSplit Configuration

```python
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5, gap=24)
# gap=24 prevents autocorrelation leakage from 24h lag features
```

### Scaler Fit-on-Train-Only Pattern

```python
# WRONG — look-ahead bias
scaler = StandardScaler()
scaled_data = scaler.fit_transform(X)  # sees test data!

# CORRECT — encapsulated in forecaster
def train_evaluate(X, y, tscv):
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)  # fit on train only
        X_test_scaled = scaler.transform(X_test)          # transform test
        model = xgb.XGBRegressor(n_estimators=100, max_depth=6)
        model.fit(X_train_scaled, y.iloc[train_idx])
        yield model.predict(X_test_scaled), y.iloc[test_idx]
```

### Default Hyperparameters

```python
xgb.XGBRegressor(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
```

### Progressive Features (D-08)

- **Tier 1 (core):** hour, day_of_week, month, is_weekend, lag_24h
- **Tier 2 (add after baseline):** is_holiday, lag_168h
- **Tier 3 (add advanced):** rolling_mean_24h, rolling_std_24h, hour_sin, hour_cos

---

## 4. Plotly Integration

### Key Plot Types for Jupyter

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Load vs Prediction overlay
fig = go.Figure()
fig.add_trace(go.Scatter(x=test_timestamps, y=y_true, name='Actual Load', mode='lines'))
fig.add_trace(go.Scatter(x=test_timestamps, y=y_pred, name='Predicted Load', mode='lines'))
fig.update_layout(title='Load Forecast vs Actual', xaxis_title='Time', yaxis_title='Load (MW)')

# 2. Error distribution histogram
fig = go.Figure()
fig.add_trace(go.Histogram(x=errors, name='Prediction Errors', nbinsx=30))
fig.add_vline(x=0, line_dash='dash', line_color='red')

# 3. Residuals over time
fig = go.Figure()
fig.add_trace(go.Scatter(x=test_timestamps, y=errors, mode='markers', name='Residuals'))
fig.add_hline(y=0, line_dash='dash', line_color='red')
```

### Jupyter integration
```python
# In notebook:
import plotly.io as pio
pio.renderers.default = 'notebook'  # or 'jupyterlab'
```

---

## 5. Data Pipeline Architecture

### Module Structure

```
ellery/
├── pipeline/
│   ├── __init__.py
│   ├── data_loader.py    # DataLoader base class + implementations
│   ├── cleaner.py         # Data cleaning utilities
│   ├── features.py        # Feature engineering
│   └── forecaster.py      # Model training + evaluation
├── notebooks/
│   ├── 01_data_ingestion.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_load_forecasting.ipynb
│   └── 05_end_to_end_baseline.ipynb
├── data/
│   └── .gitkeep          # Local data storage (gitignored)
├── requirements.txt
├── setup.sh
└── README.md
```

### DataLoader Interface

```python
class DataLoader:
    """Abstract base for electricity data loading."""
    def load_hourly_demand(self, start=None, end=None) -> pd.DataFrame:
        """Return DataFrame with columns: timestamp, load_mw"""
        raise NotImplementedError

class EpftoolboxLoader(DataLoader):
    """Load data from epftoolbox built-in datasets."""
    def load_hourly_demand(self, start=None, end=None) -> pd.DataFrame:
        from epftoolbox.data import read_data
        df, _ = read_data('DE', path='.', begin_test_date='2025-01-01')
        # Transform to standard schema
        ...

class ChineseDataLoader(DataLoader):
    """Load Chinese electricity data from user-provided files."""
    def __init__(self, data_path: str):
        self.data_path = data_path
    
    def load_hourly_demand(self, start=None, end=None) -> pd.DataFrame:
        df = pd.read_parquet(self.data_path)  # or pd.read_csv
        # Expect columns: timestamp, load_mw, region
        ...
```

---

## 6. End-to-End Baseline Implementation

### Persistence Forecast

```python
def persistence_forecast(df: pd.DataFrame) -> pd.Series:
    """Yesterday's load = today's prediction (24h lag)"""
    return df['load_mw'].shift(24).fillna(method='bfill')
```

### Minimal P&L Calculation

```python
def calculate_pnl(actual: pd.Series, forecast: pd.Series, price: float = 50.0):
    """Assumes flat price ($50/MWh). Buy at forecast, settle at actual."""
    trades = (forecast - actual) * price  # positive = profit from over-forecast
    cumulative = trades.cumsum()
    return cumulative
```

---

## 7. Anti-Patterns to Enforce (from PITFALLS.md)

1. **Look-ahead bias**: `TimeSeriesSplit` + scaler-fit-on-train-only. Add a notebook check cell that greps for `fit_transform` on full dataset.
2. **No end-to-end early**: Notebook 05 (persistence → P&L) runs BEFORE XGBoost tuning (Notebook 04).
3. **Spike-as-noise**: IQR outlier detection is REPORT-ONLY, not removal. Electricity spikes are the signal.

---

## Open Questions (RESOLVED)

1. **Chinese data availability** → RESOLVED: Government portals require manual browser access. Use epftoolbox data as primary, provide ChineseDataLoader skeleton.
2. **enda dependency** → RESOLVED: Deferred to Phase 2. H2O JVM dependency conflicts with project constraints. All Phase 1 cleaning done with pandas.
3. **XGBoost hyperparameters** → RESOLVED: Use defaults (n_estimators=100, max_depth=6, learning_rate=0.1). Tuning is a learner exercise.
4. **Docker Compose timing** → RESOLVED: Create skeleton `docker-compose.yml` with commented-out services. Uncomment in Phase 2.

---

## Assumptions

| Risk | Mitigation |
|------|-----------|
| epftoolbox installed but data download fails | Document manual download from GitHub repo as fallback |
| plotly interactive mode fails in Jupyter | Fall back to `renderers.default = 'png'` for static output |
| pip install slow in China network | Document `-i https://pypi.tuna.tsinghua.edu.cn/simple` mirror option |
| XGBoost default params produce poor MAE | Accept any result — this is a learning project, not production tune |

---
*Research complete: 2026-05-20*
