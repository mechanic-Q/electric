---
author: lmr
created_at: 2026-06-10 16:31:10
id: task-04
title: 端到端流式对话验证
priority: P0
estimated_hours: 1
depends_on: [task-01, task-02, task-03]
blocks: []
allowed_paths:
  - ellectric/api/static/index.html
---

# task-04: 端到端流式对话验证

## 修改文件（必填）

- 无代码修改，纯验证任务。如验证过程中发现 bug，修复范围限于本变更集（task-01/02/03 涉及的文件）。

## 实现要求

本任务是 Wave 1 的收尾验证环节。需要依次完成以下手动测试：

### V-01: 服务启动

```bash
cd /mnt/e/Ellectric
source ellectric/.venv/bin/activate
DEEPSEEK_API_KEY=sk-your-key uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000
```

验证：服务启动无 crash，日志包含 `StaticFiles` mount 信息，`/health` 端点可访问。

### V-02: 浏览器聊天 UI

打开浏览器访问 `http://localhost:8000/`：

1. 页面正常加载，显示"电力交易 AI 助手"标题 + ONLINE 状态指示灯
2. 显示 4 个建议快捷按钮：负荷预测、市场仿真、策略回测、模型解释
3. 底部输入框可见，placeholder 文字正确
4. 点击快捷按钮 → 问题文本自动填入输入框并发送
5. 发送后用户消息气泡出现，AI 回复逐字流式渲染
6. 工具调用时黄色标签出现（spinner 动画），完成后变绿
7. AI 回复完成后发送按钮恢复可点击

### V-03: Enter / Shift+Enter 快捷键

1. 在输入框输入文字后按 Enter → 发送消息
2. Shift+Enter → 插入换行符，不发送

### V-04: 移动端响应式

1. Chrome DevTools 切换到移动设备模式（375px 宽度）
2. 聊天界面全宽显示，消息气泡占 88% 宽度
3. 输入区域 padding 正常，无横向溢出
4. header subtitle 隐藏（`display: none`）

### V-05: 无 API Key 时的优雅降级

```bash
unset DEEPSEEK_API_KEY
# 重启服务后
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "你好", "history": []}'
```

验证：返回 SSE `error` 类型事件，消息内容包含友好错误提示（如 "未配置 DEEPSEEK_API_KEY"），HTTP 状态码仍为 200（SSE 协议在响应体内传递错误事件），服务不 crash。

## 接口定义（代码类任务必填）

本任务不涉及代码实现，以下 curl 命令用于验证已有接口行为不变。

### 现有端点验证（向后兼容性）

```bash
# Health check — 应正常返回
curl -s http://localhost:8000/health | python -m json.tool

# 负荷预测 — 应正常返回
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"source": "owid", "horizon": 24}' | python -m json.tool

# 市场仿真 — 应正常返回
curl -s -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario": "summer_peak", "days": 7}' | python -m json.tool

# 回测 — 应正常返回
curl -s -X POST http://localhost:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2022-08-01", "end_date": "2022-08-07", "strategy": "ppo", "model_path": ""}' | python -m json.tool

# 模型解释 — 应正常返回
curl -s -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{"model_type": "xgboost", "feature_index": 0}' | python -m json.tool
```

验证：所有 5 个现有端点（`/health`、`/predict`、`/simulate`、`/backtest`、`/explain`）返回格式与变更前一致，HTTP 状态码 200，`/docs` Swagger 页面正常加载。

### SSE 流式对话端点验证

```bash
# 正常对话 — 应返回 SSE text/event-stream
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "今天负荷预测值是多少", "history": []}'

# 验证：输出为 SSE 格式，逐行 data: JSON，包含 token/tool_call/tool_result/done 事件
```

## 边界处理（必填）

