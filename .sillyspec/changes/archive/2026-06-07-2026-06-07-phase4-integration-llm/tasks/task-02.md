---
id: task-02
title: Pydantic Schemas
priority: P0
estimated_hours: 2
depends_on: [task-01]
blocks: [task-03]
allowed_paths:
  - ellectric/service/schemas.py
---

# Task 02: Pydantic 请求/响应 Schemas

## 背景

Phase 4 的 service 层统一数据验证入口。4 对 request/response Pydantic model 定义 API 契约，被 handler (`task-03`)、FastAPI (`task-04`)、CLI (`task-05`)、LLM tools (`task-07`) 共用。

全部模型定义在单文件 `ellectric/service/schemas.py` 中，含 Literal 枚举校验、字段默认值、自定义验证器。

## 修改文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **新增** | `ellectric/service/schemas.py` | 新建 service 包；包含 ~10 个 Pydantic model 类 |

> 父目录 `ellectric/service/` 不存在，需先创建。`ellectric/__init__.py` 已存在（顶层包标记），无需修改。

## 实现要求

### R1: 模块 docstring

遵循 CONVENTIONS.md §1.1，文件以 `"""..."""` 模块级 docstring 开头：
- 中文标题 + `=====` 下划线
- `~~~~` 分隔段落
- 列出 4 组 schema 的架构概述
- 设计决策：为什么用 Pydantic v2 (pydantic-core Rust 后端, FastAPI 原生集成, 5-50x 更快)

### R2: Pydantic v2 语法

使用 pydantic v2 API (`model_validator`, `field_validator`, `model_config`) 而非 v1 兼容写法。项目环境使用 pydantic 2.13.4 (见 STACK.md)。

### R3: 完整类型标注

所有字段使用 Python 3.10+ 原生类型标注 (`str | None`, `list[float]`, `dict[str, float]` 等) 结合 Pydantic `Field()` 默认值和描述。

### R4: @field_validator 自定义校验

相关字段使用 `@field_validator` 或 `@model_validator` 做自定义校验逻辑。

### R5: 可序列化

所有 response model 可通过 `.model_dump()` 转为纯 dict（JSON 可序列化），用于 FastAPI Response 和 CLI 终端输出。

## 接口定义

以下 4 组 schema 严格遵循 design.md §7.1 的定义。每组包含请求体、响应体及任何子模型。

### 1. 预测 (Forecast)

#### ForecastRequest

```python
from pydantic import BaseModel, Field
from typing import Literal

class ForecastRequest(BaseModel):
    model_type: Literal["load", "price"]
    horizon: int = Field(default=24, ge=1, le=168,
                         description="预测时长，单位：小时")
    data_source: str = Field(default="owid",
                             description="数据源标识 (owid / chinese_hourly)")
```

- `model_type`: `"load"` 调用 `forecaster.py` (XGBoost 负荷预测); `"price"` 调用 `price_forecaster.py` (LEAR 电价预测)
- `horizon`: 1-168 小时 (1 周)。默认 24 对应日前预测
- `data_source`: 透传给 DataLoader 工厂

#### ForecastMetrics (子模型)

```python
class ForecastMetrics(BaseModel):
    mae: float | None = Field(default=None, description="Mean Absolute Error")
    rmse: float | None = Field(default=None, description="Root Mean Squared Error")
    mape: float | None = Field(default=None, description="Mean Absolute Percentage Error (%)")
```

> 指标可为 None：仅在有 ground truth 的回溯 (backtest) 场景下填充；新数据纯推理场景下为 None。

#### ForecastResponse

```python
from datetime import datetime

class ForecastResponse(BaseModel):
    timestamps: list[datetime]  = Field(description="预测时间戳序列 (UTC)")
    predictions: list[float]    = Field(description="预测值序列 (MW 或 元/MWh)")
    metrics: ForecastMetrics    = Field(description="预测误差指标 (回溯场景)")
```

- `timestamps` 和 `predictions` 长度必须相等 → 用 `@model_validator(mode="after")` 校验

### 2. 仿真 (Simulate)

#### SimulateRequest

```python
class SimulateRequest(BaseModel):
    config: Literal["default", "summer_peak", "wind_high"] = Field(
        description="预设场景: default=基准, summer_peak=夏季高峰, wind_high=高风电占比"
    )
    days: int = Field(default=7, ge=1, le=30,
                      description="仿真天数")
```

#### SimulateResponse

