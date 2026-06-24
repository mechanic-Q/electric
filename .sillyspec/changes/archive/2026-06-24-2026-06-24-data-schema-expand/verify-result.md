---
author: lmr
created_at: 2026-06-24T01:00:00+08:00
---

# Verify Report — 数据 schema 扩展

## 总体结论

**PASS** ✅ — 37/37 验证通过 (上次 24/24 + 新增 13 项), 0 失败.

## 质量指标

| 指标 | 值 |
|---|---|
| verify 脚本通过率 | 37/37 (100%) |
| 语法检查 | 3/3 OK |
| 5 新 source 真实数据 | 3 个非空 (744/1007/912 行), 2 个数据空 (合理) |
| 性能 | 单 loader load_data < 5s |
| 决策覆盖 | D-001~D-003@v1 全实现 |

## 真实数据加载

| Source | 行数 | granularity | 状态 |
|---|---|---|---|
| shanxi_month_deal | 0 | daily | 数据空(接口返空 list) |
| shanxi_user_transaction | 0 | daily | 数据空 |
| shanxi_year_trade_fit | 744 | month-curve | ✅ |
| shanxi_month_settle1 | 1007 | daily-point | ✅ |
| shanxi_time_div_trend | 912 | time-div | ✅ |

## 现有验证回归

24 项 (shanxi_spot_da/rt/month_settle + 优雅降级 + owid/ember 兼容) 全部通过.

## 已知限制

1. month_deal / user_transaction 实际数据全空 (接口 dateList=[]) - 不是代码 bug
2. 字段含义 inferred (无官方文档)
3. 月度 ≠ 逐日历史 (沿用 shanxi-spot 限制)

PR: https://github.com/mechanic-Q/electric/pull/9
