# Phase 1 调研: 数据基础 + 基础预测

**Phase:** 01 — 数据基础 + 基础预测
**调研日期:** 2026-05-20
**可信度:** MEDIUM（数据来源不确定性）

## 调研范围

根据 CONTEXT.md 决策：中国地方开放数据平台获取小时级负荷数据 → XGBoost 预测 → plotly 可视化 → MAE 评估 → pip+venv 环境。

---

## 1. 数据源可行性: 中国电力开放数据

### 调研结果

| 平台 | URL | 访问结果 | 可用数据 |
|----------|-----|---------------|----------------|
| 国家统计局 | data.stats.gov.cn | 403（被封锁） | 仅月度/年度宏观统计数据 |
| 深圳开放数据平台 | opendata.sz.gov.cn | 200，空响应 | 需登录/注册 |
| 上海开放数据 | data.sh.gov.cn | 412（前提条件失败） | 需验证码/人工交互 |
| 广东开放数据 | data.gd.gov.cn | TLS 错误 | HTTPS 握手失败 |
| 各种数据集平台 | 和鲸/天池/地方平台 | 需浏览器手动操作 | 存在电力负荷数据集 |

### 关键发现: 中国政府开放数据门户需要浏览器手动访问

经 7 轮测试（scrapling/httpcloak/camoufox/DuckDuckGo/GitHub API/Kaggle API/webfetch），所有中国电力数据平台均**无法程序化自动获取**。

### 实际影响

需**手动浏览器下载**电力数据。详见 `docs/chinese-electricity-data-guide.md`（已创建）。

### 数据策略（用户决定 — 仅中国数据）

**三路数据源，统一 DataLoader 接口：**

1. **OWID 年度数据（自动获取）：** Our World in Data 提供中国年度发电量/用电量数据（2000-2025），通过 `urllib` + CSV 流式解析自动拉取。用于宏观趋势分析。
2. **日级数据（手动下载）：** 从和鲸社区、阿里天池、地方开放数据平台手动获取。格式：CSV/Excel，包含 `timestamp` + `load_mw` 列。
3. **小时级数据（手动下载）：** 同上来源，理想情况下可做短期负荷预测。放入 `data/` 目录后由 `ChineseDataLoader` 自动加载。

**不依赖国际数据。** 不引入 epftoolbox（避免 TensorFlow/PyTorch 冲突），专注中国电力场景。

### Phase 1 管道的数据源

**主数据源：** OWID 中国年度数据（自动） + 用户手动获取的日/小时数据
- OWID: `https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv`
- 中国行过滤条件: `country == 'China' AND iso_code == 'CHN'`
- 关键列: `year`、`electricity_generation`、`electricity_demand`、`coal_electricity`、`solar_electricity`、`wind_electricity`
- 加载方式: `OWIDChinaLoader().load_yearly_data()` 和 `ChineseDataLoader(data_path='data/xxx.csv').load_data()`

---

## 2. 环境搭建

### 包列表（Phase 1）

| 包 | 版本 | 用途 |
|---------|---------|---------|
| Python | 3.11+ | 运行时 |
| pandas | 3.0.3 | 核心数据处理 |
| numpy | (由 pandas 引入) | 数值运算 |
| scikit-learn | 1.8.0 | TimeSeriesSplit、StandardScaler、模型评估 |
| xgboost | 3.2.0 | 梯度提升负荷预测 |
| plotly | 6.7.0 | 交互式可视化（用户偏好） |
| jupyter | 1.1.1 | Notebook 界面 |
| pyarrow | 22.0.0 | Parquet I/O（pandas Arrow 后端） |
| nbformat | latest | Jupyter notebook 版本兼容 |

### `requirements.txt` 结构

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

### 搭建命令
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # Windows 上为 .venv\Scripts\activate
pip install -r requirements.txt
pip install git+https://github.com/jeslago/epftoolbox.git  # 用于参考数据集
```

---

## 3. XGBoost 负荷预测

### TimeSeriesSplit 配置

```python
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5, gap=24)
# gap=24 防止 24h lag 特征的自相关泄漏
```

### Scaler 仅在训练集上 Fit 的模式

```python
# 错误 — look-ahead bias
scaler = StandardScaler()
scaled_data = scaler.fit_transform(X)  # 看到了测试数据！

# 正确 — 封装在预测器中
def train_evaluate(X, y, tscv):
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)  # 仅在训练集上 fit
        X_test_scaled = scaler.transform(X_test)          # transform 测试集
        model = xgb.XGBRegressor(n_estimators=100, max_depth=6)
        model.fit(X_train_scaled, y.iloc[train_idx])
        yield model.predict(X_test_scaled), y.iloc[test_idx]
