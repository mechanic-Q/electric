---
schema_version: 1
doc_type: module-card
module_id: ember-loader
---
# ember-loader
## 定位
Ember Climate 数据加载器 — 中国小时级/日级电力数据探索（实验性）
## 契约摘要
- `EmberDataLoader()` — 通过 Ember API 获取中国电力数据
- `load_data(start, end) -> pd.DataFrame` — 标准化列名，UTC 时区
## 关键逻辑
- `https://api.ember-energy.org/v1/country/CHN` — 三级容错：API → 缓存 → 降级
- 列名标准化映射至 Data Contract
## 注意事项
- 实验性模块，Ember API 可能变更或需要认证
- API 不可用时降级为提示手动下载
- needs_review: 需验证 Ember API 可用性
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
