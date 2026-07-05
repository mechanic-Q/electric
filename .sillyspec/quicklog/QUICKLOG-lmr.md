## ql-20260703-001-a3f1 | 2026-07-03 12:51:43 | 补工具缺失 + SSE测试同步 + 路由补全
状态：已完成
关联变更：default
文件：ellectric/llm/tools.py, ellectric/api/server.py, tests/test_chat_streaming_events.py

## ql-20260703-002-b8d2 | 2026-07-03 13:03:40 | 让 chat streaming 复用 DeepSeek key 解析逻辑
状态：已完成
关联变更：default
文件：ellectric/chat/streaming.py, tests/test_chat_streaming_events.py
结果：streaming.py 复用 _resolve_deepseek_key；新增无环境变量但 resolver 可用的回归测试；6 targeted passed，166 full passed。

## ql-20260703-003-c7d4 | 2026-07-03 13:16:27 | 修复 WebUI 滚动 + 欢迎页恢复 + tool_result 显示
状态：已完成
关联变更：default
文件：ellectric/api/static/index.html
结果：.chat 加 min-height:0 修复滚动；resetChat() + header ✕ 按钮恢复欢迎页；parsePayload() 从 event.content 兜底解析

## ql-20260704-001-69fd | 2026-07-04 22:36:35 | WebUI 全界面中英双语化
状态：已完成
关联变更：2026-07-05-webui-bilingual-copy
文件：ellectric/web/src/App.tsx, ellectric/api/static/*
结果：固定 UI、Copilot、主舞台、策略名、报告 title/status/summary/metric 均展示中英双语；未改后端数据结构；npm run build 通过并更新 static；扫描确认未新增 /predict、/simulate、/backtest 自动调用。
