---
author: lmr
created_at: 2026-06-25T00:35:00+08:00
---

# 山东 15min MVP 数据切换 — 功能需求

## FR-001: ShandongDataLoader

**Given** Shandong CSV 位于 `ellectric/data/shandong/`
**When** 调用 `create_loader("shandong").load_data()`
**Then** 返回 DataFrame 含 timestamp (UTC), load_mw, rt_price, wind_actual_mw, solar_actual_mw, province="shandong", granularity="15min"

## FR-002: 日期范围过滤

**Given** 数据覆盖 2024-01-01 ~ 2026-01-14
**When** `load_data("2024-06", "2024-08")`
**Then** 返回该日期范围内所有 15min 行

## FR-003: 工厂注册

**Given** `create_loader("shandong")`
**When** 在 data_loader.py 中调用
**Then** 返回 ShandongDataLoader 实例，与其他 source key 行为一致

## FR-004: TimeConfig 默认 15min

**Given** 项目启动
**When** `from ellectric.config import TimeConfig; print(TimeConfig.points_per_day)`
**Then** 输出 96（非 24）

## FR-005: 删除山西模块

**Given** 山西数据已经被判定为参考价无后续价值
**When** 本次变更完成后
**Then** ellectric/pipeline/shanxi_loader.py 不存在，create_loader("shanxi_spot_da") 抛 ValueError

## FR-006: 气象接入

**Given** WeatherFetcher 模块可用
**When** `fetcher.fetch_historical("2024-01", "2024-06")`
**Then** 返回 DataFrame 含济南/青岛的小时气象数据

## FR-007: Notebook 可运行

**Given** 11 个 notebook 已重写
**When** 用户依次运行
**Then** 每个 notebook 使用 shandong 数据源，无 import 错误，无 山西/OWID 残留引用

## NFR-001: 无新依赖

不引入新 Python 包。气象用 urllib，CSV 用 pandas（已有）。

## NFR-002: 向后兼容现有 API

CLI / API / LLM 接口不因数据源切换而改变响应结构。