```python
class SimulateResponse(BaseModel):
    status: str = Field(description="execution status: success | error")
    clearing_prices: list[float] = Field(default_factory=list,
                                         description="出清电价序列 (元/MWh)")
    dispatch: list[dict] = Field(default_factory=list,
                                 description="各单元调度结果 [{unit, power_mw, cost}, ...]")
    agent_profits: dict[str, float] = Field(default_factory=dict,
                                            description="各代理利润 (元)")
    output_dir: str = Field(default="", description="仿真输出目录路径")
    error_message: str | None = Field(default=None,
                                      description="错误信息 (status=error 时)")
```

### 3. 回测 (Backtest)

#### BacktestRequest

```python
from datetime import date

class BacktestRequest(BaseModel):
    start_date: date
    end_date: date
    strategy: Literal[
        "baseline_persistence",
        "baseline_mean",
        "oracle",
        "ppo",
        "sac",
        "td3",
    ] = Field(description="交易策略")
    model_path: str | None = Field(default=None,
                                   description="RL 模型权重路径 (strategy=ppo|sac|td3 时必填)")
    data_source: str = Field(default="owid")
```

- `start_date > end_date` → `@model_validator(mode="after")` 抛出 `ValueError`
- `strategy` in `("ppo", "sac", "td3")` 时 `model_path` 不能为 None → `@model_validator` 校验

#### BacktestResponse

```python
class BacktestResponse(BaseModel):
    status: str = Field(description="execution status: success | error")
    cumulative_pnl: list[float] = Field(default_factory=list,
                                        description="累计盈亏序列 (元)")
    sharpe_ratio: float | None = Field(default=None,
                                       description="夏普比率")
    comparison: dict[str, float] = Field(default_factory=dict,
                                         description="多策略指标对比 {strategy_name: final_pnl}")
    plot_data: dict | None = Field(default=None,
                                   description="Plotly JSON (可选, 前端渲染)")
    error_message: str | None = Field(default=None)
```

### 4. 可解释性 (Explain)

#### ExplainRequest

```python
class ExplainRequest(BaseModel):
    model_type: Literal["xgboost", "lear"] = Field(
        description="模型类型: xgboost=负荷预测, lear=电价预测"
    )
    sample_index: int = Field(default=0, ge=0,
                              description="要解释的样本在测试集中的索引")
    max_display: int = Field(default=10, ge=1, le=50,
                             description="最多显示的特征数")
```

#### FeatureImportance (子模型)

```python
class FeatureImportance(BaseModel):
    name: str        = Field(description="特征名称")
    importance: float = Field(description="重要性数值 (SHAP 或 gain)")
    rank: int        = Field(description="排名 (1-based)")
```

#### ExplainResponse

```python
class ExplainResponse(BaseModel):
    status: str = Field(description="execution status: success | error")
    feature_importance: list[FeatureImportance] = Field(
        default_factory=list,
        description="特征重要性列表，按 rank 升序"
    )
    waterfall_json: dict | None = Field(
        default=None,
        description="SHAP waterfall Plotly JSON (可选)"
    )
    error_message: str | None = Field(default=None)
```

## 边界处理

| # | 边界条件 | 处理方式 |
|---|---------|---------|
| 1 | `model_type` 传入不在 Literal 中的值 (如 `"wind"`) | Pydantic Literal 自动校验 → `ValidationError: "Input should be 'load' or 'price'"` |
| 2 | `horizon` 传入 0 或负数 | `Field(ge=1)` → `ValidationError: "Input should be greater than or equal to 1"` |
| 3 | `horizon` 传入超过 168 | `Field(le=168)` → `ValidationError: "Input should be less than or equal to 168"` |
| 4 | `ForecastResponse.timestamps` 和 `predictions` 长度不一致 | `@model_validator(mode="after")` 校验 → `ValueError("timestamps and predictions must have same length")` |
| 5 | `config` 传入未注册场景 (如 `"winter_low"`) | Pydantic Literal 自动校验 → `ValidationError` |
| 6 | `days` 传入 0 或 >30 | `Field(ge=1, le=30)` → `ValidationError` |
| 7 | `start_date > end_date` | `@model_validator(mode="after")` → `ValueError("start_date must be before or equal to end_date")` |
| 8 | `strategy` ∈ `{"ppo","sac","td3"}` 但 `model_path=None` | `@model_validator(mode="after")` → `ValueError("model_path is required for RL strategies")` |
| 9 | `start_date` 使用 str 而非 `datetime.date` | Pydantic 自动将 ISO str → `date` 转换；格式错误则 `ValidationError` |
| 10 | `sample_index` 传入负数 | `Field(ge=0)` → `ValidationError` |
| 11 | `max_display` 传入 0 或 >50 | `Field(ge=1, le=50)` → `ValidationError` |
| 12 | Response model 字段缺失默认值 (如 `cumulative_pnl` 未传) | `default_factory=list` 保证始终输出 `[]` 而非报错 |

