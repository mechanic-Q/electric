---
author: lmr
created_at: 2026-07-02 16:55:06
---

# Design: WebUI Data Agent Integration

## 背景

现有 Web Chat UI 已经完成基础对话链路：`ellectric/api/static/index.html` 通过 `POST /chat/stream` 接收 SSE，`ellectric/chat/streaming.py` 调用 LangChain Agent，Agent 经 `ellectric/llm/tools.py` 访问 FastAPI 的 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend`。

当前问题不是“不能聊天”，而是“项目事实没有统一入口”：预测、价格模型对比、Weather Tier4、风光预测、RL 全量评估、回测、SHAP 等结果散落在 API、模型文件和 `ellectric/reports/**` 中。前端也只显示 token 文本和工具状态，不展示 `tool_result` 的结构化内容。模型文件缺失时，实时预测容易直接失败，用户看不到已有离线报告中的可用结论。

本变更把现有 Web Chat UI 升级为“对话 + 数据面板 + 能力目录”的学习平台入口。

## 设计目标

1. 保留现有 FastAPI + 单页 HTML + DeepSeek/LangChain + SSE 架构。
2. 在网页中明确展示“可以问什么”和“有哪些数据/报告可查”。
3. 让 Agent 能读取能力清单、数据集元信息和离线报告。
4. 让工具结果在 AI 气泡内展示摘要，并同步到右侧数据面板。
5. 实时模型或模型文件不可用时，fallback 到最近离线报告，并明确标注来源。
6. 覆盖负荷/电价预测、风光预测、市场仿真、回测、SHAP、交易建议、离线报告、数据集元信息、能力清单。

## 非目标

- 不引入 React/Vite/Streamlit/Gradio 等新前端框架。
- 不做登录、权限、多用户或聊天记录持久化。
- 不做真实交易下单，不连接任何真实交易接口。
- 不重新训练模型，不重新生成已有报告。
- 不把 Grafana/Plotly 全部迁入 WebUI。
- 不改用 WebSocket；继续使用现有 SSE。
- 不改变现有 API 的核心请求/响应语义，只新增只读目录端点和 fallback 字段。

## 拆分判断

本变更不拆分，也不走批量模式。

理由：它是单页面、单角色、单交互流的增量改造。后端目录层、Agent 工具、SSE 协议和前端面板高度耦合，拆成多个变更会增加接口漂移风险。它也不是“模板 × 大量实例”的批量开发场景；报告和数据集数量有限，可以用固定 registry + 目录扫描组合实现。

## 总体方案

### Wave 1: 数据目录层

新增轻量 catalog/registry 服务，统一描述三类事实：

- capabilities：可问问题类别、对应 API/tool、示例问题、是否支持离线 fallback。
- datasets：数据源名称、时间范围、字段、频率、来源说明。
- reports：报告 ID、标题、类型、状态、文件路径、摘要指标、HTML/MD/JSON 资产。

registry 优先读取已知稳定报告路径：

- `ellectric/reports/full_real_run/**/SUMMARY.json`
- `ellectric/reports/rl_full_dataset/evaluation_report.json`
- `ellectric/reports/weather_tier4/weather_tier4_validation.json`
- `ellectric/reports/renewable_forecaster/renewable_forecast_validation.json`
- 价格模型对比 JSON/MD 报告，如存在则纳入

缺失报告不报错，返回 `available=false` 或跳过对应条目。

### Wave 2: API 与 fallback

新增只读 API：

- `GET /capabilities`
- `GET /datasets`
- `GET /reports`
- `GET /reports/{report_id:path}`

新 API 路由必须注册在 `app.mount("/")` 静态文件挂载之前，避免被 StaticFiles 捕获。`report_id` 允许使用 `full_real_run/latest` 这类带 `/` 的稳定 ID，因此路由使用 FastAPI path converter。

现有 `/predict` 可保持原响应模型不破坏；fallback 优先在 LLM tool 层处理，必要时 service 层提供辅助函数。实时预测失败且原因是模型缺失或加载失败时，tool 返回结构化 fallback：

```json
{
  "status": "fallback",
  "source": "offline_report",
  "fallback_reason": "model_missing",
  "report_id": "weather_tier4/latest",
  "summary": "Weather Tier4 负荷预测 MAE 下降约 19.24%",
  "metrics": {"mae_delta_pct": -19.24}
}
```

### Wave 3: Agent 工具扩展

在 `ellectric/llm/tools.py` 中新增：

- `query_capabilities()`：返回能力目录。
- `query_datasets()`：返回数据集元信息。
- `query_reports(report_type: str | None = None)`：返回报告列表或摘要。
- `read_report(report_id: str)`：读取指定报告详情。

更新 `ellectric/llm/agent.py`：

- 注册新工具。
- 系统 prompt 明确数据来源规则：优先工具；不编造数字；回答需标注实时 API 或离线报告。
- 扩展能力描述，覆盖电价、风光、天气、RL、报告、数据集。

### Wave 4: SSE 协议修复

统一后端事件字段：

```json
{"type": "tool_call", "name": "query_reports", "args": {"report_type": "price"}}
{"type": "tool_result", "name": "query_reports", "content": "...", "payload": {...}}
{"type": "error", "message": "..."}
{"type": "done"}
```

`payload` 来源于 tool 输出的 JSON 解析结果：如果 `content` 是合法 JSON，后端或前端可将其解析为 payload；如果不是合法 JSON，则 `payload=null`，前端只展示文本摘要。前端兼容旧字段，但以 `name` 为主，不再依赖不存在的 `tool` 或 `tool_id`。`tool_result.content` 必须被展示；如能 parse JSON，则生成指标表/报告卡；无法 parse 时显示文本摘要。

### Wave 5: WebUI 两栏体验

保留 `ellectric/api/static/index.html` 单文件实现。改为响应式布局：

- 左侧：聊天流、用户输入、AI token、工具状态、内嵌结果卡片。
- 右侧：数据面板，默认显示能力清单、数据集、最近报告。
- 移动端：右侧面板折叠或隐藏，结果仍在气泡内展示。

欢迎区增加可问问题分组：

- 预测：负荷、电价、风电、光伏。
- 评估：价格模型对比、Weather Tier4、RL 全量评估。
- 交易：回测、策略对比、交易建议。
- 解释：SHAP、特征重要性。
- 数据：山东数据集、报告目录、字段说明。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/service/catalog.py` | 能力、数据集、报告 registry 与读取函数 |
| 修改 | `ellectric/service/schemas.py` | 新增 Capability/Dataset/Report 相关 Pydantic schema |
| 修改 | `ellectric/service/handlers.py` | 新增 list/get catalog handlers；为预测工具 fallback 提供辅助 |
| 修改 | `ellectric/api/server.py` | 新增 `/capabilities`、`/datasets`、`/reports`、`/reports/{id}` 路由 |
| 修改 | `ellectric/llm/tools.py` | 新增 catalog/report tools；为 forecast tool 增加离线 fallback |
| 修改 | `ellectric/llm/agent.py` | 注册新 tools；更新系统 prompt |
| 修改 | `ellectric/chat/streaming.py` | 统一 SSE tool_call/tool_result/error 字段，支持 payload |
| 修改 | `ellectric/api/static/index.html` | 两栏布局、能力清单、结构化 tool_result 渲染、错误兼容 |
| 新增 | `tests/test_service_catalog.py` | catalog/report/dataset 读取单元测试 |
| 新增 | `tests/test_api_catalog.py` | 新只读端点 smoke 测试 |
| 新增 | `tests/test_chat_streaming_events.py` | SSE 事件字段兼容测试 |
| 修改 | `README.md` | 更新 Web Chat 可问问题和启动说明 |

