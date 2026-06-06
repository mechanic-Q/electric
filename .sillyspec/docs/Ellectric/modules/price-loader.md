---
schema_version: 1
doc_type: module-card
module_id: price-loader
---
# price-loader
## 定位
电价数据接入层 — 加载 ZionLuo xlsx，标准化列名，统一时区
## 契约摘要
- 入口: `create_price_loader(data_path) -> PriceDataLoader`
- 输出: DataFrame[timestamp, price_da, price_rt, load_mw, wind_mw, solar_mw, tie_line_mw]
## 关键逻辑
- 不继承 DataLoader ABC（电价数据 7 列与负荷数据差异大）
- 列名标准化：中文→英文（7 个映射）
- 时区统一为 UTC
## 注意事项
- 当前不支持 start/end 时间过滤
- 用户需手动从 ZionLuo 仓库下载 xlsx