## 非目标

- ❌ 不定义数据库 ORM 模型 (本项目无持久化需求)
- ❌ 不创建 `response_model` FastAPI 路由装饰器逻辑 (属于 task-04)
- ❌ 不在 schemas.py 中 import `ellectric.pipeline.*` (schema 层只做结构定义)
- ❌ 不使用 pydantic v1 兼容 API (`@validator`, `class Config`)
- ❌ 不为可选 LLM 模块 (task-07~10) 定义专用 schema；LLM tools 内部调用 FastAPI 时复用 ForecastRequest 等
- ❌ 不添加 `to_dataframe()` / `from_dataframe()` 转换方法 (handler 层负责)

## TDD 步骤

本 task 为纯数据结构定义（无外部依赖、无 I/O、无副作用）。"测试" 具体指 Pydantic 模型可实例化 + 校验行为正确。

```
1. [设计] 确认 design.md §7.1 所有字段、类型、默认值与 plan.md task-02 一致
   → verify: 字段列表与 design.md §7.1 逐行对照通过

2. [编码] 创建 ellectric/service/schemas.py，写入 ~10 个 model 类
   → verify: python -c "from ellectric.service.schemas import *" 无 ImportError

3. [校验-实例化] 每个 Request model 用合法参数实例化
   → verify: 不抛 ValidationError, .model_dump() 返回预期 dict

4. [校验-默认值] 用最少参数实例化 (仅必填字段)，验证默认值生效
   → verify: ForecastRequest(model_type="load").horizon == 24

5. [校验-Literal] 每个 Literal 字段用非法值实例化
   → verify: 抛出 ValidationError，错误信息包含合法选项

6. [校验-Validator] 触发跨字段检验器
   → verify: start_date > end_date → ValueError
   → verify: strategy=ppo + model_path=None → ValueError
   → verify: timestamps + predictions 长度不匹配 → ValueError

7. [校验-响应默认值] Response model 的 list/dict 字段不传值
   → verify: cumulative_pnl 为 [] (default_factory=list 生效)

8. [校验-可选字段] None 字段序列化后不出现在 .model_dump() 返回 dict 中 (Pydantic v2 default)
   → verify: BacktestResponse(status="success").model_dump() 不含 sharpe_ratio key
```

## 验收标准

| # | 验收项 | 通过条件 |
|---|--------|---------|
| AC-01 | 模块可导入 | `python -c "from ellectric.service.schemas import ForecastRequest; print(ForecastRequest)"` 打印类名，不报错 |
| AC-02 | 10 个 model 类全部定义 | `dir(schemas)` 包含: `ForecastRequest`, `ForecastMetrics`, `ForecastResponse`, `SimulateRequest`, `SimulateResponse`, `BacktestRequest`, `BacktestResponse`, `ExplainRequest`, `FeatureImportance`, `ExplainResponse` |
| AC-03 | Literal 枚举校验正确 | `ForecastRequest(model_type="wind", horizon=24)` → `ValidationError` 且错误消息含 `'load'` 和 `'price'` |
| AC-04 | Field 范围校验正确 | `ForecastRequest(model_type="load", horizon=0)` → `ValidationError` (ge=1) |
| AC-05 | Field 范围上限校验 | `SimulateRequest(config="default", days=31)` → `ValidationError` (le=30) |
| AC-06 | 跨字段校验生效 (日期) | `BacktestRequest(start_date=date(2022,8,31), end_date=date(2022,8,1), strategy="oracle")` → `ValidationError` |
| AC-07 | 跨字段校验生效 (model_path) | `BacktestRequest(start_date=date(2022,7,1), end_date=date(2022,7,7), strategy="ppo")` → `ValidationError` (model_path required) |
| AC-08 | 默认值正确 | `ForecastRequest(model_type="price").model_dump()` = `{'model_type': 'price', 'horizon': 24, 'data_source': 'owid'}` |
| AC-09 | Response 默认 factory 生效 | `SimulateResponse(status="success").clearing_prices` = `[]`, `agent_profits` = `{}` |
| AC-10 | 模块 docstring 符合规范 | docstring 包含中文标题、`=====`、`~~~~`、ASCII 架构图、设计决策 |
| AC-11 | 可选字段序列化行为 | `BacktestResponse(status="success").model_dump()` 返回 dict 中 `sharpe_ratio` 和 `plot_data` 不出现 (exclude_none 或默认 Pydantic v2 行为) |

> **AC-01 是 design.md §11.5 Wave 1 验证的直接体现。**
