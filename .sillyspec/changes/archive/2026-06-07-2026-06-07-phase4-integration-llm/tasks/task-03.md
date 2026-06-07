---
author: lmr
created_at: 2026-06-07 23:55:29
id: task-03
title: Handler 函数实现
priority: P0
estimated_hours: 3
depends_on: [task-02]
blocks: [task-04, task-05]
allowed_paths:
  - ellectric/service/handlers.py
  - ellectric/service/__init__.py
---
# task-03: Handler 函数实现

## 修改文件

- **新增**: `ellectric/service/handlers.py` — 4 个业务函数 + 辅助函数
- **新增**: `ellectric/service/__init__.py` — 空包标记

## 概述

实现 4 个 handler 函数，桥接 Pydantic schema（task-02）到 pipeline 模块（forecaster、price_forecaster、backtester、shap_explainer）。handler 是零胶水层——不做业务逻辑，只做数据加载、模型加载、参数转换、结果格式化。

## 实现要求

### 0. 包标记 (`__init__.py`)

```python
# ellectric/service/__init__.py
```

空文件即可。

### 1. `run_forecast(req: ForecastRequest) -> ForecastResponse`

**流量**:
1. 校验 `model_type` → `"load"` 或 `"price"`，其他值 raise `ValueError`
2. 按 `model_type` 决定模型和数据加载路径

**load 预测分支**:
```python
from ellectric.pipeline.forecaster import XGBoostForecaster
from ellectric.pipeline.data_loader import OWIDChinaLoader
from ellectric.pipeline.features import FeatureEngineer

model_dir = os.environ.get("ELLECTRIC_MODEL_DIR", "ellectric/models/")
data_dir = os.environ.get("ELLECTRIC_DATA_DIR", "ellectric/data/")

model_path = os.path.join(model_dir, "xgboost_model.joblib")
if not os.path.exists(model_path):
    raise FileNotFoundError(f"XGBoost 模型文件未找到: {model_path}")
forecaster = XGBoostForecaster()
forecaster.load_model(model_path)

loader = OWIDChinaLoader()
df = loader.load_data()

engineer = FeatureEngineer()
df_feat = engineer.add_tier1_features(df)
df_feat = engineer.add_tier2_features(df_feat)
df_feat = engineer.add_tier3_features(df_feat)

# 取最后 horizon 条作为预测输入
X = df_feat[forecaster._feature_cols].iloc[-req.horizon:]
predictions = forecaster.predict(X)
timestamps = df_feat["timestamp"].iloc[-req.horizon:].tolist()

# metrics 来自最近一次 train_evaluate 结果，若无则 None
metrics = ...  # 从模型元数据或 None
```

**price 预测分支**:
```python
from ellectric.pipeline.price_forecaster import LEARForecaster
from ellectric.pipeline.price_loader import PriceDataLoader

model_path = os.path.join(model_dir, "lear_model.joblib")
if not os.path.exists(model_path):
    raise FileNotFoundError(f"LEAR 模型文件未找到: {model_path}")
forecaster = LEARForecaster()
forecaster.load_model(model_path)

xlsx_path = os.path.join(data_dir, "price_data.xlsx")
loader = PriceDataLoader(xlsx_path)
df = loader.load_data()

df_feat = forecaster.add_price_features(df, "tier3")
X = df_feat[forecaster._feature_cols].iloc[-req.horizon:]
predictions = forecaster.predict(X)
timestamps = df_feat["timestamp"].iloc[-req.horizon:].tolist()
```

**返回**:
```python
from ellectric.service.schemas import ForecastResponse, ForecastMetrics
metrics_obj = ForecastMetrics(mae=result.get("mae"), rmse=None, mape=None)
return ForecastResponse(
    timestamps=timestamps,
    predictions=predictions.tolist(),
    metrics=metrics_obj,
)
```

### 2. `run_simulate(req: SimulateRequest) -> SimulateResponse`

**流量**:
1. 映射 `config` 到 YAML 配置路径
2. 通过 `subprocess.run` 调用 ASSUME 仿真
3. 解析 CSV 输出文件
4. 返回 SimulateResponse

