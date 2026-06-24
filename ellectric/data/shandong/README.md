---
author: lmr
created_at: 2026-06-25T00:45:00+08:00
---

# 山东 15min 电力数据资产 (Shandong 15-Minute Power Data Inventory)

> 用户提供 CSV 数据文件。本文件为数据资产说明书。

## 数据源

| 字段 | 值 |
|---|---|
| 文件名 | 山东_2024-2026_15min.csv |
| 大小 | 11.3 MB |
| 格式 | CSV (UTF-8 BOM) |
| 时间范围 | 2024-01-01 ~ 2026-01-14 |
| 时间粒度 | **15 分钟**（96 点/日）|
| 总行数 | 71520 行（745 天 × 96 点）|
| 省份 | 山东 |
| 数据来源 | 推定来自山东电力交易中心日前/实时出清发布 |

## 字段映射 (21 列)

### 基础
| 原始列 | 映射列 | 类型 | 说明 |
|---|---|---|---|
| 日期 | → timestamp 部分 | str | YYYY-MM-DD |
| 时刻 | → timestamp 部分 | str | 00:15 ~ 24:00，15min 间隔 |
| 是否节假日 | is_holiday | int (0/1) | 是/否 |
| 是否周末休息日 | is_weekend | int (0/1) | 是/否 |

### 实际出清值（核心）
| 原始列 | 映射列 | 单位 | 覆盖率 |
|---|---|---|---|
| 直调负荷(实际) | **load_mw** | MW | 100% ✅ |
| 实时价格 | **rt_price** | 元/MWh | 99.9% ✅ |
| 日前价格 | da_price | 元/MWh | 25%（每小时 1 点，其余 null）|
| 风电总加(实际) | wind_actual_mw | MW | 100% |
| 光伏总加(实际) | solar_actual_mw | MW | 100% |
| 非市场化核电总加(实际) | nuclear_actual_mw | MW | 100% |
| 自备机组总加(实际) | captive_actual_mw | MW | 100% |
| 联络线受电负荷(实际) | tie_line_actual_mw | MW | 100% |
| 抽蓄(实际) | pumped_storage_mw | MW | 100% |
| 地方电厂发电总加(实际) | local_gen_actual_mw | MW | 100% |

### 预测值（默认不映射，include_forecasts=True 时可用）
直调负荷(预测) / 联络线受电负荷(预测) / 风电总加(预测) / 光伏总加(预测) / 非市场化核电总加(预测) / 自备机组总加(预测) / 地方电厂发电总加(预测)

### 注入列
| 列 | 值 | 说明 |
|---|---|---|
| province | "shandong" | 常量 |
| source | "user-provided-csv" | 数据来源标识 |
| granularity | "15min" | 时间粒度 |

## 关键限制

1. **24:00 时间点**：原始 CSV 包含 `24:00`（非有效 ISO 时间）。ShandongDataLoader 自动转换为次日 `00:00`。每日首个数据点可能是前一天的 24:00 → 00:00 继承。

2. **日前价格稀疏**：日前价格仅在每小时第一个 15min 时段提供（00:15, 01:00, ..., 23:00），其余 3/4 点为 null。**实际应用中优先用实时价格作为价格信号**。

3. **负荷定义**：`load_mw = 直调负荷(实际)`，不包含自备机组、地方电厂的出力。

4. **数据来源未官方验证**：数据来自用户提供，未与山东电力交易中心官方发布核对。

## 与 Electric 项目的使用

```python
from ellectric.pipeline.data_loader import create_loader

loader = create_loader("shandong")
df = loader.load_data("2024-06", "2024-08")

# df.columns: timestamp, load_mw, rt_price, da_price,
#             wind_actual_mw, solar_actual_mw, nuclear_actual_mw, ...
```
