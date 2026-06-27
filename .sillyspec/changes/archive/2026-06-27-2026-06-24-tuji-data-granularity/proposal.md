---
author: lmr
created_at: 2026-06-26 21:12:40
---

# Proposal

## 动机

Electric 当前 MVP 已拥有山东 15min 现货数据资产，但代码和文档中仍存在小时级假设：固定 `24/168` 点窗口、固定小时级重采样、TradingEnv `24` 维动作提示、API handler 固定加载 OWID 年级数据。继续保留这些残留会让学习者以为系统已迁移到 15min，实际训练、预测、回测仍按小时级或年级路径运行。

本变更要把现有小时级数据模型全面升级为 15min 粒度，让数据接入、清洗、特征、预测、交易环境、接口与文档围绕同一套 15min 时间语义工作。

## 关键问题

1. **时间窗口语义不一致**：`TimeConfig` 已声明 15min 默认值，但 `features.py`、`price_forecaster.py`、`forecaster.py`、`trading_env.py` 中仍有 `24/168` 点数或小时级提示，容易导致 lag、rolling、gap 与真实 15min 数据错位。

2. **频率规范化存在降采样风险**：`cleaner.standardize_frequency()` 当前存在把非目标频率重采样到小时级的逻辑，这与山东 15min canonical 数据资产冲突。

3. **接口层仍绕开 15min 数据源**：`ForecastRequest` / `BacktestRequest` 虽有 `data_source` 字段，但 handlers 固定使用 OWID 或旧 price loader，无法让 CLI/API/LLM 路径默认走山东 15min 数据。

## 变更范围

- 统一 `TimeConfig` 作为时间分辨率 Single Source of Truth。
- 修正清洗、特征、预测、交易环境中的硬编码窗口和小时级提示。
- 保持 `lag_24h`、`load_forecast_24h` 等字段名表达时间跨度，而不是固定点数。
- 让 Forecast/Backtest/Explain 相关 schema 和 handler 支持或默认使用 `shandong` 数据源。
- 更新 CLI/API/LLM/notebook/README/module docs 中的 15min 语义。
- 新增最小测试覆盖 15min lag、rolling、frequency 和 TradingEnv action shape。

## 不在范围内（显式清单）

- 不做通用多频率平台。
- 不新增复杂 runtime 配置系统。
- 不自动把小时级低频数据插值为 15min 真值。
- 不重写模型架构或新增算法。
- 不改真实市场结算逻辑。
- 不删除 OWID/ChineseDataLoader/EmberLoader 兼容路径。

## 成功标准（可验证）

- `TimeConfig.points_per_day == 96`、`points_per_week == 672`、`freq == "15min"` 时，1 天/1 周相关 lag 与 rolling 特征按 96/672 点计算。
- `standardize_frequency()` 对 15min 输入不降采样到小时级。
- `TradingEnv.action_space.shape == (96,)`，错误信息不再写死 “24 维”。
- Forecast/Backtest schema 的 `data_source` 支持 `shandong`，handler 不再无视该字段固定加载 OWID。
- CLI/API/LLM 文案中 `horizon=24` 表示 24 小时时间跨度；15min 数据下内部可对应 96 点。
- README、module docs、notebook 文案与当前山东 15min MVP 一致。
- 新增测试通过，且不破坏现有 public API 名称。
