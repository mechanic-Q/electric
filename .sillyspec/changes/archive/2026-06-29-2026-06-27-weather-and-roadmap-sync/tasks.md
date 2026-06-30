---
author: lmr
created_at: 2026-06-27 18:58:49
---

# Tasks

- [ ] T-001 — 扩展 `FeatureEngineer` Tier4 weather API (`ellectric/pipeline/features.py`) — 覆盖 FR-001, FR-003, FR-004, D-006@v2
- [ ] T-002 — 实现 weather parquet cache 读取/抓取/写入与降级路径 (`ellectric/pipeline/features.py`, `ellectric/fetch/weather.py`) — 覆盖 FR-002, FR-003, D-007@v2
- [ ] T-003 — 修正或规避 `WeatherFetcher.align_to_15min()` 30min 容差边界 (`ellectric/fetch/weather.py`) — 覆盖 FR-003, D-007@v2
- [ ] T-004 — 增加 weather feature 测试 (`tests/test_weather_features.py`) — 覆盖 FR-001~FR-004, D-006@v2, D-007@v2
- [ ] T-005 — 更新 feature-engineer 模块文档与 module-map (`docs/Ellectric/modules/feature-engineer.md`, `docs/Ellectric/modules/_module-map.yaml`) — 覆盖 FR-005, D-009@v1
- [ ] T-006 — 更新 scan 架构文档旧事实 (`docs/Ellectric/scan/ARCHITECTURE.md`) — 覆盖 FR-005, D-009@v1
- [ ] T-007 — 更新 README/ROADMAP/REQUIREMENTS 状态 (`ellectric/README.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`) — 覆盖 FR-005, D-001@v1~D-005@v1
- [ ] T-008 — 新增 LLM Wiki closeout synthesis (`wiki/synthesis/electric-phase4-closeout-20260627.md`) — 覆盖 FR-006, D-008@v1
- [ ] T-009 — 更新 LLM Wiki 现有 entity/synthesis/index/log (`wiki/entities/lmr-electric.md`, `wiki/synthesis/electric-data-requirements-vs-tuji-20260622.md`, `wiki/index.md`, `wiki/log.md`) — 覆盖 FR-006, D-008@v1
- [ ] T-010 — 验证与对账：运行 weather tests、旧 API 兼容测试、文档 grep、wiki schema 检查 — 覆盖 FR-001~FR-006
