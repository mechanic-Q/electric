---
schema_version: 1
doc_type: module-card
module_id: cleaner
---
# cleaner
## 定位
电力时序数据预处理模块：对 DataFrame 执行 schema 校验、缺失值修复、IQR 异常值检测（只报告不删除）、UTC 时区标准化。边界：仅处理结构化列（timestamp, load_mw），不做领域级纠错或数据补全。
## 契约摘要
- `clean_data(df)` — 4 步管道入口：validate_schema → ffill+bfill 填充 → IQR 异常检测（Tukey's fences, 只记日志） → UTC 时区标准化
- `validate_schema(df)` — 返回 `{valid, issues, summary}`，检查 REQUIRED_COLUMNS 存在性、timestamp 类型、load_mw 类型和空值
- `REQUIRED_COLUMNS = {"timestamp", "load_mw"}` — 输入数据契约
- `OPTIONAL_COLUMNS` — 含 region, year, generation_twh 等，不强制但可透传
## 关键逻辑
```
def clean_data(df):
    validate_schema(df)                  # → 列名/类型/空值检查
    df["load_mw"].ffill().bfill()       # → 极端情况 fallback
    outliers = df[load_mw < Q1-1.5*IQR | load_mw > Q3+1.5*IQR]
    if len(outliers): logger.warning(...)  # → 只报告，不删除
    df["timestamp"] = utc_normalize(df["timestamp"])  # → 时区统一
```
## 注意事项
- IQR 异常值**永不删除**：尖峰负荷是重要信号，不是噪声。在 Phase 1 设计阶段已明确反"spike-as-noise"反模式。
- 缺失值填充使用 ffill+bfill 简单策略，适合年级粗粒度数据；后续如接入小时级数据需评估是否需要插值方案。
- `validate_schema` 返回 dict 而非抛异常，调用方需自行检查 `result["valid"]`。
- 仅依赖 pandas + numpy + logging，无内部模块依赖。
## 变更索引
- ql-20260606-001-a3f2 | 新增 detect_timezone(), standardize_frequency(), get_data_quality_score()
## 人工备注
<!-- MANUAL_NOTES_START -->
<!-- MANUAL_NOTES_END -->
