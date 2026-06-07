---
author: lmr
created_at: 2026-06-07T23:00:00+08:00
---

# Design: Phase 4 — Integration + LLM Interface

## 1. 背景

Phases 1-3 已实现完整技术闭环：数据管道 → 负荷/电价预测 → 市场仿真 → RL 交易智能体 → 回测 → 可解释性。但所有功能只能通过 Jupyter Notebook 或独立脚本逐模块调用，没有一个统一的对外接口。

Phase 4 的目标是将这些能力包装为 **REST API + CLI 命令行 + 自然语言助手**，使学习者能通过三种方式触及全平台功能。

## 2. 设计目标

- 提供 FastAPI REST API (`/predict`, `/simulate`, `/backtest`, `/explain`)
- 提供 CLI 命令行工具 (`el-cli forecast|simulate|backtest|explain`)
- 提供 LLM 自然语言交易助手 (LangChain + DeepSeek API)
- **零改动 pipeline 层** — 所有已有模块代码不变
- 覆盖 ROADMAP Phase 4 全部 5 条成功标准

## 3. 非目标

- 不做 Web UI 前端
- 不做用户认证/权限系统
- 不做实时数据流 (WebSocket)
- 不做生产级部署（systemd/docker）
- 不做多用户并发
- 不做拖拽式图形投标界面
- MLflow 作为可选项，不在 MVP 范围内

## 4. 拆分判断

不拆分。理由：3 个模块（API/CLI/LLM）共享 service 层，紧密集成。预估 8-10 个 task，分 3 Wave 完成。无重复模式，不触发批量模式。

## 5. 总体方案

### 架构层次

```
┌────────────────────────────────────────────┐
│  入口层                                      │
│  CLI (typer)    FastAPI(uvicorn)   LLM Agent │
│  el-cli cmd     :8000/docs         终端对话   │
└────────┬─────────────┬──────────────┬───────┘
         │             │              │
         │  import     │  import      │  HTTP
         ▼             ▼              ▼
┌────────────────────────────────────────────┐
│  Service 层  ← 新增                        │
│  schemas.py  (Pydantic 请求/响应模型)        │
│  handlers.py (run_forecast/simulate/bt)     │
└──────────────────┬─────────────────────────┘
                   │ import (零改动)
                   ▼
┌────────────────────────────────────────────┐
│  Pipeline 层  ← 已有，不改                  │
│  forecaster / price_forecaster /           │
│  backtester / shap_explainer /             │
│  assume/run_simulation                     │
└────────────────────────────────────────────┘
```

### 数据流

```
CLI 命令 → service/handlers → pipeline 模块 → 结果 → 终端输出
HTTP 请求 → FastAPI route → service/handlers → pipeline 模块 → JSON 响应
自然语言 → LangChain Agent → tool call → FastAPI HTTP → service → pipeline → 回复
```

### Wave 分组

| Wave | 产出 | 验证方式 |
|------|------|---------|
| Wave 1 | service/ + requirements-phase4.txt | import 通过，schemas 可实例化 |
| Wave 2 | API(api/) + CLI(cli/) | `uvicorn` 启动成功，`el-cli forecast load 24` 跑通 |
| Wave 3 | LLM(llm/) | `el-cli ask "预测负荷"` 返回有效结果 |

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **新增** | `ellectric/service/__init__.py` | 包标记 |
| **新增** | `ellectric/service/schemas.py` | 4 对 Pydantic 请求/响应模型 |
| **新增** | `ellectric/service/handlers.py` | 4 个业务函数 |
| **新增** | `ellectric/api/__init__.py` | 包标记 |
| **新增** | `ellectric/api/server.py` | FastAPI app + 4 路由 |
| **新增** | `ellectric/cli/__init__.py` | 包标记 |
| **新增** | `ellectric/cli/main.py` | typer CLI app (4 命令) |
| **新增** | `ellectric/llm/__init__.py` | 包标记 |
| **新增** | `ellectric/llm/tools.py` | LangChain tools (3 个) |
| **新增** | `ellectric/llm/agent.py` | LangChain agent 初始化 |
| **新增** | `ellectric/llm/chat.py` | 交互式对话入口 |
| **新增** | `ellectric/requirements-phase4.txt` | Phase 4 新增依赖 (7 packages) |
| **修改** | `ellectric/requirements.txt` | 追加 Phase 4 依赖引用 |

> 所有已有 pipeline/ 文件不做任何修改。

## 7. 接口定义

