---
id: task-09
title: 修复 SSE 事件字段协议（覆盖：FR-06, D-001@v1, D-005@v1）
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on: [task-07]
blocks: [task-10, task-11]
requirement_ids: [FR-06]
decision_ids: [D-001@v1, D-005@v1]
allowed_paths: [ellectric/chat/streaming.py]
---

## Goal

统一 `stream_chat()` 产出的五种 SSE 事件字段，使 `tool_result` 携带可选 `payload`（JSON 解析结果），确保前端可一致读取 `name`/`args`/`content`/`message`。

## Implementation

1. **`tool_result` 增加 `payload` 字段**（`streaming.py` L164-168）：对 `tool_output` 尝试 `json.loads()`，成功则 `payload=解析结果`，失败则 `payload=None`。
2. **保留现有字段**：`tool_call` 保持 `name`+`args`，`error` 保持 `message`，`token` 保持 `content`，`done` 无附加字段。
3. **不做字段重命名或删除**：不改 `name`→`tool` 等，避免向后破坏。
4. **边界处理**：`tool_output` 非字符串时先 `str()` 转换再尝试解析。

## Acceptance

- `tool_result` 事件包含 `name`、`content`、`payload` 三个字段。
- JSON 可解析的 tool 输出 → `payload` 为 dict/list；不可解析 → `payload=None`。
- `tool_call` 仍含 `name`+`args`；`error` 仍含 `message`；`token` 仍含 `content`。
- 现有 token/done 行为不变。

## Verify

```bash
python -m pytest tests/test_chat_streaming_events.py -q
```

## Constraints

- 仅修改 `ellectric/chat/streaming.py`。
- emit `name`/`args`/`content`/`message` 字段名保持一致，不引入新缩写。
- 保留 `token`/`done` 事件的现有行为。
