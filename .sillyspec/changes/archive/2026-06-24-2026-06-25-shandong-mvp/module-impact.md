---
author: lmr
created_at: 2026-06-25T01:45:00+08:00
---

# Module Impact — 山东 15min MVP 数据切换

## 交叉验证

| 来源 | 文件数 | 说明 |
|---|---|---|
| proposal 声明 | 17 | 新增 5 + 修改 12 |
| tasks.md 任务覆盖 | 18 | Wave 1-5 |
| git diff (HEAD~1..HEAD) | 35+ 文件 | 含非源码文件（data CSV, wiki, sillyspec 文档）|

以 git diff 为准。

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| pipeline 数据加载 | 新增 + 数据结构变更 | `shandong_loader.py` (A), `data_loader.py` (M) | 新增 ShandongDataLoader（21列扩展schema）；工厂删8山西分支、注册shandong源 | false |
| pipeline 配置 | 配置变更 | `config.py` (M) | TimeConfig 默认 24/168/h → 96/672/15min | false |
| notebook 学习 | 逻辑变更 | 11 notebook (M) | 数据源 OWID→山东，适配 15min 粒度、96 维 action space | false |
| fetch 数据抓取 | 重写 | `weather.py` (A), `__init__.py` (M) | 删 ShanxiFetcher，新建 WeatherFetcher (Open-Meteo) | false |
| 文档 | 文档更新 | `CLAUDE.md` (M), `README.md` (M) | 山东15min定位，删除OWID/山西描述 | false |
| 数据资产 | 新增 | `data/shandong/` | 山东 CSV 71520行 + README | false |
| 外部数据 | 新增 | `data/raw/china_provincial/` | Zenodo 31省小时负荷 (Wu & Kan 2018) | false |

## 删除影响

| 删除内容 | 影响 | 回滚路径 |
|----------|------|----------|
| `shanxi_loader.py` (8 loader类) | 所有 create_loader("shanxi_*") 调用将 ValueError | git checkout HEAD~1 shanxi_loader.py |
| `fetch/shanxi.py` | import ellectric.fetch.shanxi 失效 | git checkout HEAD~1 |
| `data/raw/shanxi/` (1948 JSON) | 山西原始数据丢失 | git checkout HEAD~1 data/raw/shanxi/ |

## 未匹配文件（非核心变更）

| 文件 | 说明 |
|------|------|
| `.agents/skills/huashu-design/` | 已有设计资源，未受影响 |
| `ellectric/models/` | 训练产物（joblib），可在 notebook 中重新生成 |