```python
import subprocess, csv, os

CONFIG_MAP = {
    "default": "ellectric/assume/configs/default.yaml",
    "summer_peak": "ellectric/assume/configs/summer_peak.yaml",
    "wind_high": "ellectric/assume/configs/wind_high.yaml",
}

config_path = CONFIG_MAP.get(req.config)
if config_path is None:
    raise ValueError(f"未知场景 '{req.config}'，可选: {list(CONFIG_MAP.keys())}")
if not os.path.exists(config_path):
    raise FileNotFoundError(f"场景配置文件未找到: {config_path}")

output_dir = f"/tmp/assume_results_{req.config}_{int(time.time())}"

result = subprocess.run(
    ["python", "assume/run_simulation.py",
     "--config", config_path,
     "--output", output_dir,
     "--days", str(req.days)],
    capture_output=True, text=True, timeout=600,
)
if result.returncode != 0:
    raise RuntimeError(
        f"ASSUME 仿真失败 (returncode={result.returncode})\n"
        f"stderr: {result.stderr}"
    )

# 解析 CSV 输出
clearing_prices = []
dispatch = []
agent_profits = {}

prices_path = os.path.join(output_dir, "clearing_prices.csv")
if os.path.exists(prices_path):
    with open(prices_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            clearing_prices.append(float(row["clearing_price"]))

dispatch_path = os.path.join(output_dir, "dispatch.csv")
if os.path.exists(dispatch_path):
    df_dispatch = pd.read_csv(dispatch_path)
    dispatch = df_dispatch.to_dict(orient="records")

profits_path = os.path.join(output_dir, "agent_profits.csv")
if os.path.exists(profits_path):
    df_profits = pd.read_csv(profits_path)
    agent_profits = dict(zip(df_profits["agent"], df_profits["profit"]))

return SimulateResponse(
    status="success",
    clearing_prices=clearing_prices,
    dispatch=dispatch,
    agent_profits=agent_profits,
    output_dir=output_dir,
)
```

### 3. `run_backtest(req: BacktestRequest) -> BacktestResponse`

**流量**:
1. 校验日期格式 `YYYY-MM-DD`（正则 `^\d{4}-\d{2}-\d{2}$`）
2. 校验 `start < end`
3. 分类策略：
   - 基线策略（`baseline_persistence`、`baseline_mean`、`oracle`）: `model=None`
   - RL 策略（`ppo`、`sac`、`td3`）: 需要 `model_path` 参数
4. 加载数据 → 创建 `BacktestRunner` → `replay()` → 累计 P&L 和指标
5. 可选运行多个基线做 `compare()` 对比

```python
import re, os
from ellectric.pipeline.backtester import BacktestRunner
from ellectric.pipeline.data_loader import OWIDChinaLoader
from ellectric.pipeline.price_loader import PriceDataLoader
from ellectric.pipeline.rl_trainer import RLAgentFactory

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BASELINE_STRATEGIES = {"baseline_persistence", "baseline_mean", "oracle"}
RL_STRATEGIES = {"ppo", "sac", "td3"}
SUPPORTED_STRATEGIES = BASELINE_STRATEGIES | RL_STRATEGIES

# 策略校验
if req.strategy not in SUPPORTED_STRATEGIES:
    raise ValueError(
        f"未知策略 '{req.strategy}'，可选: {sorted(SUPPORTED_STRATEGIES)}"
    )
if not DATE_PATTERN.match(req.start_date.isoformat()):
    raise ValueError(f"start_date 格式非法: {req.start_date}（应为 YYYY-MM-DD）")
if not DATE_PATTERN.match(req.end_date.isoformat()):
    raise ValueError(f"end_date 格式非法: {req.end_date}（应为 YYYY-MM-DD）")
if req.start_date >= req.end_date:
    raise ValueError(f"start_date ({req.start_date}) 必须早于 end_date ({req.end_date})")

start = req.start_date.isoformat()
end = req.end_date.isoformat()

# RL 策略必须提供 model_path
if req.strategy in RL_STRATEGIES and not req.model_path:
    raise ValueError(
        f"RL 策略 '{req.strategy}' 需要提供 model_path 参数"
    )
# 基线策略不需要 model_path
if req.strategy in BASELINE_STRATEGIES:
    req.model_path = None  # 确保为 None

# 加载数据
loader = OWIDChinaLoader()
load_df = loader.load_data()

price_loader = PriceDataLoader(
    os.path.join(os.environ.get("ELLECTRIC_DATA_DIR", "ellectric/data/"), "price_data.xlsx")
)
price_df = price_loader.load_data()

# 创建环境和 runner
from ellectric.pipeline.trading_env import ElectricityMarketEnv
env_factory = lambda: ElectricityMarketEnv(load_df, price_df, None, None)
runner = BacktestRunner(env_factory)

# 执行回放
if req.strategy in RL_STRATEGIES:
    from ellectric.pipeline.rl_trainer import RLAgentFactory
    agent = RLAgentFactory.load(req.strategy, req.model_path)
    replay_df = runner.replay(agent, load_df, price_df, start, end, strategy_name=req.strategy)
else:
    replay_df = runner.replay(None, load_df, price_df, start, end, strategy_name=req.strategy)

# 运行基线对比
comparison_results = {
    req.strategy: replay_df,
}
for baseline in ["baseline_persistence", "baseline_mean"]:
    df_bs = runner.replay(None, load_df, price_df, start, end, strategy_name=baseline)
    comparison_results[baseline] = df_bs
comparison_df = runner.compare(comparison_results)

# 构建响应
cumulative_pnl = replay_df["pnl_cumulative"].tolist()
comparison_dict = {
    row["策略"]: row["总收益"]
    for _, row in comparison_df.iterrows()
}
sharpe_row = comparison_df[comparison_df["策略"] == req.strategy]
sharpe_val = float(sharpe_row["夏普比率"].iloc[0]) if len(sharpe_row) > 0 else None

return BacktestResponse(
    status="success",
    cumulative_pnl=cumulative_pnl,
    sharpe_ratio=sharpe_val,
    comparison=comparison_dict,
    plot_data=None,  # Wave 2 中由 API 层生成
)
```

