# Conventions — Ellectric 项目编码规范

author: lmr | created_at: 2026-06-06T00:00:00+08:00 | updated_at: 2026-06-10T00:00:00+08:00

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
- `BacktestRunner._env_factory` — 环境工厂
- `ElectricityMarketEnv._max_capacity` — 最大容量

**证据**: `features.py:60`, `backtester.py:140`, `trading_env.py`

### 2.6 延迟导入模式（Phase 4）

所有 pipeline 模块在 handlers.py 中以函数内 `import` 形式延迟加载，避免模块级循环依赖：

```python
def _run_load_forecast(req: ForecastRequest) -> ForecastResponse:
    from ellectric.pipeline.forecaster import XGBoostForecaster  # 函数内导入
    ...
```

**适用范围**: `service/handlers.py` 中的所有 4 个业务 handler

**证据**: `handlers.py:69-71`, `handlers.py:100-102`, `handlers.py:222-225`, `handlers.py:300-305`

### 2.7 Pydantic v2 Schema 惯例（Phase 4）

所有数据模型使用 Pydantic v2 原生 API（不使用 v1 兼容语法）：

```python
# model_validator(mode="after") 替代 @validator
@model_validator(mode="after")
def _check_length_match(self) -> "ForecastResponse":
    if len(self.timestamps) != len(self.predictions):
        raise ValueError("timestamps and predictions must have same length")
    return self

# field_validator 替代 @validator
@field_validator("horizon")
@classmethod
def _check_horizon(cls, v: int) -> int:
    ...

# Literal 类型替代 Enum
model_type: Literal["load", "price"]

# model_config 替代 class Config
model_config = {"exclude_none": True}

# None | Type 替代 Optional[Type]
sharpe_ratio: float | None = None
```

**证据**: `schemas.py:84-88`, `schemas.py:78`, `schemas.py:194`

### 2.8 LLM @tool 模式（Phase 4）

LangChain 工具函数使用 `@tool` 装饰器，函数体通过模块级共享 `httpx.Client` 调用本地 FastAPI：

```python
_CLIENT = httpx.Client(timeout=30.0)  # 模块级共享

@tool
def query_forecast(model_type: str, horizon: int = 24) -> str:
    """查询负荷或电价预测结果。"""
    ...
```

- 所有工具函数返回字符串（JSON 或错误描述）
- httpx 请求使用 `raise_for_status()` 异常传递
- 3 层错误处理: TimeoutException → HTTPStatusError → RequestError

**证据**: `tools.py:19-20`, `tools.py:23-54`

### 2.9 RL Agent 工厂模式（Phase 3）

```python
BaseRLAgent(ABC)          # 抽象基类，定义 train/predict/save/load
  ├── PPOAgent            # stable-baselines3 PPO 适配器
  ├── SACAgent            # stable-baselines3 SAC 适配器
  └── TD3Agent            # stable-baselines3 TD3 适配器

RLAgentFactory.create("ppo", env) → BaseRLAgent  # 工厂创建
RLAgentFactory.load("ppo", path) → BaseRLAgent   # 加载已有模型
```

**证据**: `rl_trainer.py:33-42`, `rl_trainer.py:150-175`

### 2.10 预测器统一接口（跨所有预测器）

XGBoostForecaster 和 LEARForecaster 共享同一接口契约：

| 方法 | 签名 | 说明 |
|------|------|------|
| `.train_evaluate(X, y)` | `→ dict` | 训练 + 评估，返回 {predictions, actuals, metrics, model} |
| `.predict(X)` | `→ np.ndarray` | 推理 |
| `.save_model(path)` | `→ None` | joblib 持久化 |
| `.load_model(path)` | `→ None` | 加载 |

**证据**: `forecaster.py`, `price_forecaster.py`

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

所有预测器（持续法、XGBoost、LEAR）遵循统一接口（已实施于 forecaster.py 和 price_forecaster.py）：

| 方法 | 签名 | 说明 |
|------|------|------|
| `.train_evaluate(X, y)` | `→ dict` | 训练 + 评估，返回 {predictions, actuals, metrics, model} |
| `.predict(X)` | `→ np.ndarray` | 推理 |
| `.save_model(path)` | `→ None` | 持久化 (joblib) |
| `.load_model(path)` | `→ None` | 加载 |

### 特征工程命名（负荷 / 电价）

| 模块 | 实际命名 | 含义 | 证据 |
|------|----------|------|------|
| `features.py` | `add_tier1/2/3_features` | 负荷特征 3 层 | `features.py:62-193` |
| `features.py` | `get_feature_columns(tier)` | 返回 tier 特征列名 | `features.py:55-58` |
| `price_forecaster.py` | `add_price_features(df, "tier3")` | 电价特征 3 层 | `price_forecaster.py:50-68` |
| `price_forecaster.py` | `_TIER1/2/3_COLS` | 模块级特征列名常量 | `price_forecaster.py:50-62` |
| `price_forecaster.py` | `_FEATURE_MAP` | tier→列名映射字典 | `price_forecaster.py:64-68` |

### DataLoader / PriceDataLoader 命名合约

| 类 | 方法 | 说明 |
|------|------|------|
| DataLoader (ABC) | `.load_data(start, end)` | 加载负荷数据 → DataFrame[timestamp, load_mw] |
| DataLoader (ABC) | `.load_hourly_demand(start, end)` | 返回 timestamp-indexed Series |
| DataLoader (ABC) | `.get_metadata()` | 返回 {source, data_version, rows, start, end, frequency} |
| PriceDataLoader | `.load_data()` | 加载电价数据 → DataFrame[7 columns] |
| PriceDataLoader | `.get_metadata()` | 返回 {source, data_version, rows, columns} |