```

### 默认超参数

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

### 渐进式特征 (D-08)

- **Tier 1（核心）:** hour、day_of_week、month、is_weekend、lag_24h
- **Tier 2（基线后添加）:** is_holiday、lag_168h
- **Tier 3（高级添加）:** rolling_mean_24h、rolling_std_24h、hour_sin、hour_cos

---

## 4. Plotly 集成

### Jupyter 关键图表类型

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 负荷 vs 预测叠加
fig = go.Figure()
fig.add_trace(go.Scatter(x=test_timestamps, y=y_true, name='实际负荷', mode='lines'))
fig.add_trace(go.Scatter(x=test_timestamps, y=y_pred, name='预测负荷', mode='lines'))
fig.update_layout(title='负荷预测 vs 实际', xaxis_title='时间', yaxis_title='负荷 (MW)')

# 2. 预测误差分布直方图
fig = go.Figure()
fig.add_trace(go.Histogram(x=errors, name='预测误差', nbinsx=30))
fig.add_vline(x=0, line_dash='dash', line_color='red')

# 3. 残差随时间变化
fig = go.Figure()
fig.add_trace(go.Scatter(x=test_timestamps, y=errors, mode='markers', name='残差'))
fig.add_hline(y=0, line_dash='dash', line_color='red')
```

### Jupyter 集成
```python
# 在 notebook 中:
import plotly.io as pio
pio.renderers.default = 'notebook'  # 或 'jupyterlab'
```

---

## 5. 数据管道架构

### 模块结构

```
ellectric/
├── pipeline/
│   ├── __init__.py
│   ├── data_loader.py    # DataLoader 基类 + 实现
│   ├── cleaner.py         # 数据清洗工具
│   ├── features.py        # 特征工程
│   └── forecaster.py      # 模型训练 + 评估
├── notebooks/
│   ├── 01_data_ingestion.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_load_forecasting.ipynb
│   └── 05_end_to_end_baseline.ipynb
├── data/
│   └── .gitkeep          # 本地数据存储（gitignored）
├── requirements.txt
├── setup.sh
└── README.md
```

### DataLoader 接口

```python
class DataLoader:
    """电力数据加载抽象基类。"""
    def load_hourly_demand(self, start=None, end=None) -> pd.DataFrame:
        """返回含列 timestamp、load_mw 的 DataFrame"""
        raise NotImplementedError

class EpftoolboxLoader(DataLoader):
    """从 epftoolbox 内置数据集加载数据。"""
    def load_hourly_demand(self, start=None, end=None) -> pd.DataFrame:
        from epftoolbox.data import read_data
        df, _ = read_data('DE', path='.', begin_test_date='2025-01-01')
        # 转换为标准 schema
        ...

class ChineseDataLoader(DataLoader):
    """从用户提供的文件加载中国电力数据。"""
    def __init__(self, data_path: str):
        self.data_path = data_path
    
    def load_hourly_demand(self, start=None, end=None) -> pd.DataFrame:
        df = pd.read_parquet(self.data_path)  # 或 pd.read_csv
        # 预期列: timestamp、load_mw、region
        ...
```

---

## 6. 端到端基线实现

### 持久性预测

```python
def persistence_forecast(df: pd.DataFrame) -> pd.Series:
    """昨天的负荷 = 今天的预测（24h lag）"""
    return df['load_mw'].shift(24).fillna(method='bfill')
```

### 最小 P&L 计算

```python
def calculate_pnl(actual: pd.Series, forecast: pd.Series, price: float = 50.0):
    """假设固定电价（$50/MWh）。按预测买入，按实际结算。"""
    trades = (forecast - actual) * price  # 正向 = 预测偏高带来的利润
    cumulative = trades.cumsum()
    return cumulative
```

---

## 7. 需强制执行的反模式（来自 PITFALLS.md）

1. **Look-ahead bias**: `TimeSeriesSplit` + scaler 仅在训练集上 fit。添加 notebook 检查 cell，对完整数据集 grep `fit_transform`。
2. **不早做端到端**: Notebook 05（持久性 → P&L）在 XGBoost 调优（Notebook 04）之前运行。
3. **Spike-as-noise**: IQR 离群值检测仅报告，不删除。电力 spike 就是信号。

---

## 8. 未决问题（已解决）

1. **中国数据可用性** → 已解决：政府门户需要浏览器手动访问。使用 epftoolbox 数据作为主数据源，提供 ChineseDataLoader 骨架。
2. **enda 依赖** → 已解决：推迟到 Phase 2。H2O JVM 依赖与项目约束冲突。Phase 1 所有清洗用 pandas 完成。
3. **XGBoost 超参数** → 已解决：使用默认值（n_estimators=100, max_depth=6, learning_rate=0.1）。调优作为学习者练习。
4. **Docker Compose 时机** → 已解决：创建含注释服务的骨架 `docker-compose.yml`。Phase 2 取消注释。

---

## 假设与风险

| 风险 | 缓解措施 |
|------|-----------|
| epftoolbox 安装成功但数据下载失败 | 记录从 GitHub repo 手动下载作为备选方案 |
| plotly 交互模式在 Jupyter 中失败 | 降级使用 `renderers.default = 'png'` 输出静态图 |
| 国内网络 pip install 慢 | 记录 `-i https://pypi.tuna.tsinghua.edu.cn/simple` 镜像选项 |
| XGBoost 默认参数 MAE 表现差 | 接受任何结果 — 这是学习项目，不是生产调优 |

---
*调研完成于: 2026-05-20*
