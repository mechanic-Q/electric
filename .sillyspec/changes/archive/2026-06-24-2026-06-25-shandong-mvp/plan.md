---
author: lmr
created_at: 2026-06-25T01:30:00+08:00
---

# 实现计划 — 山东 15min MVP

plan_level: full
理由: 17 文件跨 pipeline/fetch/config/notebooks 4 个模块，含 schema 扩展和新模块。

## Wave 拓扑

```
Wave 1 (基础设施)        Wave 2 (山西清理)         Wave 3 (气象接入)
└─ T1.1 Loader              └─ T2.1 删 shanxi_loader   └─ T3.1 WeatherFetcher
└─ T1.2 工厂                └─ T2.2 删 fetch/shanxi    └─ T3.2 __init__
└─ T1.3 TimeConfig          └─ T2.3 删 data/raw/shanxi
└─ T1.4 数据+README         └─ T2.4 删 verify_shanxi
                            
Wave 4 (文档+Notebook)                      Wave 5 (Wiki)
└─ T4.1 README ───────────────────┐         └─ T5.1 synthesis
└─ T4.2 CLAUDE.md ────────────────┤         └─ T5.2 entity update
└─ T4.3 Notebook 01-11 (并行) ────┤         └─ T5.3 log/index sync
└─ T4.4 管道验证 (smoke test) ────┘
```

## 执行顺序

1. **Wave 1**：必须先建 Loader/Config，下游全部依赖
2. **Wave 2**：可与 Wave 1 并行，但不能晚于 Wave 4 notebook 切换
3. **Wave 3**：独立模块，可在任意点并行
4. **Wave 4**：依赖 Wave 1 完成（notebook 用新 Loader）
5. **Wave 5**：与 Wave 4 并行，文档记录

详细任务清单见 `tasks.md`。

## 关键依赖

- T4.3 notebook 必须等 T1.1+T1.2+T1.3+T1.4 全部完成（数据源就绪）
- T2.1 删 shanxi_loader 必须等 T1.2 factory 已不再引用 shanxi（避免 ImportError）
- T4.4 smoke test 是整个变更的最终验收信号

## 风险预案

| 风险 | 缓解 |
|---|---|
| Notebook 重写耗时 | 用 3 个 sub-agent 并行处理 01-04 / 05-08 / 09-11 |
| 山西数据被误删 | 已在 git 历史中，可回滚 |
| Open-Meteo 网络依赖 | weather.py 已捕获 URLError，离线返回空 DataFrame |
