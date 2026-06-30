---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Tasks: LLM 交易建议工具

- [ ] T-01: 新增 recommend request/response schema
  - 文件: `ellectric/service/schemas.py`
  - 覆盖: FR-01, FR-02, FR-03, D-001@v1, D-002@v1

- [ ] T-02: 实现 `run_recommend_trade()` service handler
  - 文件: `ellectric/service/handlers.py`
  - 覆盖: FR-04, FR-06, FR-07, D-003@v1, D-004@v1

- [ ] T-03: 新增 `/recommend` FastAPI endpoint
  - 文件: `ellectric/api/server.py`
  - 覆盖: FR-05

- [ ] T-04: 新增 CLI `recommend` 子命令
  - 文件: `ellectric/cli/main.py`
  - 覆盖: FR-05

- [ ] T-05: 新增 LangChain `recommend_trade` tool 并注册到 agent
  - 文件: `ellectric/llm/tools.py`, `ellectric/llm/agent.py`
  - 覆盖: FR-05, D-003@v1

- [ ] T-06: 新增测试
  - 文件: `tests/test_recommend_handler.py`
  - 覆盖: FR-01~FR-08

- [ ] T-07: 生成样例报告与模块文档
  - 文件: `docs/Ellectric/modules/recommend.md`, `ellectric/reports/recommend/sample_output.md`
  - 覆盖: FR-07
