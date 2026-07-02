---
id: task-06
title: 更新服务层与 API 测试
author: lmr
created_at: 2026-07-03 01:21:50
priority: P0
depends_on: [task-01, task-02, task-03]
blocks: [task-08]
requirement_ids: [FR-01, FR-02, FR-04]
decision_ids: [D-001@v1, D-002@v1, D-004@v1]
allowed_paths:
  - tests/test_service_catalog.py
  - tests/test_api_catalog.py
goal: >
  用测试锁定 Weather Tier4 semantic metrics、metrics_meta、degraded fallback 与 API 输出契约。
implementation:
  - 更新 service catalog 测试断言 semantic keys 和 meta。
  - 增加 degraded report fixture 或 monkeypatch 覆盖 fallback。
  - API test 断言 report detail 包含 metrics_meta。
acceptance:
  - service catalog tests 覆盖 ok/degraded/missing。
  - API catalog tests 覆盖 metrics_meta 序列化。
  - 旧 legacy route 测试仍通过。
verify:
  - PYTHONWARNINGS=ignore ./.venv/bin/python -m pytest tests/test_service_catalog.py tests/test_api_catalog.py -q
constraints:
  - 不依赖真实网络。
  - 不修改报告原始 fixture 文件，优先 tmp_path/monkeypatch。
