---
author: lmr
created_at: 2026-06-07 23:55:29
id: task-04
title: FastAPI 服务
priority: P0
estimated_hours: 2
depends_on: [task-03]
blocks: [task-06]
allowed_paths:
  - ellectric/api/__init__.py
  - ellectric/api/server.py
---

# task-04: FastAPI 服务

## 修改文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **新增** | `ellectric/api/__init__.py` | 包标记 |
| **新增** | `ellectric/api/server.py` | FastAPI app + 4 路由 |

> 父目录 `ellectric/api/` 不存在，需先创建。

## 实现要求

### R1: 包标记

`ellectric/api/__init__.py` 为空文件。

### R2: FastAPI app 初始化

```python
from fastapi import FastAPI

app = FastAPI(
    title="Ellectric API",
    description="AI+电力交易技术学习平台 — Phase 4 Integration & LLM Interface",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

### R3: 4 个 POST 路由

每个路由：
- 接收对应的 Pydantic Request model 作为请求体
- 注入对应的 handler 函数作为业务逻辑
- 声明 `response_model` 为对应的 Response model
- FastAPI 自动完成请求体验证（422）和响应序列化

```python
from fastapi import FastAPI
from ellectric.service.schemas import (
    ForecastRequest, ForecastResponse,
    SimulateRequest, SimulateResponse,
    BacktestRequest, BacktestResponse,
    ExplainRequest, ExplainResponse,
)
from ellectric.service.handlers import (
    run_forecast, run_simulate, run_backtest, run_explain,
)

app = FastAPI(title="Ellectric API", version="0.1.0")

@app.post("/predict", response_model=ForecastResponse)
def predict(req: ForecastRequest):
    return run_forecast(req)

@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    return run_simulate(req)

@app.post("/backtest", response_model=BacktestResponse)
def backtest(req: BacktestRequest):
    return run_backtest(req)

@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    return run_explain(req)
```

### R4: 健康检查端点（可选但推荐）

```python
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
```

便于 task-06 和 task-07 (LLM tools 通过 httpx 调 API) 快速验证服务可用性。

### R5: 模块 docstring

遵循 CONVENTIONS.md §1.1，文件以 `"""..."""` 模块级 docstring 开头：
- 中文标题 + `=====` 下划线
- `~~~~` 分隔段落
- 架构层次描述（API 层 → Service 层 → Pipeline 层）
- 启动命令示例

### R6: uvicorn 启动方式

```bash
uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000
```

### R7: 错误处理边界（继承 FastAPI 默认行为）

| 场景 | 行为 | 实现方式 |
|------|------|---------|
| 不存在的端点 (如 `POST /unknown`) | 404 `{"detail":"Not Found"}` | FastAPI 默认 |
| 请求体 JSON 格式错误 | 422 `{"detail":[...]}`，指出非法字段和原因 | FastAPI + Pydantic 自动 |
| 请求体缺少必填字段 | 422 `{"detail":[{"loc":["body","model_type"],"msg":"field required"}]}` | FastAPI + Pydantic 自动 |
| handler 抛出 `NotImplementedError` | 500 `{"detail":"Not Implemented"}` | FastAPI 默认异常处理 |
| handler 抛出 `FileNotFoundError` | 500 `{"detail":"...模型文件未找到..."}` | FastAPI 默认异常处理 |
| handler 抛出 `ValueError` (校验逻辑) | 500 `{"detail":"ValueError: ..."}` | FastAPI 默认异常处理 |

不自定义异常处理中间件 —— 保持 FastAPI 默认行为最大透明度和可调试性。

## 边界处理（必填）

| # | 边界场景 | 处理方式 |
|---|---------|---------|
| 1 | handler import 失败（如 `handlers.py` 未完成） | Python 启动时报 `ImportError`，uvicorn 拒绝启动。符合预期——task-03 依赖在 task-04 执行前必须已完成 |
| 2 | schema import 失败 | 同上——task-02 的 schemas 必须先完成 |
| 3 | 传入非预期的 HTTP 方法（如 `GET /predict`） | FastAPI 返回 405 Method Not Allowed，带 `Allow: POST` 头 |
| 4 | CPU 密集型 handler 阻塞 event loop | 当前所有 handler 为同步函数，FastAPI 在同步端点中在线程池运行，不影响其他请求排队。单机学习平台场景足够 |
| 5 | 请求参数包含额外未定义字段（如 `{"model_type":"load","extra_field":1}`） | Pydantic v2 默认忽略 extra fields，不报错。如需严格校验可加 `model_config = {"extra": "forbid"}`，但设计不添加——兼容未来扩展现有 endpoint |
| 6 | Swagger `/docs` 在 `--port 8000` 已被占用时 | uvicorn 启动失败，端口占用错误。`lsof -ti:8000 | xargs kill` 后重试 |
| 7 | handler 返回 None（意外情况） | FastAPI 无法序列化 None → 500 `"Response model validation error"`。当前 handler 签名明确返回 Response model |
| 8 | uvicorn 热重载（开发模式） | 支持 `uvicorn ellectric.api.server:app --reload`，但非默认。在 task-06 验证中不使用 `--reload` |

## 非目标（本任务不做的事）

- ❌ 不自定义异常处理中间件 (exception handlers)
- ❌ 不添加 CORS 中间件（单机学习平台，无需跨域）
- ❌ 不添加认证/授权中间件（学习平台，不需要）
- ❌ 不实现请求日志中间件（uvicorn 默认日志已够用）
- ❌ 不添加 rate limiting（无并发场景）
- ❌ 不使用 `BackgroundTasks` 做异步执行（同步 handler 足够，且仿真/回测应为阻塞式）
- ❌ 不实现任何缓存层（每次调用重新执行预测/仿真）
- ❌ 不写 WebSocket 端点（ROADMAP 未要求实时推送）

## TDD 步骤

```
1. [创建] 创建 ellectric/api/__init__.py + ellectric/api/server.py
   → verify: python -c "from ellectric.api.server import app; print(app.title)" 输出 "Ellectric API"