| # | 场景 | 处理方式 |
|---|------|---------|
| E-01 | 服务未启动时访问 `http://localhost:8000/` | 浏览器显示"无法连接"，预期行为。服务启动后恢复正常。 |
| E-02 | `DEEPSEEK_API_KEY` 未设置时发送聊天请求 | SSE 流返回 `error` 类型事件，内容为 `"DEEPSEEK_API_KEY 未设置，请在服务端配置环境变量"`。HTTP 200 + event-stream，不 crash。前端显示红色错误卡片。 |
| E-03 | 用户发送空消息（纯空格或空字符串） | 前端 `sendMessage()` 拒绝发送（`!query.trim()` 检查），不产生 HTTP 请求。 |
| E-04 | SSE 流中断（网络断开/手动刷新页面） | 前端 `fetch` 的 `catch` 块捕获 `TypeError`（network error），显示红色错误卡片。已接收的 token 内容保留在气泡中，不清空。 |
| E-05 | `marked.js` CDN 加载失败 | `typeof marked === 'undefined'` 为 `true`，但当前 index.html 未实现 fallback — 此为已知待改进项（design.md R-03 风险已登记）。验证时确认浏览器控制台有 `marked is not defined` 错误，聊天功能仍可正常发送/接收 token 但 Markdown 不渲染（显示原始文本）。**不阻塞本任务，留待后续修复。** |
| E-06 | 多标签页同时打开聊天页面 | 两个标签页独立管理 `conversation` 数组（浏览器内存），互不干扰。每条消息独立 POST，服务端无状态。 |
| E-07 | 用户输入超长消息（>2000 字符） | HTML `<textarea maxlength="2000">` 阻止输入超过 2000 字符。粘贴超长文本时自动截断。 |
| E-08 | API 路由优先级：访问 `/docs` 时是否被 StaticFiles 拦截 | FastAPI `/docs` 路由在 `StaticFiles` mount 之前注册，API 路由优先匹配。验证 `curl http://localhost:8000/docs` 返回 Swagger UI HTML，不被 static 覆盖。 |
| E-09 | 浏览器不支持 `ReadableStream`（IE 11） | 非目标范围（requirements.md 明确支持 Chrome/Firefox/Safari/Edge 最近 2 个主版本）。 |

## 非目标（本任务不做的事）

- 不修改任何代码（纯验证）
- 不新增自动化测试框架
- 不修复 `marked.js` fallback 缺失（R-03 已登记，非本变更集范围）
- 不验证多用户并发（设计文档未做会话隔离）
- 不做性能压测
- 不做跨浏览器兼容性矩阵测试（非 IE 均可）
- 不验证 LLM 回复质量（依赖 DeepSeek 模型能力，非本变更集范围）

## 参考

- 需求文档：`/mnt/e/Ellectric/.sillyspec/changes/2026-06-10-web-chat-ui/requirements.md`
- 设计文档：`/mnt/e/Ellectric/.sillyspec/changes/2026-06-10-web-chat-ui/design.md`（第 8 节验收标准）
- 实现计划：`/mnt/e/Ellectric/.sillyspec/changes/2026-06-10-web-chat-ui/plan.md`
- 聊天 UI：`/mnt/e/Ellectric/ellectric/api/static/index.html`
- SSE 事件协议：design.md 第 4 节（SSE 事件协议表）
- 架构文档：`/mnt/e/Ellectric/.sillyspec/docs/Ellectric/scan/ARCHITECTURE.md`

## TDD 步骤

### 步骤 1：环境就绪检查

```bash
# 确认虚拟环境存在且依赖安装
ls /mnt/e/Ellectric/ellectric/.venv/bin/python && echo "OK"
python -c "import fastapi, uvicorn; print('FastAPI + Uvicorn OK')"

# 确认关键技术点已完成
grep -r "chat/stream" /mnt/e/Ellectric/ellectric/api/server.py > /dev/null && echo "/chat/stream endpoint OK"
grep -r "streaming=True" /mnt/e/Ellectric/ellectric/llm/agent.py > /dev/null && echo "agent streaming OK"
ls /mnt/e/Ellectric/ellectric/chat/streaming.py > /dev/null && echo "streaming.py OK"
```

### 步骤 2：启动服务（无 API Key）

```bash
cd /mnt/e/Ellectric
source ellectric/.venv/bin/activate
unset DEEPSEEK_API_KEY
uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000 &
sleep 3
curl -s http://localhost:8000/health
# 预期输出: {"status": "healthy", "timestamp": "..."}
```

### 步骤 3：验证静态文件 + API 优先级

```bash
# 静态文件正常返回
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/
# 预期: 200

# /docs 优先级正常（不被 static 覆盖）
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs
# 预期: 200

# 不存在的路径返回标准 FastAPI 错误
curl -s http://localhost:8000/nonexistent
# 预期: {"detail": "Not Found"}
```

### 步骤 4：验证无 API Key 时 SSE 优雅降级

```bash
curl -s -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "你好", "history": []}' 2>&1 | head -3
# 预期输出包含: data: {"type":"error","content":"...DEEPSEEK_API_KEY..."}
```