### 7.1 Pydantic Schemas (schemas.py)

```python
# ── 预测 ──
class ForecastRequest:
    model_type: Literal["load", "price"]
    horizon: int = 24          # 预测时长 (小时)
    data_source: str = "owid"  # 数据源

class ForecastResponse:
    timestamps: list[datetime]
    predictions: list[float]
    metrics: ForecastMetrics

class ForecastMetrics:
    mae: float | None
    rmse: float | None
    mape: float | None

# ── 仿真 ──
class SimulateRequest:
    config: Literal["default", "summer_peak", "wind_high"]
    days: int = 7

class SimulateResponse:
    status: str                # "success" | "error"
    clearing_prices: list[float]
    dispatch: list[dict]
    agent_profits: dict[str, float]
    output_dir: str

# ── 回测 ──
class BacktestRequest:
    start_date: date
    end_date: date
    strategy: Literal["baseline_persistence", "baseline_mean", "oracle", "ppo", "sac", "td3"]
    model_path: str | None = None  # RL 模型需要
    data_source: str = "owid"

class BacktestResponse:
    status: str
    cumulative_pnl: list[float]
    sharpe_ratio: float | None
    comparison: dict[str, float]  # 多策略对比
    plot_data: dict | None        # Plotly JSON (可选)

# ── 可解释性 ──
class ExplainRequest:
    model_type: Literal["xgboost", "lear"]
    sample_index: int = 0
    max_display: int = 10

class FeatureImportance:
    name: str
    importance: float
    rank: int

class ExplainResponse:
    status: str
    feature_importance: list[FeatureImportance]
    waterfall_json: dict | None  # Plotly JSON
```

### 7.2 Handler 函数签名 (handlers.py)

```python
def run_forecast(req: ForecastRequest) -> ForecastResponse
def run_simulate(req: SimulateRequest) -> SimulateResponse
def run_backtest(req: BacktestRequest) -> BacktestResponse
def run_explain(req: ExplainRequest) -> ExplainResponse
```

### 7.3 FastAPI 路由 (server.py)

```python
app = FastAPI(title="Ellectric API", version="0.1.0")

POST /predict  → ForecastRequest → ForecastResponse
POST /simulate → SimulateRequest → SimulateResponse
POST /backtest → BacktestRequest → BacktestResponse
POST /explain  → ExplainRequest  → ExplainResponse
```

### 7.4 CLI 命令 (cli/main.py)

```bash
el-cli forecast  <MODEL> <HORIZON>              # load|price, 24
el-cli simulate  <SCENARIO> [--days N]           # default|summer_peak|wind_high
el-cli backtest  <START> <END> <STRATEGY>        # YYYY-MM-DD dates
el-cli explain   <MODEL> <SAMPLE>                # xgboost|lear
el-cli ask        "<自然语言问题>"                # LLM 单次查询 (Wave 3)
```

### 7.5 LLM Tools (llm/tools.py)

```python
@tool
def query_forecast(model_type: str, horizon: int) -> str
    """查询负荷或电价预测结果"""

@tool
def run_simulation(scenario: str, days: int) -> str
    """运行电力市场仿真"""

@tool
def run_backtest(start_date: str, end_date: str, strategy: str) -> str
    """运行历史回测"""
```

每个 tool 内部通过 `httpx` POST 调用本机 FastAPI (`http://localhost:8000`).

## 8. 数据模型

无数据库表变更。本阶段不引入持久化存储（TimescaleDB 已在 Phase 2 预留但未激活）。

新增数据结构仅为上述 Pydantic schemas（运行时 JSON 序列化，不持久化）。

## 9. 兼容策略

### 9.1 Brownfield 保证

| 保证项 | 说明 |
|--------|------|
| pipeline 零改动 | `ellectric/pipeline/` 下 14 个模块文件不做任何修改 |
| assume 零改动 | `ellectric/assume/` 下脚本和配置不变 |
| notebooks 零改动 | 11 个 Jupyter notebook 继续可用 |
| 导入路径不变 | 已有 `from ellectric.pipeline.xxx import yyy` 全部有效 |
| 回退路径 | Phase 4 文件全部在新增目录中，删除 `service/` `api/` `cli/` `llm/` 即可完全回退 |

### 9.2 不改变的接口

- `DataLoader.load_data(start, end)` → 保持
- `XGBoostForecaster.train_evaluate(X, y)` → 保持
- `LEARForecaster.train_evaluate(df, tier)` → 保持
- `BacktestRunner.replay(model, ...)` → 保持
- `assume/run_simulation.py --config` → 保持

