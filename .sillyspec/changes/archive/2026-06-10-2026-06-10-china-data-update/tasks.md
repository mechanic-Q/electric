---
author: lmr
created_at: 2026-06-10 13:30:00
---

# Tasks — 中国电力数据更新

## Wave 1: OWID 3 级回退 + 缓存

- [ ] 1.1 新增 OWID_CDN_URL 常量 + 修改 load_data() 回退链路 — `ellectric/pipeline/data_loader.py`
- [ ] 1.2 新增 _fetch_from_url() / _load_from_cache() / _save_cache() 方法 — `ellectric/pipeline/data_loader.py`
- [ ] 1.3 验证 OWID 拉取成功到 2025 年 — `ellectric/notebooks/01_data_ingestion.ipynb`

## Wave 2: Ember 数据加载器

- [ ] 2.1 新增 EmberLoader(DataLoader) 类 — `ellectric/pipeline/ember_loader.py`
- [ ] 2.2 create_loader() 注册 ember 源 — `ellectric/pipeline/data_loader.py`
- [ ] 2.3 更新 _module-map.yaml 新增 ember-loader 条目 — `.sillyspec/docs/Ellectric/modules/_module-map.yaml`

## Wave 3: 验证 + 文档

- [ ] 3.1 全管道 notebook 01→05 验证 — `ellectric/notebooks/01-05*.ipynb`
- [ ] 3.2 更新 README 数据源说明 — `ellectric/README.md`
- [ ] 3.3 更新 INTEGRATIONS.md Ember 条目 — `.sillyspec/docs/Ellectric/scan/INTEGRATIONS.md`
- [ ] 3.4 新增 data-sources.md — `docs/data-sources.md`
