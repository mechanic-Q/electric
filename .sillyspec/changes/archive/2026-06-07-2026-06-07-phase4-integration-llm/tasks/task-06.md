---
id: task-06
title: 端到端验证
priority: P0
estimated_hours: 1
depends_on: [task-04, task-05]
blocks: [task-07]
allowed_paths: []
---

# task-06: 端到端验证

## 修改文件

无（纯验证任务，不写代码）

## 实现要求

本任务是对 task-04 (FastAPI) 和 task-05 (CLI) 的端到端集成验证。无新增或修改文件，执行以下手动测试步骤确认 API + CLI 全链路可用：

### 步骤 1: 安装 Phase 4 依赖
```bash
pip install -r ellectric/requirements-phase4.txt
```

### 步骤 2: 启动 API 服务
```bash
uvicorn ellectric.api.server:app --port 8000 &
```
等待 `Uvicorn running on http://127.0.0.1:8000` 消息出现（约 2-5 秒）。

### 步骤 3: 测试 predict 端点
```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"model_type":"load","horizon":24}' | python -m json.tool
```

### 步骤 4: 验证 predict 响应
- HTTP 状态码必须为 200
- JSON body 必须包含以下字段：
  - `timestamps`: 列表，长度为 `horizon` (24)，ISO 8601 格式
  - `predictions`: 列表，长度为 `horizon` (24)，元素为 float
  - `metrics`: 对象，包含 `mae`、`rmse`、`mape` 三个数值或 `null`

### 步骤 5: 验证 Swagger 文档
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
```
必须返回 `200`。

### 步骤 6: 测试 CLI forecast 命令
```bash
el-cli forecast load 24
```
验证：终端输出以表格形式展示预测结果（至少包含时间戳和预测值两列）。

### 步骤 7: 测试 CLI simulate 命令
```bash
el-cli simulate summer_peak --days 7
```
验证：终端输出包含出清价格、调度摘要、代理利润信息。

### 步骤 8: 停止服务
```bash
kill %1 2>/dev/null || kill $(lsof -ti:8000) 2>/dev/null
```

## 边界处理（必填）

### 降级场景：pipeline 数据不可用
如果预测模型文件或训练数据不可用（首次运行、文件缺失等），API 不 crash：
- `POST /predict` 返回 503 或 500，body 中 `detail` 字段包含清晰的错误描述，指向缺失的资源路径
- 错误信息格式：`"模型文件未找到: ellectric/models/xxx.json。请先运行 notebook 04 或 06 训练模型。"`
- 开发者看到错误消息后知道下一步该做什么

### 降级场景：ASSUME 不可用
如果 ASSUME 仿真环境未安装/配置：
- `el-cli simulate summer_peak` 提示 "ASSUME 未安装或配置不完整"，返回码非零
- `POST /simulate` 返回错误 JSON，`detail` 说明缺失依赖和安装步骤

### 进程清理
- 无论验证成功或失败，Step 8 必须执行
- `kill %1` 失败时 fallback 到 `lsof -ti:8000 | xargs kill`
- 最终确认端口 8000 已释放（`lsof -ti:8000` 无输出）

### CLI 不可用
- 如果 `el-cli` 未安装到 PATH（`command not found`），用 `python -m ellectric.cli.main` 替代
- 两种调用方式等价

## 非目标（本任务不做的事）

- 不修改任何源文件
- 不编写自动化测试脚本（本任务是手动验证，自动化测试在 CI 阶段引入）
- 不测试 LLM 功能（task-07~09 独立验证）
- 不测试 backtest 和 explain 端点（仅验证核心路径 predict + simulate）
- 不启动 Grafana / TimescaleDB / Docker Compose
- 不做性能压测或并发测试
- 不验证 Phase 1-3 已有功能（仅验证 Phase 4 新增的 API/CLI 层）

## TDD 步骤

1. **前置**: 确认 task-04 和 task-05 已完成，文件存在：
   - `ellectric/api/server.py`
   - `ellectric/cli/main.py`
2. **环境**: `pip install -r ellectric/requirements-phase4.txt` 成功，无依赖冲突
3. **启动**: `uvicorn ellectric.api.server:app --port 8000 &` 成功启动，输出 `Application startup complete`
4. **API 测试**: `curl -X POST http://localhost:8000/predict ...` 返回 200 + 合法 JSON
5. **Swagger**: `curl http://localhost:8000/docs` 返回 200
6. **CLI 测试**: `el-cli forecast load 24` 输出表格，`el-cli simulate summer_peak --days 7` 输出结果
7. **清理**: `kill %1` 停止 uvicorn，确认端口释放

> 如任一降级场景触发（模型/数据/ASSUME 不可用），验证错误信息格式和可操作性，不要求功能正常输出。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `pip install -r ellectric/requirements-phase4.txt` | 所有 7 个包安装成功，无依赖冲突报错 |
| AC-02 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"model_type":"load","horizon":24}'` | 返回 `200` 或降级错误码 (`500`/`503`)，不能是 `404` 或连接拒绝 |
| AC-03 | predict 200 响应 JSON 包含 `timestamps`、`predictions`、`metrics` 三个顶层字段 | 字段存在，`predictions` 长度为 `horizon` |
| AC-04 | predict 降级响应 JSON 包含 `detail` 字段，描述清晰的错误原因和修复步骤 | 错误信息包含资源路径和建议操作 |
| AC-05 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs` | 返回 `200`（Swagger UI HTML 可加载） |
| AC-06 | `el-cli forecast load 24` | 终端输出包含结构化表格（至少时间戳 + 预测值两列），或无歧义的错误提示 |
| AC-07 | `el-cli simulate summer_peak --days 7` | 终端输出包含 "clearing" / "dispatch" / "profit" 相关内容，或无歧义的错误提示 |
| AC-08 | 停止 uvicorn 后 `lsof -ti:8000` 无输出 | 端口 8000 已释放，无残留进程 |
| AC-09 | `git diff --stat ellectric/pipeline/` | pipeline 目录下文件零改动（回归验证） |