## 接口定义

### Pydantic schema

```python
class CapabilityItem(BaseModel):
    id: str
    title: str
    category: Literal["forecast", "simulation", "backtest", "explain", "trade", "report", "dataset"]
    description: str
    example_questions: list[str]
    endpoint: str | None = None
    tool_name: str | None = None
    supports_offline_fallback: bool = False
    available: bool = True

class DatasetInfo(BaseModel):
    id: str
    title: str
    description: str
    source: str
    frequency: str | None = None
    rows: int | None = None
    start: str | None = None
    end: str | None = None
    columns: list[str] = Field(default_factory=list)
    available: bool = True

class ReportSummary(BaseModel):
    id: str
    title: str
    report_type: str
    status: Literal["ok", "missing", "error"]
    generated_at: str | None = None
    summary: str
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    paths: dict[str, str] = Field(default_factory=dict)

class ReportDetail(ReportSummary):
    content: dict | str | None = None
```

### Service functions

```python
def list_capabilities() -> list[CapabilityItem]: ...
def list_datasets() -> list[DatasetInfo]: ...
def list_reports(report_type: str | None = None) -> list[ReportSummary]: ...
def get_report(report_id: str) -> ReportDetail: ...
def build_forecast_fallback(model_type: str, error: Exception) -> dict | None: ...
```

