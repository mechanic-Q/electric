---
schema_version: 1
doc_type: module-card
module_id: feature-engineer
---
# feature-engineer
## 定位
时序特征工程模块，提供3层渐进式特征构造器（Tier1基础 → Tier2节日 + 周滞后 → Tier3滚动统计 + 循环编码）。纯特征变换，不涉及模型训练与数据清洗。
## 契约摘要
- `add_tier1_features(df)` — 构造 hour / day_of_week / month / is_weekend / lag_24h
- `add_tier2_features(df)` — 构造 is_holiday (holidays.China, fallback=0) / lag_168h
- `add_tier3_features(df)` — 构造 rolling_mean_24h / rolling_std_24h / hour_sin / hour_cos
- `get_feature_columns(tier)` — 按 tier 返回特征列名列表
- `prepare_features(df, tiers)` — 一次性构造多层特征的便捷包装
  
  输入: pd.DataFrame (含 timestamp, load), 输出: pd.DataFrame (增加特征列)
## 关键逻辑
1. Tier1: df.hour → hour; df.dayofweek → day_of_week; month/is_weekend → int; lag_24h = load.shift(24)
2. Tier2: try `import holidays` → 查 China holidays → is_holiday 0/1; except ImportError → 全部填 0; lag_168h = load.shift(168)
3. Tier3: rolling(24).mean/.std; hour → sin(2π*h/24), cos(2π*h/24)
## 注意事项
- holidays 包可选——缺失时 is_holiday 全为 0，不会抛异常
- 滞后特征 shift 会导致前 N 行为 NaN，训练前需 dropna
- 循环编码处理小时周期性：23:00 和 00:00 在向量空间是相邻的
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
