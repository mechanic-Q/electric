# Conventions — Ellectric 项目编码规范

author: lmr | created_at: 2026-06-06T00:00:00+08:00

## 框架隐形规则

### 1.1 模块级三引号文档（模块契约）

每个 `.py` 文件以 `"""..."""` 模块级 docstring 开头，使用中英双语混合（Chinese + English），结构为：
- 文件标题（中文） + `=====` 下划线
- `~~~~` 分隔的段落标题（中文 + 英文术语）
- ASCII 图表用于架构概览
- 设计决策说明（"为什么用 X？"）

**证据**: `data_loader.py:1-50`, `cleaner.py:1-32`, `features.py:1-38`, `forecaster.py:1-43`

### 1.2 抽象基类 + 工厂函数（依赖倒置）

数据加载层使用 **ABC 抽象基类** 定义接口契约，通过 **工厂函数** 返回具体实例。下游代码只依赖 `DataLoader` 接口，不耦合具体数据源。

```
DataLoader(ABC)  ← 抽象基类，定义 load_data() 签名
  ├── OWIDChinaLoader    (自动拉取 OWID 数据)
  └── ChineseDataLoader  (手动加载本地 CSV)
create_loader(source) → DataLoader  ← 工厂函数
```

**证据**: `data_loader.py:91-105` (`class DataLoader(ABC)`, `@abstractmethod`), `data_loader.py:281` (`create_loader`)

### 1.3 数据合约模式（元数据驱动校验）

以 module-level `set` 定义列名合约，下游用 `validate_schema()` 校验：
- `REQUIRED_COLUMNS = {"timestamp", "load_mw"}` — 缺失直接报错
- `OPTIONAL_COLUMNS = {...}` — 有则保留，无则忽略

**证据**: `cleaner.py:42-44` (`REQUIRED_COLUMNS`, `OPTIONAL_COLUMNS`)

### 1.4 渐进式特征工程（Tier 分层）

特征工程分三层递进，每层有独立方法 + 独立日志：
- `tier1` (核心): hour, day_of_week, month, is_weekend, lag_24h
- `tier2` (中级): is_holiday, lag_168h
- `tier3` (高级): rolling_mean, rolling_std, hour_sin, hour_cos

内部用 `self._features_added` 追踪已添加层级，`get_feature_columns(tier)` 返回对应层级的特征名列表。

**证据**: `features.py:62-193` (`add_tier1/2/3_features`, `get_feature_columns`)

### 1.5 可选依赖的 try/except ImportError 模式

非核心依赖（如 `holidays` 包）使用 `try/except ImportError` 包裹，fallback 为默认值并记录 warning，保证管道不因缺失可选包而中断。

**证据**: `features.py:120-127` (`try: import holidays ... except ImportError: logger.warning(...)`)

---

## 代码风格

### 2.1 段落分隔符

- `# ═══════════════════` (双线等号) — 模块/大类之间的顶级分界
- `# ── ... ──` (双线破折号) — 函数内部逻辑段落的子级分界，带中文注释和右对齐终止符

**证据**: `data_loader.py:86-88`, `forecaster.py:164/186/201/215-217`, `cleaner.py:65/75/87/117`

### 2.2 类型标注 (Type Annotations)

全部函数签名使用完整类型标注：
- 参数: `pd.DataFrame`, `str`, `Optional[str]`, `list`
- 返回值: `-> pd.DataFrame`, `-> pd.Series`, `-> go.Figure`, `-> DataLoader`, `-> dict`
- 字符串引用: 使用 `"pd.DataFrame"` 或 `"np.ndarray"` 形式的 forward reference

**证据**: `data_loader.py:106`, `features.py:62/100/138`, `forecaster.py:54/81-85/126-130/298-298`

### 2.3 Logger 标准化

每个模块以固定模式初始化 logger：
```python
import logging
logger = logging.getLogger(__name__)
```
使用 `logger.info()` 报告进度，`logger.warning()` 报告降级，每条日志带中文描述。

**证据**: 所有 4 个 pipeline 模块均使用此模式 (`data_loader.py:58/61`, `cleaner.py:36/38`, `features.py:42/44`, `forecaster.py:47/51`)

### 2.4 内部函数命名

