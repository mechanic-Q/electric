---
author: lmr
created_at: 2026-07-02 16:55:06
---

# Tasks

> 只列任务名、文件路径、覆盖的 FR/D。实现细节在 plan 阶段展开。

## 任务列表

- [ ] task-01: 新增 catalog registry 服务
  - 文件：`ellectric/service/catalog.py`
  - 覆盖：FR-01, FR-02, FR-03, D-002@v1, D-003@v1, D-005@v1

- [ ] task-02: 扩展 service schemas
  - 文件：`ellectric/service/schemas.py`
  - 覆盖：FR-01, FR-02, FR-03, D-002@v1, D-005@v1

- [ ] task-03: 新增 catalog handlers 与 forecast fallback helper
  - 文件：`ellectric/service/handlers.py`
  - 覆盖：FR-01, FR-02, FR-03, FR-05, D-003@v1, D-005@v1

- [ ] task-04: 新增 capabilities/datasets/reports API 路由
  - 文件：`ellectric/api/server.py`
  - 覆盖：FR-01, FR-02, FR-03, FR-09, D-002@v1, D-005@v1

- [ ] task-05: 扩展 LLM tools 并实现离线报告 fallback
  - 文件：`ellectric/llm/tools.py`
  - 覆盖：FR-04, FR-05, D-002@v1, D-003@v1, D-004@v1, D-005@v1

- [ ] task-06: 更新 Agent prompt 和工具注册
  - 文件：`ellectric/llm/agent.py`
  - 覆盖：FR-04, D-002@v1, D-004@v1, D-005@v1

- [ ] task-07: 修复 SSE 事件字段协议
  - 文件：`ellectric/chat/streaming.py`
  - 覆盖：FR-06, D-001@v1, D-005@v1

- [ ] task-08: 改造 WebUI 为聊天 + 数据面板
  - 文件：`ellectric/api/static/index.html`
  - 覆盖：FR-07, FR-08, D-001@v1, D-002@v1, D-004@v1, D-005@v1

- [ ] task-09: 新增 catalog service 测试
  - 文件：`tests/test_service_catalog.py`
  - 覆盖：FR-01, FR-02, FR-03, FR-05, D-002@v1, D-003@v1, D-005@v1

- [ ] task-10: 新增 catalog API smoke 测试
  - 文件：`tests/test_api_catalog.py`
  - 覆盖：FR-01, FR-02, FR-03, FR-09, D-005@v1

- [ ] task-11: 新增 SSE 事件协议测试
  - 文件：`tests/test_chat_streaming_events.py`
  - 覆盖：FR-06, D-001@v1, D-005@v1

- [ ] task-12: 更新 README Web Chat 使用说明
  - 文件：`README.md`
  - 覆盖：FR-08, D-002@v1, D-004@v1

- [ ] task-13: 运行 targeted verification
  - 文件：`.sillyspec/local.yaml`, `tests/`, `ellectric/api/server.py`
  - 覆盖：FR-01 至 FR-09, D-001@v1 至 D-005@v1
