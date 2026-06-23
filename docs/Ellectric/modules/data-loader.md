---
schema_version: 1
doc_type: module-card
module_id: data-loader
---
# data-loader
## 定位
电力数据加载抽象层 —— 通过 ABC 统一接口屏蔽 OWID 远程拉取与本地文件读取的差异，工厂函数按 source 参数创建对应实例。边界仅到 `pd.DataFrame(timestamp, load_mw, region)` 产出，不涉及清洗/特征工程。
## 契约摘要
- `DataLoader.load_data(start, end) -> pd.DataFrame` — 强制契约，返回三列标准格式
- `OWIDChinaLoader` — 流式解析 OWID GitHub 25MB CSV，过滤 iso_code='CHN'，TWh→日均 MW
- `ChineseDataLoader` — 本地 CSV/Excel/Parquet 自动检测格式，列名标准化，UTC 时区归一化
- `create_loader("owid"|"manual"|"file", **kwargs)` — 单一入口，返回符合契约的 DataLoader
## 关键逻辑
```
loader = create_loader(source, data_path/...)      // 工厂路由
df = loader.load_data("2020-01-01", "2024-12-31")  // 统一接口
// OWIDChinaLoader: stream CSV rows -> filter CHN -> safe_float -> twh_to_daily_mw
// ChineseDataLoader: read_* via format -> standardize_columns -> tz_localize UTC
return df[timestamp, load_mw, region]
```
## 注意事项
- OWID CSV 为单一大文件，流式读取避免内存峰值；网络不可用时回退异常，不做本地缓存
- `_safe_float` 返回 None 而非抛异常，上游需自行决策缺失值策略
- 中国 hourly 数据需手动下载，`ChineseDataLoader` 仅负责加载已落盘的本地文件
## 变更索引
- ql-20260606-001-a3f2 | 新增 get_metadata(), load_hourly_demand(), data_version 属性
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
