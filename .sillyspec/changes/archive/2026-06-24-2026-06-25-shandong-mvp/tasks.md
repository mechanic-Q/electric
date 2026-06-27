---
author: lmr
created_at: 2026-06-25T01:00:00+08:00
---

# 任务列表 — 山东 15min MVP 数据切换

plan_level: full
理由: 17文件跨pipeline/fetch/config/notebooks四个模块，含schema扩展和新模块。

## Wave 1: 基础设施 — 先建 Loader + 工厂 + Config

- [x] T1.1: 新建 `ellectric/pipeline/shandong_loader.py` — ShandongDataLoader (230行, 21列扩展schema)
- [x] T1.2: 修改 `ellectric/pipeline/data_loader.py` — factory删除8个shanxi分支，注册shandong源
- [x] T1.3: 修改 `ellectric/config.py` — TimeConfig默认 96/672/15min
- [x] T1.4: 拷贝 CSV 到 `ellectric/data/shandong/` + 写 README.md 数据资产说明

## Wave 2: 山西清理 — 删除旧模块

- [x] T2.1: 删除 `ellectric/pipeline/shanxi_loader.py` (8个类)
- [x] T2.2: 删除 `ellectric/fetch/shanxi.py` + `ellectric/scripts/fetch_shanxi.py`
- [x] T2.3: 删除 `ellectric/data/raw/shanxi/` (1948 JSON)
- [x] T2.4: 删除 `ellectric/scripts/verify_shanxi_loader.py`

## Wave 3: 气象接入 — WeatherFetcher

- [x] T3.1: 新建 `ellectric/fetch/weather.py` — WeatherFetcher (Open-Meteo, 纯标准库)
- [x] T3.2: 更新 `ellectric/fetch/__init__.py` — ShanxiFetcher → WeatherFetcher

## Wave 4: 文档 + Notebook — 同步所有引用

- [ ] T4.1: 更新 `ellectric/README.md` — 项目定位从OWID+山西→山东15min
- [x] T4.2: 更新 `CLAUDE.md` — 数据源和架构描述
- [ ] T4.3: Notebook 数据源切换 (01-11.ipynb)
- [ ] T4.4: 管道验证 — Load→Clean→Features→XGBoost 全通

## Wave 5: Wiki 同步

- [x] T5.1: 新建 synthesis 页 `shandong-mvp-switch-20260625`
- [x] T5.2: 更新 entity 页 `lmr-electric`
- [x] T5.3: 更新 log.md + index.md

## 未完成项

| 任务 | 优先级 | 说明 |
|---|---|---|
| T4.1 README 更新 | P1 | 项目主文档仍然引用旧源 |
| T4.3 Notebook 重写 | P1 | 11个 notebook 需要数据源从OWID切到shandong |
| T4.4 管道验证 | P0 | 已完成 ✅ (XGBoost MAE=5526MW, 8.0%) |
