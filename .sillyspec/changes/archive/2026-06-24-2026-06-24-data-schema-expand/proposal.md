---
author: lmr
created_at: 2026-06-24T00:10:00+08:00
---

# Proposal — 数据 schema 扩展

## 动机

变更 #7 (shanxi-spot-data-access) 接入了 3 个核心 API（spot_da/spot_rt/month_settle），D-006@v1 决策"暂仅接入 3 个"，其余 5 个有效 API 已下载但未实现 loader：

- `month_deal` — 批发市场中长期成交（购方/售方 × 日期 × 电量 × 价格）
- `user_transaction` — 用户侧成交（市场主体 × 日期 × 电量 × 价格）
- `year_trade_fit` — 年度交易各标的月拟合分时价格曲线（标的 × 96点）
- `month_settle1` — 月度统一结算点电价（与 month_settle 同结构）
- `time_div_trend` — 分时浮动项历史参考值（series × 96点）

本变更补完。

## 关键问题

1. **完整字段覆盖**：缺少中长期/用户侧成交、年度拟合曲线、分时浮动项，无法做完整的电力市场行为分析
2. **数据浪费**：原始 JSON 已下载 1947 个文件，5 个 API 数据被搁置
3. **未来扩展低门槛**：抽象基类 ShanxiBaseLoader 已就绪，每个子类只需 30 行

## 变更范围

- 5 个新 loader 子类（继承 ShanxiBaseLoader）
- create_loader 扩展 5 个 source key（延迟导入）
- verify_shanxi_loader 扩展验证段
- 字段语义化重命名 + inferred 标注

## 不在范围内

- ❌ 不修改任何已有 loader（spot_da/spot_rt/month_settle/base）
- ❌ 不抓取新数据（数据已在 raw/shanxi/）
- ❌ 不做特征工程对新字段建模
- ❌ 不扩展 cleaner/forecaster 等下游模块
- ❌ 不新增依赖

## 成功标准

1. `create_loader("shanxi_month_deal")` 返回 ShanxiMonthDealLoader，load_data 非空
2. `create_loader("shanxi_user_transaction")` 同上
3. `create_loader("shanxi_year_trade_fit")` 同上
4. `create_loader("shanxi_month_settle1")` 同上
5. `create_loader("shanxi_time_div_trend")` 同上
6. 现有 verify_shanxi_loader 24 项验证保持通过（回归）
7. 扩展后总验证 ≥ 35 项（24 + 新增 5 source × 至少 2-3 项）
8. shanxi_loader.py 现有 4 类源码零修改
9. requirements.txt 不变