**注意**: PriceDataLoader 不继承 DataLoader ABC（组合优于继承），但接口风格一致。

### Cleaner 命名合约

| 函数 | 说明 |
|------|------|
| `clean_data(df) → DataFrame` | 主清洗入口 |
| `validate_schema(df) → dict` | 返回 {valid, issues, summary} |
| `detect_timezone(df) → str` | 返回 IANA 时区名 |
| `standardize_frequency(df) → DataFrame` | 时间频率规范化 |
| `get_data_quality_score(df) → dict` | 返回 {quality_score, details} |

### 新增命名约定（Phase 2-4）

| 模块 | 名称 | 含义 |
|------|------|------|
| `trading_env.py` | `ElectricityMarketEnv` | Gymnasium RL 环境 |
| `trading_env.py` | `RewardRegistry.register/get/list` | 奖励函数注册表模式 |
| `trading_env.py` | `RewardFunction` (Protocol) | 奖励函数接口协议 |
| `rl_trainer.py` | `BaseRLAgent` (ABC) | RL 智能体抽象基类 |
| `rl_trainer.py` | `RLAgentFactory.create/load` | RL 智能体工厂 |
| `backtester.py` | `BacktestRunner.replay/compare` | 回测运行器 |
| `backtester.py` | `baseline_persistence/mean/oracle` | 基线策略函数 |
| `backtester.py` | `SUPPORTED_STRATEGIES` | 策略名常量列表 |
| `shap_explainer.py` | `explain_xgboost_sample/explain_lear_sample` | SHAP waterfall |
| `shap_explainer.py` | `feature_importance_ranking` | 跨模型特征重要性 |
| `shap_explainer.py` | `_get_shap()` | 惰性导入 shap |
| `statistical_tests.py` | `run_statistical_tests()` | DM/GW 检验入口 |
| `handlers.py` | `run_forecast/simulate/backtest/explain` | 业务 handler |
| `handlers.py` | `_get_model_dir()/_get_data_dir()` | 目录解析辅助函数 |
| `handlers.py` | `_CONFIGURE_MAP` | ASSUME 场景配置映射 |
| `handlers.py` | `_SUPPORTED_STRATEGIES` | 支持的回测策略集合 |
| `tools.py` | `_CLIENT` | 模块级共享 httpx 客户端 |
| `tools.py` | `query_forecast/run_simulation/run_backtest` | @tool 装饰函数 |
| `schemas.py` | `*Request` / `*Response` | Pydantic v2 数据契约 |

### 禁止事项

- ✗ 同一概念用两个名称（如 `generate_features` vs `add_features`）
- ✗ 新增列不更新此注册表
- ✗ 预测器接口不统一（某些没有 save_model 是 bug，不是设计）
- ✗ 用 `df['timestamp'].dt.tz_localize()` 代替 `dt.tz_convert()` 在已知 UTC 的数据上
- ✗ 在 handlers.py 模块级别导入 pipeline 模块（必须函数内 lazy import）
- ✗ handlers.py 中 run_* 函数抛出非 `ValueError`/`FileNotFoundError`/`RuntimeError` 的异常
- ✗ LLM tools 中硬编码 API URL（必须通过 `ELLECTRIC_API_URL` 环境变量配置）
- ✗ 在 `trading_env.py` 中使用 `gym` 而非 `gymnasium`（gym 已废弃，本项目使用 gymnasium 1.2.3）
- ✗ Pydantic v1 API（`@validator`, `class Config`）—— 本项目仅使用 v2 语法
- ✗ shap 模块级导入（必须通过 `_get_shap()` 函内惰性导入）

## Git 管理规范

### commit message 格式

```
<类型>(<范围>): <中文描述>

类型: 新增/修复/重构/文档/清理
范围: 阶段1/阶段2/阶段3/阶段4/pipeline/notebooks/配置/api/service/cli/llm/assume

示例:
  新增(阶段1): OWID 中国数据自动拉取与清洗管道
  修复(阶段1): gap=24, MAE-only, 补充 save_model/plot_forecast
  修(pipeline): 统一预测器接口 save/load/predict
  新增(阶段2): LEAR 电价预测器 + DM/GW 统计检验
  新增(阶段3): RL 交易智能体 PPO/SAC/TD3 + 回测引擎
  新增(阶段4): FastAPI/CLI/LLM 集成层
  修复(阶段4): handlers.py ASSUME配置路径+subprocess路径错误
  清理: 移除未使用的导入和过期注释
```

### 分支命名

```
gsd/阶段1-数据基础       ← Phase 1
sillyspec/阶段2-重规划    ← Phase 2 worktree（SillySpec 自动创建）
sillyspec/阶段3-rl交易    ← Phase 3 worktree
sillyspec/阶段4-集成      ← Phase 4 worktree
```

### PR 与审查

- PR 标题和正文使用中文
- 每个阶段独立 PR，merge 到 master
- review 前确认所有 notebook JSON 有效、py 编译通过
- Phase 4 审查特别注意点：
  - Pydantic v2 语法正确性（无 v1 遗留）
  - handlers.py 延迟导入模式是否保持（无模块级 pipeline import）
  - CLI --json 输出是否完整性（无序列化遗漏）
  - LLM tools 错误处理是否覆盖所有 httpx 异常类型

### 文档语言规范

- 所有计划文档（`.planning/`）使用中文，技术术语保留英文
- commit message 使用中文
- PR 标题和正文使用中文
- 代码注释使用中文
- 技术术语保留英文：XGBoost, MAE, TimeSeriesSplit, RL, LLM, API, CLI