### 步骤 5：验证现有端点不受影响

```bash
# 逐一调用 4 个业务端点
echo "=== /predict ==="
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"source": "owid", "horizon": 24}' | python -c "import sys,json; d=json.load(sys.stdin); assert 'predictions' in d; print('OK')"

echo "=== /simulate ==="
curl -s -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario": "summer_peak", "days": 7}' | python -c "import sys,json; d=json.load(sys.stdin); assert 'summary' in d; print('OK')"

echo "=== /backtest ==="
curl -s -X POST http://localhost:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2022-08-01", "end_date": "2022-08-07", "strategy": "ppo", "model_path": ""}' | python -c "import sys,json; d=json.load(sys.stdin); assert 'metrics' in d; print('OK')"

echo "=== /explain ==="
curl -s -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{"model_type": "xgboost", "feature_index": 0}' | python -c "import sys,json; d=json.load(sys.stdin); assert 'shap_value' in d; print('OK')"

echo "=== All endpoints OK ==="
```

### 步骤 6：有 API Key 时端到端流式对话

```bash
# 停止旧服务，用真实 API Key 重启
kill %1 2>/dev/null
export DEEPSEEK_API_KEY=sk-your-real-key
uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000 &
sleep 3

# SSE 流式对话 — 观察 token 流输出
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "今天电力负荷预测值是多少？", "history": []}'
# 预期输出: data: {"type":"token","content":"..."} 逐行输出，最后 data: {"type":"done"}
```

### 步骤 7：浏览器手动验证（不可自动化）

1. 打开 Chrome/Firefox → `http://localhost:8000/`
2. 确认：页面显示"电力交易 AI 助手" + ONLINE 状态灯
3. 点击快捷按钮 "负荷预测" → 消息发送 + AI 流式回复
4. 输入 "仿真夏季高峰 7 天" 按 Enter → 工具调用黄色标签出现，完成后变绿
5. Shift+Enter 换行 → 不发送
6. DevTools → 移动设备模式 (375px) → 布局正常
7. DevTools Network 面板 → `/chat/stream` 请求 type 为 `text/event-stream`

### 步骤 8：清理

```bash
kill %1 2>/dev/null
```

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `curl http://localhost:8000/` | HTTP 200，返回 HTML 内容（聊天 UI） |
| AC-02 | 浏览器访问 `http://localhost:8000/` | 显示"电力交易 AI 助手"标题 + ONLINE 状态灯 + 4 个建议快捷按钮 + 输入框 |
| AC-03 | `curl http://localhost:8000/health` | HTTP 200，`{"status": "healthy", ...}` |
| AC-04 | `curl http://localhost:8000/docs` | HTTP 200，返回 Swagger UI HTML（不被 StaticFiles 拦截） |
| AC-05 | 无 API Key 时 `POST /chat/stream` | SSE 返回 `error` 事件，服务不 crash，HTTP 200 |
| AC-06 | 有 API Key 时 `POST /chat/stream` | SSE 流式逐 token 输出，最后一个事件 `type: done` |
| AC-07 | `POST /predict` 端点 | 返回格式不变，HTTP 200 |
| AC-08 | `POST /simulate` 端点 | 返回格式不变，HTTP 200 |
| AC-09 | `POST /backtest` 端点 | 返回格式不变，HTTP 200 |
| AC-10 | `POST /explain` 端点 | 返回格式不变，HTTP 200 |
| AC-11 | 浏览器输入框按 Enter | 发送消息 |
| AC-12 | 浏览器输入框按 Shift+Enter | 插入换行，不发送 |
| AC-13 | 移动端 (375px) 浏览器访问 | 全宽布局，气泡 88% 宽度，header subtitle 隐藏 |
| AC-14 | 工具调用触发（仿真/回测问题） | 黄色 tag 出现 + spinner，完成后变绿 tag "完成" |
| AC-15 | AI 回复中包含 Markdown（表格/列表/代码） | 正确渲染：表格有边框/th 蓝色 header，代码块有语法高亮，等宽字体 |

**AC-15 特殊要求**：由于需要触发真实工具调用（仿真/回测），此验收项依赖 DEEPSEEK_API_KEY 有效且 Agent 实际调用了工具。如 API Key 不可用，此验收项标记为"暂缓验证"，由后续集成测试覆盖。
