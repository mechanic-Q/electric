---
author: lmr
created_at: 2026-06-10 13:30:00
---

# Proposal — 中国电力数据更新

## 动机

Ellectric 项目的中国电力数据停留在 2017 年，无法获取最新数据。实际上 OWID 上游已更新到 2025 年，但项目缺少可靠的拉取机制，在国内网络环境下经常失败。需要更新数据并加固拉取链路。

## 关键问题

### 1. 单点网络依赖，国内常不可用
当前硬编码 `raw.githubusercontent.com` 作为唯一数据源。该域名在中国大陆被 GFW 阻断或不稳定，导致拉取超时。OWID 实际上有官方 CDN (`owid-public.owid.io`)，更稳定但未使用。

### 2. 无本地缓存，网络断则完全不可用
每次 `load_data()` 都发起 HTTP 请求，无本地缓存。即使曾经成功拉取过，下次网络中断也无法使用历史数据。

### 3. 只有年度数据，缺少高时间分辨率数据
当前仅有 OWID 年度数据（年级 TWh → 日均 MW），无法支持小时级/日级的负荷预测、电价预测等后续阶段。Ember Climate 提供了小时级数据但项目未接入。

## 变更范围

- OWID 数据拉取 3 级回退（CDN → GitHub → 本地缓存）
- 本地 Parquet 缓存机制（成功后自动写缓存）
- 新增 `EmberLoader` 探索小时级数据
- 工厂函数 `create_loader()` 注册 `ember` 源
- 文档更新（README + INTEGRATIONS + 新增 data-sources.md）
- 全管道 notebook 验证

## 不在范围内（显式清单）

- 不引入 PUDL、ENTSO-E、pypsa 等重型专业库
- 不修改 cleaner/features/forecaster 下游模块
- 不新增 CLI/API 接口
- 不做数据版本对比/数据质量评分
- 不修改 ChineseDataLoader 现有逻辑

## 成功标准（可验证）

- [x] `create_loader("owid").load_data()` 返回 2025 年数据
- [x] CDN 不可用时自动回退到 GitHub raw
- [x] 网络全断时从本地缓存加载（不抛异常）
- [x] `create_loader("owid")` / `"manual"` / `"file"` 向后兼容
- [x] notebook 01→05 全流程跑通，图表显示最新年份
- [x] 文档新增数据源一览页