### API routes

```python
@app.get("/capabilities") -> list[CapabilityItem]
@app.get("/datasets") -> list[DatasetInfo]
@app.get("/reports") -> list[ReportSummary]
@app.get("/reports/{report_id:path}") -> ReportDetail
```

### LLM tools

```python
@tool
def query_capabilities() -> str: ...

@tool
def query_datasets() -> str: ...

@tool
def query_reports(report_type: str | None = None) -> str: ...

@tool
def read_report(report_id: str) -> str: ...
```

## 数据模型

本变更不新增数据库表，不持久化用户输入，不改变现有报告文件格式。数据模型是内存/文件系统 registry：

- report id 使用稳定字符串，如 `full_real_run/latest`、`rl_full_dataset/evaluation`、`weather_tier4/validation`。
- report paths 仅返回项目内相对路径，避免暴露任意文件系统路径。
- metrics 只提取可安全序列化的标量；复杂数组留在 detail content 中。
- datasets 元信息优先从 loader metadata 或 DataFrame 轻量读取获得；读取失败则返回 available=false。

## 兼容策略

- 未配置 `DEEPSEEK_API_KEY` 时，`/chat/stream` 仍返回现有错误提示；新增端点不依赖 LLM key。
- 现有 `/predict`、`/simulate`、`/backtest`、`/explain`、`/recommend` 路由保留。
- 新 catalog 端点只读，无副作用。
- 报告缺失不导致服务启动失败。
- 前端兼容旧 SSE 字段：读取 `event.name || event.tool || 'TOOL'`，错误读取 `event.message || event.content`。
- 实时模型不可用时，通过 tool fallback 给出离线报告结果；如果报告也缺失，则返回友好错误和可用能力清单。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 报告文件路径和命名不稳定 | P1 | 使用显式 registry + glob fallback；缺失报告返回 missing 而非异常 |
| R-02 | LLM 把离线报告当成实时预测 | P1 | tool 返回 source/fallback_reason；prompt 要求回答标注来源 |
| R-03 | 前端解析大型 JSON 导致页面卡顿 | P2 | 气泡显示摘要，右侧面板截断/折叠详细 content |
| R-04 | `/simulate` 等耗时工具在聊天中阻塞 | P2 | 本变更不改执行模型；UI 显示工具运行状态和错误 |
| R-05 | 新 schema 破坏现有 FastAPI OpenAPI 或测试 | P1 | 新增端点独立 schema；不修改旧 response_model 必填字段 |
| R-06 | 模型缺失 fallback 与原 API 错误语义冲突 | P1 | fallback 优先放在 LLM tool 层，不强行改变 `/predict` 语义 |

## 决策追踪

- D-001@v1 覆盖：展示结构采用对话内嵌 + 右侧数据面板。对应章节：总体方案 Wave 4/5，文件变更 `index.html`、`streaming.py`。
- D-002@v1 覆盖：数据发现采用能力清单 + AI 引导双通道。对应章节：Wave 1/2/3，文件变更 `catalog.py`、`server.py`、`tools.py`。
- D-003@v1 覆盖：实时模型缺失时 fallback 到离线报告。对应章节：Wave 2/3，文件变更 `tools.py`、`handlers.py`。
- D-004@v1 覆盖：本次范围接通全部已有项目能力。对应章节：设计目标、Wave 1-5、接口定义。
- D-005@v1 覆盖：采用方案 B 数据目录与报告层。对应章节：总体方案 Wave 1-5、文件变更清单与接口定义。

## 自审

- 需求覆盖：通过。覆盖用户确认的交互式网页、全部数据能力接通、页面引导、DeepSeek 后端现状和数据连接缺口。
- 决策覆盖：通过。D-001@v1 至 D-005@v1 均被设计章节引用。
- 约束一致性：通过。保留 FastAPI/Pydantic/handler/tool 架构；不引入新前端框架；使用现有报告和 API。
- 真实性：通过。现有文件路径来自代码读取；新增文件/函数已标注为新增。
- YAGNI：通过。排除登录、多用户、真实交易、前端框架重构、模型重训。
- 验收标准：通过。端点、SSE 事件、前端渲染和 fallback 均可测试。
- 非目标：通过。scope creep 已明确。
- 兼容策略：通过。旧 API 保留，新端点只读，缺失报告/模型有 fallback。
- 风险识别：通过。关键技术风险已登记。
- 生命周期契约表：不适用。本文不设计后台长任务租约、守护进程或心跳类工作流；聊天 history 由现有前端内存维护，不新增状态机协议。
