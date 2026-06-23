---
author: lmr
created_at: 2026-06-23T18:00:00+08:00
---

# Module Impact — 山西现货数据接入

## 变更概述

`shanxi-spot-data-access` (PR #7)：新增山西零售商城 15min 现货数据接入层。ShanxiBaseLoader 抽象基类 + 3 个子类，create_loader 工厂扩展。

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|---|---|---|---|---|
| data-loader | 新增 + 接口变更 | `ellectric/pipeline/shanxi_loader.py` (新增) | ShanxiBaseLoader + 3 子类 | false |
| data-loader | 接口变更 | `ellectric/pipeline/data_loader.py` (修改, +20 行) | create_loader() 新增 3 个 source 分支 | false |
| scripts | 新增 | `ellectric/scripts/verify_shanxi_loader.py` (新增) | 24 项验证脚本 | false |
| data | 新增 | `ellectric/data/raw/shanxi/` (1947 文件) | 原始 JSON 数据 | false |
| data | 新增 | `ellectric/data/raw/shanxi/README.md` (新增) | 数据资产说明 | false |

## 未匹配文件

| 文件 | 原因 |
|---|---|
| `ellectric/data/raw/shanxi/*.json` (1947 文件) | 数据资产文件，不在模块映射中 |

## 下游影响分析

- **create_loader() 现有 source** (`owid`/`manual`/`file`/`ember`)：行为完全不变
- **EmberLoader**：顶部 import DataLoader — 不受影响
- **cleaner.py**：注释中提及 DataLoader — 不受影响
- **price_loader.py**：doc 中提及 DataLoader — 不受影响
- **无调用点扩散**：create_loader() 仅 data_loader.py 内部引用

## 验证结论

`python ellectric/scripts/verify_shanxi_loader.py` — 24/24 通过，0 失败。