### 4. `run_explain(req: ExplainRequest) -> ExplainResponse`

**流量**:
1. 校验 `model_type` → `"xgboost"` 或 `"lear"`
2. 加载对应模型和数据
3. 调用 SHAP waterfall 和特征重要性
4. 将 plotly Figure 序列化为 JSON

```python
import json
from ellectric.service.schemas import ExplainResponse, FeatureImportance

model_dir = os.environ.get("ELLECTRIC_MODEL_DIR", "ellectric/models/")
data_dir = os.environ.get("ELLECTRIC_DATA_DIR", "ellectric/data/")

if req.model_type == "xgboost":
    from ellectric.pipeline.forecaster import XGBoostForecaster
    from ellectric.pipeline.data_loader import OWIDChinaLoader
    from ellectric.pipeline.features import FeatureEngineer
    from ellectric.pipeline.shap_explainer import (
        explain_xgboost_sample,
        feature_importance_ranking,
    )

    model_path = os.path.join(model_dir, "xgboost_model.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"XGBoost 模型文件未找到: {model_path}")
    forecaster = XGBoostForecaster()
    forecaster.load_model(model_path)

    loader = OWIDChinaLoader()
    df = loader.load_data()
    engineer = FeatureEngineer()
    df_feat = engineer.add_tier1_features(df)
    df_feat = engineer.add_tier2_features(df_feat)
    df_feat = engineer.add_tier3_features(df_feat)

    waterfall_fig = explain_xgboost_sample(
        forecaster, df_feat, req.sample_index, req.max_display
    )
    models = {"XGBoost": forecaster}
    importance_df = feature_importance_ranking(models, forecaster._feature_cols)

elif req.model_type == "lear":
    from ellectric.pipeline.price_forecaster import LEARForecaster
    from ellectric.pipeline.price_loader import PriceDataLoader
    from ellectric.pipeline.shap_explainer import (
        explain_lear_sample,
        feature_importance_ranking,
    )

    model_path = os.path.join(model_dir, "lear_model.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"LEAR 模型文件未找到: {model_path}")
    forecaster = LEARForecaster()
    forecaster.load_model(model_path)

    xlsx_path = os.path.join(data_dir, "price_data.xlsx")
    loader = PriceDataLoader(xlsx_path)
    df = loader.load_data()
    df_feat = forecaster.add_price_features(df, "tier3")

    waterfall_fig = explain_lear_sample(
        forecaster, df_feat, req.sample_index, req.max_display
    )
    models = {"LEAR": forecaster}
    importance_df = feature_importance_ranking(models, forecaster._feature_cols)

else:
    raise ValueError(f"不支持的 model_type '{req.model_type}'，可选: 'xgboost', 'lear'")

# 序列化 waterfall 为 Plotly JSON
waterfall_json = json.loads(waterfall_fig.to_json())

# 从 DataFrame 构建 FeatureImportance 列表
feature_importance_list = [
    FeatureImportance(
        name=row["feature"],
        importance=float(row["importance"]),
        rank=int(row["rank"]),
    )
    for _, row in importance_df.iterrows()
]

return ExplainResponse(
    status="success",
    feature_importance=feature_importance_list,
    waterfall_json=waterfall_json,
)
```

## 依赖路径

```
from ellectric.service.schemas import (
    ForecastRequest, ForecastResponse, ForecastMetrics,
    SimulateRequest, SimulateResponse,
    BacktestRequest, BacktestResponse,
    ExplainRequest, ExplainResponse, FeatureImportance,
)
```

## 边界处理