### 9.3 新增依赖不冲突

Phase 4 新增依赖 (FastAPI, typer, langchain, langchain-openai, chromadb, httpx, uvicorn) 与 Phase 1-3 已有依赖无已知冲突。

## 10. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|---------|
| R-01 | DeepSeek API 不能访问（GFW/网络限制） | P1 | LLM 模块可选启动；API/CLI 不依赖 LLM，独立可用 |
| R-02 | ASSUME 仿真无法通过 Python API 调用（当前仅 CLI） | P1 | handler 通过 subprocess 调 `run_simulation.py`，无需 Python API |
| R-03 | 模型文件路径硬编码导致不同环境运行失败 | P2 | handler 使用可配置环境变量 `ELLECTRIC_MODEL_DIR`，默认 `ellectric/models/` |
| R-04 | Pydantic v2 与 langchain v1.x 版本冲突 | P2 | 版本 pin 明确写入 requirements-phase4.txt |
| R-05 | 无 CI/CD 测试覆盖，回归风险 | P2 | MVP 阶段手动验证；不阻塞交付 |
| R-06 | CLI 和 API 行为不一致（service 层 bug） | P2 | 共享 service 层天然降低此风险；手动交叉验证 |

## 11. 自审

### 11.1 需求覆盖检查

对照 ROADMAP Phase 4 5 条成功标准：

| # | 成功标准 | 覆盖 | 实现方式 |
|---|---------|------|---------|
| 1 | `GET /predict?horizon=24h` 返回 JSON | ✅ | `POST /predict` (Pydantic Body 更安全) → ForecastResponse |
| 2 | `ellectric simulate start --scenario summer_peak` | ✅ | `el-cli simulate summer_peak` |
| 3 | `ellectric backtest run --start ... --end ...` | ✅ | `el-cli backtest 2022-08-01 2022-08-31 ppo` |
| 4 | LLM 助手回答 "昨天峰值负荷多少？" | ✅ | agent.py + tools.py → query_forecast |
| 5 | 自然语言交易命令 | ✅ | agent.py 解析自然语言 → run_simulation |

差异说明：ROADMAP 写 `GET /predict?horizon=24h`，设计中改用 `POST /predict`。理由：predict 请求有结构化参数 (model_type, horizon, data_source) 且可能扩展，POST 比 GET 更适合。不影响功能等效性。

### 11.2 约束一致性

- **CONVENTIONS.md**: 新增模块遵循现有模式——模块级 docstring（中文+English）、类型标注、logger 模式、Plotly 可视化
- **ARCHITECTURE.md**: 不改 pipeline 拓扑，在外部新增接入层
- **PROJECT.md**: 全部使用开源工具，Python 3.11+

### 11.3 真实性

- `XGBoostForecaster`, `LEARForecaster`, `BacktestRunner`, `ElectricityMarketEnv` — 全部来自真实现有代码
- `assume/run_simulation.py --config` — 真实 CLI 参数
- 标注"新增"的文件在现有代码库中不存在

### 11.4 YAGNI 检查

| 潜在功能 | 决定 | 理由 |
|---------|------|------|
| MLflow 集成 | 不做 | ROADMAP 未列入成功标准 |
| Web UI 前端 | 不做 | 非目标 |
| 用户认证 | 不做 | 学习平台，不需要 |
| WebSocket 实时推送 | 不做 | 超出 MVP 范围 |
| pyproject.toml | 不做 | sys.path 方案已可工作，不引入无必要变更 |
| grafana embedding 到 API | 不做 | Grafana 已独立可用 |

### 11.5 验收标准

每 Wave 有具体验证：
- Wave 1: `python -c "from ellectric.service.schemas import ForecastRequest; print(ForecastRequest)"` 成功
- Wave 2: `uvicorn` 启动 + `curl` 测试 + `el-cli forecast load 24` 有输出
- Wave 3: `el-cli ask "预测负荷"` 返回有效自然语言

### 11.6 自审结论

✅ 需求覆盖：5/5 成功标准有对应实现
✅ 约束一致：与 CONVENTIONS、ARCHITECTURE、PROJECT 无矛盾
✅ 文件真实：所有引用模块名来自实际代码
✅ YAGNI：未引入不必要的功能
✅ 兼容：pipeline 零改动，回退路径清晰
✅ 风险：6 个风险均有应对策略
✅ 非目标：明确 6 项不做
