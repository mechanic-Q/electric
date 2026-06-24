---
author: lmr
created_at: 2026-06-25T00:35:00+08:00
---

# 决策记录 — 山东 15min MVP

| ID | 决策 | 备选 | 理由 |
|---|---|---|---|
| D-001@v1 | ShandongDataLoader 继承 DataLoader ABC，扩展 schema | 独立模块不继承 | 工厂统一，learn cost 最低 |
| D-002@v1 | 删除 shanxi_loader.py + 全量 1948 JSON | 保留归档 | 山西是参考价，不能用；删干净避免混淆 |
| D-003@v1 | Notebook 原地覆盖 | 另存 archive 目录 | git 历史可回溯；避免目录碎片 |
| D-004@v1 | 本期接 Open-Meteo 气象 | 后续单独变更 | 数据已有风电光伏实际出力，气象做特征增强，边际成本低 |
| D-005@v1 | TimeConfig 默认 96/672/15min | 保留 24 小时模式 + 运行时切换 | 整个项目意义在 15min，不需要小时级兼容 |
| D-006@v1 | features 优先用实时价格 | 两项都做 | 日前价格 75% null，实时价格 99.9% 完整 |
| D-007@v1 | load_mw 列保留为合同要求列 | 改为 `actual_load_mw` | 下游 modules 都依赖 load_mw 列名 |
