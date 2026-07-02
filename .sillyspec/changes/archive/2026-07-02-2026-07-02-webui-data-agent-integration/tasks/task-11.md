---
id: task-11
title: 改造 WebUI 为聊天 + 数据面板
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on:
  - task-04
  - task-09
blocks:
  - task-12
  - task-13
requirement_ids:
  - FR-07
  - FR-08
decision_ids:
  - D-001@v1
  - D-002@v1
  - D-004@v1
  - D-005@v1
allowed_paths:
  - ellectric/api/static/index.html
---

## goal

将单栏聊天升级为响应式两栏：左栏聊天流 + 右栏数据面板（能力清单、数据集元信息、最近报告列表）。工具结果在气泡内展示结构化卡片（指标表/报告卡），同时同步到右侧面板。

## implementation

1. HTML 结构改为 `#app > .shell > .chat + .data`，右侧面板默认显示按类别分组的能力清单、数据集（fetch `/datasets`）、最近报告（fetch `/reports`）
2. CSS 两栏 grid `minmax(420px,1fr) 380px`；移动端 `<860px` 折叠右侧面板，右侧结果仍通过气泡内卡片展示
3. JS 启动时 fetch `/capabilities` 渲染建议 chips；fetch `/datasets`/`/reports` 填充面板
4. SSE: 兼容旧 `event.tool`/`event.tool_id` 和新 `event.name`；读取 `event.message || event.content` 作为错误信息；`tool_result` 的 `payload` 解析为结构化卡片（指标 table/报告卡），非 JSON 则显示文本摘要
5. 欢迎区改为分组问题：预测、评估、交易、解释、数据
6. fallback 来源信息在所有卡片底部标注（`source=offline_report` / `fallback_reason=model_missing`）; header/subtitle 样式保留

## acceptance

- [ ] 首页显示能力清单（分组）+ 数据集 + 最近报告，来自 catalog API
- [ ] 工具结果在气泡内渲染为结构化卡片（指标 table）
- [ ] SSE 同时兼容旧 `event.tool` 和新 `event.name` field
- [ ] 模型缺失时气泡内 fallback 卡片标注 `source=offline_report`
- [ ] 移动端右侧面板折叠，结果仍在气泡内展示

## verify

```bash
python -m pytest tests/test_api_catalog.py tests/test_chat_streaming_events.py -q
```

## constraints

单文件 HTML（无 React/Vite 依赖）；移动端 `<860px` 时折叠右侧面板，聊天流保持可用