| # | 条件 | 行为 |
|---|------|------|
| 1 | `model_type` 非 `"load"`/`"price"` (forecast) 或 `"xgboost"`/`"lear"` (explain) | `raise ValueError` 列出可选值 |
| 2 | 模型文件不存在 (`xgboost_model.joblib` 或 `lear_model.joblib`) | `raise FileNotFoundError` 附带完整路径 |
| 3 | ASSUME `subprocess.run` returncode != 0 | `raise RuntimeError` 附带 `stderr` |
| 4 | ASSUME subprocess 超时 (超过 600s) | `subprocess.TimeoutExpired` 自然传播 |
| 5 | `start_date`/`end_date` 格式非法（不匹配 `YYYY-MM-DD`） | `raise ValueError` 指明格式 |
| 6 | `start_date >= end_date` | `raise ValueError` |
| 7 | RL 策略 (`ppo`/`sac`/`td3`) 且 `model_path=None` | `raise ValueError` 要求提供模型路径 |
| 8 | 基线策略 (`baseline_persistence`/`baseline_mean`/`oracle`) 忽略传入的 `model_path` | 静默设为 `None`，不报错 |
| 9 | `req.config` (simulate) 不在 `CONFIG_MAP` 中 | `raise ValueError` 列出可选场景 |
| 10 | `req.strategy` (backtest) 不是支持的策略 | `raise ValueError` 列出可选策略 |
| 11 | SHAP explainer `sample_index` 越界 | `IndexError` 自然传播 |
| 12 | 数据加载器找不到文件 (`PriceDataLoader` / `OWIDChinaLoader`) | `FileNotFoundError` 自然传播 |
| 13 | BacktestRunner 数据重叠校验失败 | `ValueError` 自然传播 |
| 14 | `ELLECTRIC_MODEL_DIR` / `ELLECTRIC_DATA_DIR` 环境变量不设置 | 使用默认值 `ellectric/models/` / `ellectric/data/` |
| 15 | pipeline 模块导入失败（依赖缺失等） | `ImportError` 自然传播，不做静默捕获 |

## 非目标

- 不做任何日志（pipeline 模块自带 logger，handler 不额外写日志）
- 不做缓存（每次调用实时加载模型和数据）
- 不做性能优化（模型加载/数据读取在每次调用时执行）
- 不做异步（handler 同步，FastAPI 通过线程池处理）
- 不修改 `ellectric/pipeline/` 下任何文件

## 导入原则

handler 只管 import 和调用，零改动 pipeline 模块。所有 pipeline 导入都在函数内部（延迟导入），不放在模块顶部，以支持只导入 handlers.py 但不触发 pipeline 依赖加载。

## TDD 步骤

| 步骤 | 操作 | 期望 |
|------|------|------|
| 1 | 创建 `service/__init__.py` 空文件 | 包可导入 |
| 2 | 创建 `service/handlers.py`，编写最小 `run_forecast`（只做 model_type 校验） | `ValueError` 正确抛出 |
| 3 | 添加 `run_forecast` load 分支：mock 模型加载和数据加载 | 返回 `ForecastResponse` |
| 4 | 添加 `run_forecast` price 分支 | 类似验证 |
| 5 | 添加 `run_simulate`：mock subprocess | 验证场景映射、错误处理和 CSV 解析 |
| 6 | 添加 `run_backtest`：mock BacktestRunner | 验证日期校验、策略分类、RL vs baseline |
| 7 | 添加 `run_explain`：mock SHAP 调用 | 验证 waterfall_json 序列化和特征重要性输出 |
| 8 | 全函数验收：`python -c "from ellectric.service.handlers import run_forecast, run_simulate, run_backtest, run_explain; print('ok')"` | 导入无错误 |

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| 1 | `python -c "from ellectric.service.handlers import run_forecast, run_simulate, run_backtest, run_explain; print('ok')"` | 输出 "ok" |
| 2 | Python REPL 中 `run_forecast(ForecastRequest(model_type="invalid", horizon=24))` | `ValueError` 包含 "load" 和 "price" |
| 3 | Python REPL 中 `run_explain(ExplainRequest(model_type="invalid"))` | `ValueError` 包含 "xgboost" 和 "lear" |
| 4 | Python REPL 中 `run_simulate(SimulateRequest(config="nonexistent"))` | `ValueError` 包含可选场景 |
| 5 | Python REPL 中 `run_backtest(BacktestRequest(start_date="01-01-2022", end_date="2022-02-01", strategy="oracle"))` | `ValueError` 指明日期格式 |
| 6 | Python REPL 中 `run_backtest(BacktestRequest(start=date(2022,1,1), end=date(2022,2,1), strategy="ppo"))` | `ValueError` 要求 `model_path` |
| 7 | Python REPL 中 `run_backtest(BacktestRequest(start=date(2022,1,1), end=date(2022,2,1), strategy="oracle"))` | **不**报错（基线策略不需要 model_path） |
| 8 | `git diff --stat ellectric/pipeline/` | 无输出（pipeline 零改动） |