模块内部辅助函数使用 `_` 前缀（无装饰器，纯 Python 约定），类型标注完整：
- `_safe_float()` — 安全类型转换
- `_twh_to_daily_mw()` — 单位换算
- `_standardize_columns()` — 列名标准化

**证据**: `data_loader.py:322-390` (`_safe_float`, `_twh_to_daily_mw`, `_standardize_columns`)

### 2.5 内部属性追踪

类实例状态追踪使用 `self._` 前缀的内部属性，不带 property 装饰器：
- `FeatureEngineer._features_added: list` — 追踪已添加的 tier 层级

**证据**: `features.py:60`, `features.py:96/134/174`

---

## 符号注册表

所有模块间的数据合约和命名约定，新增代码必须遵守。

### DataFrame 列名合约

所有 DataLoader 产出、Cleander 消费的 DataFrame 必须包含：

| 列名 | 类型 | 说明 |
|------|------|------|
| `timestamp` | datetime64[ns, UTC] | 时间戳 |
| `load_mw` | float64 | 负荷值 (MW) |
| `region` | str | 区域标识（可选） |

```text
禁止: date, datetime, time, 日期, 时间  → 统一为 timestamp
禁止: load, demand, power, 负荷, 用电量  → 统一为 load_mw
```

### 预测器命名合约

所有预测器（持续法、XGBoost、LEAR）遵循统一接口：

| 方法 | 签名 | 说明 |
|------|------|------|
| `.train_evaluate(X, y)` | `→ dict` | 训练 + 评估，返回 {predictions, actuals, metrics, model} |
| `.predict(X)` | `→ np.ndarray` | 推理 |
| `.save_model(path)` | `→ None` | 持久化 (joblib) |
| `.load_model(path)` | `→ None` | 加载 |

### 特征工程命名

| 实际命名 | 含义 | 禁止别名 |
|----------|------|----------|
| `add_tier1_features` | 添加核心特征 (hour/day_of_week/month/is_weekend/lag_24h) | `generate_calendar_features` |
| `add_tier2_features` | 添加中级特征 (is_holiday/lag_168h) | `generate_lag_features` |
| `add_tier3_features` | 添加高级特征 (rolling_mean/std, hour_sin/cos) | `generate_rolling_features` |
| `get_feature_columns(tier)` | 返回指定 tier 的特征列名列表 | `get_feature_names` |

### DataLoader 命名合约

| 方法 | 说明 |
|------|------|
| `.load_data(start, end)` | 加载数据返回 DataFrame |
| `.load_hourly_demand(start, end)` | 返回 timestamp-indexed Series |
| `.get_metadata()` | 返回 {source, data_version, rows, start, end, frequency} |

### Cleaner 命名合约

| 函数 | 说明 |
|------|------|
| `clean_data(df) → DataFrame` | 主清洗入口 |
| `validate_schema(df) → dict` | 返回 {valid, issues, summary} |
| `detect_timezone(df) → str` | 返回 IANA 时区名 |
| `standardize_frequency(df) → DataFrame` | 时间频率规范化 |
| `get_data_quality_score(df) → dict` | 返回 {quality_score, details} |

### 禁止事项

- ✗ 同一概念用两个名称（如 `generate_features` vs `add_features`）
- ✗ 新增列不更新此注册表
- ✗ 预测器接口不统一（某些没有 save_model 是 bug，不是设计）
- ✗ 用 `df['timestamp'].dt.tz_localize()` 代替 `dt.tz_convert()` 在已知 UTC 的数据上

## Git 管理规范

### commit message 格式

```
<类型>(<范围>): <中文描述>

类型: 新增/修复/重构/文档/清理
范围: 阶段1/阶段2/pipeline/notebooks/配置

示例:
  新增(阶段1): OWID 中国数据自动拉取与清洗管道
  修复(阶段1): gap=24, MAE-only, 补充 save_model/plot_forecast
  重构(pipeline): 统一预测器接口 save/load/predict
  文档: 新增中国电力数据获取指南
```

### 分支命名

```
gsd/阶段1-数据基础     ← Phase 1
sillyspec/阶段2-重规划  ← Phase 2 worktree（SillySpec 自动创建）
```

### PR 与审查

- PR 标题和正文使用中文
- 每个阶段独立 PR，merge 到 master
- review 前确认所有 notebook JSON 有效、py 编译通过
