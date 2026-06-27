---
schema_version: 1
doc_type: module-card
module_id: feature-engineer
---
# feature-engineer
## 定位
时序特征工程模块，提供4层渐进式特征构造器（Tier1基础 → Tier2节日 + 周滞后 → Tier3滚动统计 + 循环编码 → Tier4气象特征）。纯特征变换，不涉及模型训练与数据清洗。
## 契约摘要
- `add_tier1_features(df)` — 构造 hour / day_of_week / month / is_weekend / lag_24h
- `add_tier2_features(df)` — 构造 is_holiday (holidays.China, fallback=0) / lag_168h
- `add_tier3_features(df)` — 构造 rolling_mean_24h / rolling_std_24h / hour_sin / hour_cos
- `get_feature_columns(tier)` — 按 tier 返回特征列名列表
- `add_tier4_weather_features(df, weather_df=None, weather_cache_path=None, fetch_if_missing=True)` — 构造气象特征（气温/辐射/风速/降水/湿度/云量），支持缓存与自动抓取
- `get_feature_columns("tier4")` — 返回 Tier1-3 + 实际存在的 weather 列
- `prepare_features(df, tiers, weather_df=None, weather_cache_path=None, fetch_if_missing=True)` — 一次性构造多层特征；tiers 包含 "tier4" 时自动准备前置层；缺 weather 列时不会抛异常
   
  输入: pd.DataFrame (含 timestamp, load), 输出: pd.DataFrame (增加特征列)
## 关键逻辑
1. Tier1: df.hour → hour; df.dayofweek → day_of_week; month/is_weekend → int; lag_24h = load.shift(TimeConfig.points_per_day)
2. Tier2: try `import holidays` → 查 China holidays → is_holiday 0/1; except ImportError → 全部填 0; lag_168h = load.shift(TimeConfig.points_per_week)
3. Tier3: rolling(TimeConfig.points_per_day).mean/.std; hour → sin(2π*h/24), cos(2π*h/24)
4. Tier4: 气象数据的来源优先级为 ①显式 weather_df → ②parquet cache → ③fetch_if_missing 抓取（Open-Meteo）→ ④降级返回无 weather 列的 df。对齐方式为 reindex + ffill（小时级源 → 15min 目标轴）。cache 路径默认 ellectric/data/shandong/weather_2024-2026.parquet，可覆盖。weather 列命名模式 {var}_{city}，城市来自 SHANDONG_CITIES（jinan, qingdao）
## 注意事项
- holidays 包可选——缺失时 is_holiday 全为 0，不会抛异常
- 滞后特征 shift 会导致前 N 行为 NaN，训练前需 dropna
- 循环编码处理小时周期性：23:00 和 00:00 在向量空间是相邻的
- weather cache 是派生数据，可删除后由 fetch_if_missing=True 自动重建
- 天气数据源为 Open-Meteo 小时级 API；15min 对齐使用前向填充 (ffill)，不代表真实 15min 气象
- Open-Meteo 网络失败不会阻断管道，Tier4 降级为无 weather 特征（记录 warning）
- weather 列命名格式 {var}_{city}，城市源自 SHANDONG_CITIES（jinan, qingdao）
### Weather Tier4 验证
验证脚本: `python ellectric/scripts/validate_weather_tier4.py` — 验证 Weather Tier4 特征接入正确性并输出 JSON/Markdown 报告。
产物路径: `ellectric/reports/weather_tier4/weather_tier4_validation.json` 和 `weather_tier4_validation.md`。
语义: 报告式验证 (report-only)，不设硬性精度提升阈值 (hard_threshold_applied=false)。
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
