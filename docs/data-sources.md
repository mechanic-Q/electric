# 数据源一览

## 数据源总览

| 数据源 | 粒度 | 时间范围 | 获取方式 | 状态 |
|--------|------|----------|----------|------|
| OWID | 年度 | 2000–2025 | 自动（三级回退） | 生产就绪 |
| ChineseDataLoader | 日/小时 | 用户自定义 | 手动本地文件 | 生产就绪 |
| Ember | 小时 | 近年 | API（探索性） | 实验性 |

---

## 1. OWID（Our World in Data）

OWID 能源数据库整合了 Ember、EIA、IEA 等多个权威数据源，是本项目的主数据源。

### 数据特点

- **粒度**：年度（每年一行）
- **范围**：2000–2025 年，中国（`iso_code == 'CHN'`）
- **字段**：发电量、用电量、煤电、水电、风电、太阳能、核电等
- **转换**：TWh → 日均 MW（`_twh_to_daily_mw()`）

### 三级回退策略

`OWIDChinaLoader` 依次尝试以下数据源，任一成功即停止：

1. **OWID 官方 CDN**（`owid-public.owid.io`）— 国内访问较稳定，15 秒超时
2. **GitHub Raw**（`raw.githubusercontent.com`）— 备用通道，30 秒超时
3. **本地 Parquet 缓存** — 兜底方案，网络全断时使用上次成功拉取的数据

### 缓存机制

- 成功拉取后自动写入：`ellectric/data/owid_china_cache.parquet`
- 缓存格式：Parquet 列式存储（高效压缩）
- 跳过缓存：调用 `load_data(refresh=True)` 强制从网络重新拉取
- 缓存大小约 50KB（相比原始 CSV 25MB 大幅压缩）

### 使用方式

```python
from ellectric.pipeline.data_loader import OWIDChinaLoader

loader = OWIDChinaLoader()
df = loader.load_data()              # 优先网络，失败读缓存
df = loader.load_data(refresh=True)  # 强制刷新
meta = loader.get_metadata()         # 元信息：source, rows, start, end
```

---

## 2. ChineseDataLoader（手动本地）

用于加载手动下载的日级或小时级本地数据文件，支持 CSV、Excel、Parquet 格式。

### 数据特点

- **粒度**：日级或小时级（取决于源文件）
- **范围**：用户自行准备
- **文件位置**：`ellectric/data/` 目录下
- **格式**：CSV、Excel（.xlsx）、Parquet（.parquet）

### 使用方式

```python
from ellectric.pipeline.data_loader import ChineseDataLoader

loader = ChineseDataLoader("data/my_data.csv")
df = loader.load_data()
```

---

## 3. Ember（探索性）

Ember 是一个专注于电力行业碳排放和能源转型的独立智库，提供全球电力行业的小时级和日级数据。

### 当前状态

- **集成状态**：未集成到主流程，仅作为探索性数据源
- **API 访问**：部分数据需要申请 API Key
- **粒度**：小时级（高频数据，适合市场仿真）

### 潜在用途

- 高频负荷预测（小时级 vs OWID 的年度）
- 碳排放因子分析
- 电力市场实时价格模拟

---

## 数据合约

所有 DataLoader 子类必须遵守以下数据契约：

### 必须包含的列

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `timestamp` | datetime64[ns, UTC] | 必需 | 时间戳，强制 UTC 时区 |
| `load_mw` | float64 | 必需 | 电力负荷，单位 MW |

### 禁止的列名别名

以下名称**不允许**作为 `timestamp` 或 `load_mw` 的别名：

- 时间相关：`date`, `datetime`, `time`, `日期`, `时间`
- 负荷相关：`load`, `demand`, `power`, `用电量`, `负荷`

### 原因

统一的数据合约确保下游模块（清洗、特征工程、预测）无需针对不同数据源编写适配代码，实现**依赖倒置**。

---

## 文件位置汇总

| 文件 | 路径 | 说明 |
|------|------|------|
| OWID 缓存 | `ellectric/data/owid_china_cache.parquet` | 网络拉取的本地备份 |
| 用户数据 | `ellectric/data/*.csv / *.xlsx / *.parquet` | 手动放置的本地数据 |
| 数据加载器 | `ellectric/pipeline/data_loader.py` | 所有 DataLoader 实现 |
