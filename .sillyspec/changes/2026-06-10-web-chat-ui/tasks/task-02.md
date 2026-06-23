---
author: lmr
created_at: 2026-06-10 16:31:10
id: task-02
title: 修改 llm/agent.py — ChatOpenAI 加 streaming=True
priority: P0
estimated_hours: 1
depends_on: []
blocks: [task-03]
allowed_paths:
  - ellectric/llm/agent.py
---

# task-02: 修改 llm/agent.py — ChatOpenAI 加 streaming=True

## 修改文件（必填）
- 修改 `ellectric/llm/agent.py`

## 实现要求

基于 design.md section 6.3，对 `create_agent_executor()` 做以下两处修改：

1. **`ChatOpenAI` 构造函数新增 `streaming=True`** — 使 LLM 实例支持 LangChain `astream_events()`，后续 `chat/streaming.py` 可通过异步流式接口逐 token 产出 SSE 事件。`streaming=True` 不影响同步 `.invoke()` 调用（`ask_agent()` 继续正常工作）。

2. **model 参数化** — 将硬编码的 `"deepseek-v4-flash"` 改为 `os.environ.get("ELLECTRIC_LLM_MODEL", "deepseek-v4-flash")`，允许通过环境变量切换模型而不改代码。`DEEPSEEK_API_KEY` 的检查逻辑保持不变。

## 接口定义（代码类任务必填）

### `create_agent_executor()` — 修改前后 diff

```diff
 def create_agent_executor():
     api_key = os.environ.get("DEEPSEEK_API_KEY")
     if not api_key:
         raise RuntimeError(...)

     llm = ChatOpenAI(
-        model="deepseek-v4-flash",
+        model=os.environ.get("ELLECTRIC_LLM_MODEL", "deepseek-v4-flash"),
         api_key=api_key,
         base_url="https://api.deepseek.com/v1",
         temperature=0.3,
+        streaming=True,
     )

     return create_agent(
         model=llm,
         tools=[query_forecast, run_simulation, run_backtest],
         system_prompt=_SYSTEM_PROMPT,
     )
```

`ask_agent()` 不修改。

## 边界处理（必填）

1. **`ELLECTRIC_LLM_MODEL` 未设置** — `os.environ.get(..., "deepseek-v4-flash")` 回退到默认值，行为与修改前完全一致。
2. **`DEEPSEEK_API_KEY` 未设置** — 继续抛出 `RuntimeError`，异常消息不变，快速失败不走到 ChatOpenAI 实例化。
3. **`streaming=True` + 同步 `.invoke()`** — LangChain 的 `streaming=True` 在同步 `agent.invoke()` 下自动收集完整响应，`ask_agent()` 返回值类型 `str` 不变，调用方无感知。
4. **`ELLECTRIC_LLM_MODEL` 设为非法值** — 不在此任务校验。DeepSeek API 会在首次调用时返回 4xx 错误，由 LangChain 抛出 `OpenAIError`，`ask_agent()` 的调用方已有通用异常处理。
5. **`temperature` 和 `base_url` 不参数化** — 保持硬编码。`temperature=0.3` 是经过验证的合理默认值；`base_url` 固定为 DeepSeek 兼容端点。未出现在 design.md 的改动范围中。
6. **DeepSeek 非标准模型名（如 `deepseek-chat`）** — `ELLECTRIC_LLM_MODEL` 接受任意字符串，由 DeepSeek API 校验。设置 `export ELLECTRIC_LLM_MODEL=deepseek-chat` 即可切换到对话模型，无需改代码。

## 非目标（本任务不做的事）

- 不修改 `ask_agent()` 函数签名或实现
- 不在 `agent.py` 中引入 `astream_events()` 调用（由 `chat/streaming.py` 负责）
- 不参数化 `temperature` 或 `base_url`
- 不新增任何 import 语句
- 不修改 `_SYSTEM_PROMPT` 常量
- 不添加 `.env` 文件读取逻辑（继续使用 `os.environ.get`）
- 不修改 `ellectric/llm/tools.py`

## 参考

- design.md section 6.3 — `ellectric/llm/agent.py` 修改定义
- design.md section 7 兼容策略 — agent.py 向后兼容，`ask_agent()` 行为不变
- plan.md — task-02 在 Wave 1 中与 task-01 并行，无依赖
- `ellectric/llm/agent.py` — 当前代码，修改基数
- CONVENTIONS.md section 2.2 类型标注、section 2.3 Logger 标准化

## TDD 步骤

1. **写测试** — 修改前运行 `python -c "from ellectric.llm.agent import create_agent_executor, ask_agent; print('import OK')"` 确认当前可导入
2. **确认失败** — 不适用（本任务无新增逻辑，仅参数化 + 加标志位）
3. **写代码** — 执行上述 diff，修改 `agent.py` 两处
4. **确认通过** — 重新运行步骤 1 的导入检查；设置 `ELLECTRIC_LLM_MODEL=deepseek-chat` 验证参数化生效：`python -c "import os; os.environ['ELLECTRIC_LLM_MODEL']='deepseek-chat'; from ellectric.llm.agent import create_agent_executor; print('model param OK')"`
5. **回归** — `curl -X POST http://localhost:8000/health` 确认 API 服务正常；运行 `python -m ellectric.cli.main ask "你好"` (需 DEEPSEEK_API_KEY) 确认 `ask_agent()` 仍正常返回字符串

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| 1 | `python -c "from ellectric.llm.agent import create_agent_executor, ask_agent"` | 无 ImportError，函数存在 |
| 2 | `ELLECTRIC_LLM_MODEL` 未设置时实例化 `create_agent_executor()` | 使用默认 `deepseek-v4-flash`，无异常 |
| 3 | `export ELLECTRIC_LLM_MODEL=deepseek-chat && python -c "..."` | 使用指定模型，参数化生效 |
| 4 | `DEEPSEEK_API_KEY` 未设置时调用 `create_agent_executor()` | 抛出 `RuntimeError`，消息包含 "DEEPSEEK_API_KEY 未设置" |
| 5 | 有 API Key 时 `ask_agent("你好")` | 返回非空字符串，无 streaming 相关错误 |
| 6 | `ChatOpenAI` 实例化参数检查 | `streaming=True` 已传入，`temperature=0.3` 不变 |