2. [安装依赖] pip install fastapi uvicorn httpx
   → verify: 无报错

3. [启动服务] uvicorn ellectric.api.server:app --port 8000 &
   → verify: 等待 "Uvicorn running on" 日志出现（最多 5 秒）

4. [测试端点-预测] curl -s -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"model_type":"load","horizon":24}' \
     -o /dev/null -w "%{http_code}"
   → verify: 返回 200

5. [测试端点-仿真] curl -s -X POST http://localhost:8000/simulate \
     -H "Content-Type: application/json" \
     -d '{"config":"default","days":3}' \
     -o /dev/null -w "%{http_code}"
   → verify: 返回 200

6. [测试端点-回测] curl -s -X POST http://localhost:8000/backtest \
     -H "Content-Type: application/json" \
     -d '{"start_date":"2022-08-01","end_date":"2022-08-07","strategy":"oracle"}' \
     -o /dev/null -w "%{http_code}"
   → verify: 返回 200

7. [测试端点-可解释性] curl -s -X POST http://localhost:8000/explain \
     -H "Content-Type: application/json" \
     -d '{"model_type":"xgboost","sample_index":0}' \
     -o /dev/null -w "%{http_code}"
   → verify: 返回 200

8. [验证 422 - 非法枚举] curl -s -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"model_type":"wind","horizon":24}' \
     -o /dev/null -w "%{http_code}"
   → verify: 返回 422
   → verify: body 包含 "Input should be 'load' or 'price'"

9. [验证 422 - 缺失必填字段] curl -s -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{}' \
     -o /dev/null -w "%{http_code}"
   → verify: 返回 422
   → verify: body 包含 "field required"

10. [验证 422 - 类型错误] curl -s -X POST http://localhost:8000/predict \
      -H "Content-Type: application/json" \
      -d '{"model_type":"load","horizon":"not-a-number"}' \
      -o /dev/null -w "%{http_code}"
    → verify: 返回 422
    → verify: body 包含 "Input should be a valid integer"

11. [验证 404] curl -s -X POST http://localhost:8000/unknown \
      -o /dev/null -w "%{http_code}"
    → verify: 返回 404

12. [验证 405 - 错误 HTTP 方法] curl -s -X GET http://localhost:8000/predict \
      -o /dev/null -w "%{http_code}"
    → verify: 返回 405

13. [验证 Swagger UI] curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
    → verify: 返回 200
    → verify: 响应 HTML 包含 "swagger" 或 "openapi"

14. [验证 OpenAPI JSON] curl -s http://localhost:8000/openapi.json | python -c "import json,sys; spec=json.load(sys.stdin); print('paths:',len(spec.get('paths',{})))"
    → verify: 至少输出 "paths: 5" (4 POST + 1 GET health，或 4 POST 无健康检查)

15. [清理] kill %1 2>/dev/null || kill $(lsof -ti:8000) 2>/dev/null
    → verify: lsof -ti:8000 无输出
```

> 步骤 4-7 的 handler 内部可抛 `NotImplementedError`（task-03 stub 状态）。本 task 验证的是 **FastAPI 路由层** 正确性：启动不报错、路由注册正确、请求体校验到 422、响应序列化到 200、错误处理到 404/405。handler 内部逻辑正确性由 task-06 验证。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `python -c "from ellectric.api.server import app; print(app.title)"` | 输出 `Ellectric API` |
| AC-02 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"model_type":"load","horizon":24}'` | 返回 `200` |
| AC-03 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/simulate -H "Content-Type: application/json" -d '{"config":"default","days":3}'` | 返回 `200` |
| AC-04 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/backtest -H "Content-Type: application/json" -d '{"start_date":"2022-08-01","end_date":"2022-08-07","strategy":"oracle"}'` | 返回 `200` |
| AC-05 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/explain -H "Content-Type: application/json" -d '{"model_type":"xgboost","sample_index":0}'` | 返回 `200` |
| AC-06 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"model_type":"wind","horizon":24}'` | 返回 `422` |
| AC-07 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{}'` | 返回 `422` |
| AC-08 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/unknown -H "Content-Type: application/json" -d '{}'` | 返回 `404` |
| AC-09 | `curl -s -o /dev/null -w "%{http_code}" -X GET http://localhost:8000/predict` | 返回 `405` |
| AC-10 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs` | 返回 `200` |
| AC-11 | `curl -s http://localhost:8000/openapi.json | python -c "import json,sys; spec=json.load(sys.stdin); paths=spec.get('paths',{}); assert '/predict' in paths; assert '/simulate' in paths; assert '/backtest' in paths; assert '/explain' in paths; print('OK:', list(paths.keys()))"` | 输出包含 `OK:` 和至少 `['/predict', '/simulate', '/backtest', '/explain']` |
| AC-12 | TDD step 15: `kill %1; lsof -ti:8000` | 端口 8000 已释放，无残留进程 |
