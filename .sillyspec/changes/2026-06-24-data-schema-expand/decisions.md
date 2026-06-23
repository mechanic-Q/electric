---
author: lmr
created_at: 2026-06-24T00:10:00+08:00
---

# Decisions — 数据 schema 扩展

## D-001@v1 — 同文件追加 5 子类

**决策**：5 个新 loader 子类追加到 `shanxi_loader.py` 末尾，沿用 ShanxiBaseLoader 模式。

**备选**：
- B：独立 `shanxi_schema_ext.py`（被拒：拆文件增加引用导入复杂度）
- C：配置表驱动（被拒：抽象过早，5 个字段差异大）

**理由**：与既有 3 类同模式，单元测试覆盖一致，单 import 路径清晰。

## D-002@v1 — 长表展开

**决策**：对 array-typed JSON records（如 `dateList`/`energyList`/`priceList` 或 `seriesData`/`seriesName`），展开为长表：每个(date, energy, price) 或 (series, time_index, value) 一行。

**理由**：保持与 spot_da/rt/month_settle 长表语义一致，下游 cleaner/features 直接消费无需 reshape。

## D-003@v1 — inferred 字段语义保留

**决策**：5 个新子类字段含义未官方文档化，标 `inferred` 在 docstring。

**理由**：与 shanxi-spot-data-access 一致原则，避免造成虚假权威。
