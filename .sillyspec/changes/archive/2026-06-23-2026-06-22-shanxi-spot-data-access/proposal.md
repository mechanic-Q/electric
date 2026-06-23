---
author: lmr
created_at: 2026-06-23T14:52:56+08:00
---

# Proposal — 山西现货数据接入

## 动机 (Motivation)

Electric 项目当前数据基础有两个瓶颈：

1. **粒度过粗**：基于 OWID 年级数据（除以 365 得日均 MW），无法支撑 15 分钟级现货市场仿真和交易策略训练
2. **省份代表性不足**：是中国整体宏观数据，与省级实际现货市场行为差异巨大

2026-06-22 电力数据源穷举调研已确认：

- 山西电力交易中心（`pmos.sx.sgcc.com.cn`）是国内**唯二**正式运行 15min 级现货市场的省份
- 其零售商城子域（`pxf-phbsx-shop`）提供 8 个公开数据查询 API，无需企业认证即可访问
- 经验证：spot_da/spot_rt 接口返回 15min × 24h = 96 点曲线，month_settle 返回逐日分时结算价

## 关键问题 (Why current solution is insufficient)

| 现状 | 不足 |
|---|---|
| OWID 年级数据 | 无法做日内/小时内决策 |
| `electricity_load_hourly.parquet` 示例数据 | 是 2011-2015 历史，非真实现货 |
| 没有省级现货数据接入层 | 无法对标图迹 GeekBidder OS 15min 现货系统 |
| 没有真实出清价 | RL 训练只能用合成奖励，与真实市场脱节 |

## 变更范围 (In Scope)

- ✅ 全量下载山西零售商城 18 个 marketInfo API 历史月份（2018-01~2026-12）至 `ellectric/data/raw/shanxi/`
- ✅ 实现 `ShanxiBaseLoader` 抽象基类 + 3 个子类（spot_da、spot_rt、month_settle）
- ✅ `create_loader()` 工厂扩展 3 个 source key
- ✅ 字段语义化重命名 + 推断置信度标注
- ✅ 写 `data/raw/shanxi/README.md` 数据资产说明

## 不在范围内 (Out of Scope)

- ❌ 不修改 `trading_env.py`/`features.py`/`forecaster.py`/`api/server.py`/`cli/main.py` 等
- ❌ 不做 15min→hourly 聚合（留给后续验证类变更）
- ❌ 不做 24/168 硬编码参数化（留给独立 `time-resolution-param` 变更）
- ❌ 不做训练/回测/SHAP/可视化
- ❌ 不做准实时调度/数据版本管理
- ❌ 不接入广东数据（留给 `gd-spot-data-access` 变更）
- ❌ 不接入剩余 4 个有效但低优先级 API（month_deal、user_transaction、year_trade_fit、time_div_trend），仅原始归档
- ❌ 不实现 `exportPriceData` Excel 导出接入

## 成功标准 (Success Criteria, 可验证)

1. `ellectric/data/raw/shanxi/` 包含 ≥ 200 个有效 JSON 文件（spot_da/spot_rt/month_settle 三类）
2. `ellectric/data/raw/shanxi/README.md` 存在且包含：API 表、字段映射、有效范围、限制说明
3. `from ellectric.pipeline.data_loader import create_loader; create_loader("shanxi_spot_da").load_data()` 返回非空 DataFrame
4. 返回 DataFrame 必须包含列：`timestamp`(UTC datetime64)、`load_mw`、`province`、`source`、`granularity`、`da_price_a`、`da_price_b`
5. `create_loader("shanxi_spot_rt").load_data()` 同样返回 DataFrame，含 `rt_energy_demand`、`rt_energy_supply` 列
6. `create_loader("shanxi_month_settle").load_data()` 返回 2018-01~2026-12 数据，含 `settle_day_price`、`settle_rt_price` 列
7. 现有的 `create_loader("owid")` 调用不受任何影响
8. 不引入新依赖（仅使用 pandas、pathlib 等标准/已有依赖）