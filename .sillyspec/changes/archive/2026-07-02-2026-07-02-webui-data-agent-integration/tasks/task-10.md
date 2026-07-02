---
id: task-10
title: 新增 SSE 事件协议测试（覆盖：FR-06, D-001@v1, D-005@v1）
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-09]
blocks: [task-13]
requirement_ids: [FR-06]
decision_ids: [D-001@v1, D-005@v1]
allowed_paths:
  - tests/test_chat_streaming_events.py
---

## goal

为 `ellectric/chat/streaming.py` 的 SSE 事件协议编写测试，锁定 tool_call / tool_result / error / done 四种事件的 JSON 字段契约，防止前端的字段依赖被意外破坏。

## implementation

1. 新建 `tests/test_chat_streaming_events.py`，`async def` 测试函数。
2. 使用 mock 替换 `create_agent_executor` 的返回值，使其 `astream_events` 返回可控的事件序列（tool_call → tool_result → done）。
3. 调用 `stream_chat("test")`，收集产出的 SSE 帧 JSON。
4. 分别验证：
   - `tool_call`: 字段 `type`=`"tool_call"`、`name` 存在、`args` 存在。
   - `tool_result`: 字段 `type`=`"tool_result"`、`name` 存在、`content` 存在。
   - `error`: 字段 `type`=`"error"`、`message` 存在。
   - `done`: 字段 `type`=`"done"`。
5. `error` 边界覆盖：空 query 返回 `{"type":"error","message":"查询不能为空"}`。
6. 全部事件 JSON 可 parse 且非空。
7. 不覆盖 `DEEPSEEK_API_KEY` 缺失的 `error`（与 SSE 协议无关）。

## acceptance

- 所有 SSE 事件帧符合 `{"type": ..., ...}` JSON 格式。
- `tool_call` / `tool_result` / `error` / `done` 四种事件的必选字段在前端解析时均可预期存在。
- mock agent 不依赖 DeepSeek API key、不联网。

## verify

```bash
python -m pytest tests/test_chat_streaming_events.py -q
```

## constraints

- mock agent event stream，不调用真实 LLM。
- 不依赖 `DEEPSEEK_API_KEY` 环境变量，不联网。
- 测试不修改生产代码或现有测试。
- 遵循 project `tests/` 内现有 pytest 风格（`async def` + mock patch）。
