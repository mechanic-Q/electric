---
author: lmr
created_at: 2026-07-03 01:16:03
---

# Decisions: Forecast Fallback Metrics + Today Guard

## D-001@v1: Weather Tier4 指标使用语义化 key + meta

status: accepted
priority: P1

采用 `mae_baseline_tier3`、`mae_weather_tier4`、`mae_delta_pct` 作为稳定 keys，并通过 `metrics_meta` 提供 label/unit。

理由：raw key 缺少实验上下文，前端裸渲染会误导用户。

## D-002@v1: degraded 报告允许 fallback

status: accepted
priority: P1

`ok` 和 `degraded` 报告都允许作为 fallback 来源；`missing/error` 不允许。

理由：degraded 报告仍是可用离线事实，但必须告知质量限制。

## D-003@v1: Agent 必须区分“今天”和“数据集最新可用日”

status: accepted
priority: P1

用户说“今天/当前/实时”时，Agent 必须先说明无真实今日数据源，并询问是否使用数据集最新可用日或历史日期。

理由：项目是历史数据学习平台，不是实时预测系统。

## D-004@v1: 前端指标渲染向后兼容

status: accepted
priority: P2

`renderMetrics` 优先使用 `metrics_meta`，没有 meta 时继续展示原始 key/value。

理由：避免破坏 renewable/price/RL 等已有报告卡片。
