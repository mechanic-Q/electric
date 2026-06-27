---
author: lmr
created_at: 2026-06-28 00:57:11
---

# Proposal

## 动机

WeatherFetcher Tier4 气象特征已经接入 `FeatureEngineer`，但当前只证明了接口层可用，还没有形成面向学习者的可复现验证闭环。本变更要把 Weather Tier4 从“已接入”推进到“可验证”：检查天气数据是否正确合并到山东 15min 负荷时间轴，并量化 Tier1-3 baseline 与 Tier1-4 weather 特征的预测指标差异。

## 关键问题

1. **接入正确性不可见**：现有 Tier4 会按 weather_df / cache / fetch / degraded 优先级运行，但缺少统一报告说明本次到底使用了哪个来源、哪些 weather 列被合并、缺失率和时间覆盖是否合理。
2. **精度影响不可复现**：notebook 手动观察不适合作为稳定验收；需要脚本在同一默认数据、同一模型配置、同一时序切分下生成 baseline vs Tier4 指标。
3. **Weather 不提升容易被误判为失败**：架构文档明确 Tier4 是可选增强，不保证精度提升；因此首轮应采用报告式验证，而不是硬性阈值验收。

## 变更范围

- 新增 Weather Tier4 验证脚本入口。
- 复用默认山东 15min 数据和现有 `FeatureEngineer` / `XGBoostForecaster`。
- 显式解析 weather 来源：cache / fetch / degraded。
- 检查 weather 字段、时区、缺失、覆盖范围、15min 对齐后空值。
- 运行 Tier1-3 baseline 与 Tier1-4 weather 对比实验。
- 输出 JSON 和 Markdown 报告。
- 新增测试覆盖报告 schema、降级行为、指标 delta。
- 更新 feature-engineer 模块文档，补充验证入口。

## 不在范围内（显式清单）

- 不新增或更换天气数据源。
- 不把 Weather Tier4 改成必选特征。
- 不设置 MAE/RMSE/MAPE 硬性提升阈值。
- 不修改现有 `FeatureEngineer`、`prepare_features`、`XGBoostForecaster` 的公开 API。
- 不改动 API、CLI、LLM、交易仿真或真实交易逻辑。
- 不新增 notebook-only 流程作为唯一验证方式。
- 不持久化生产模型。

## 成功标准（可验证）

- 运行 `python ellectric/scripts/validate_weather_tier4.py` 后生成 JSON 和 Markdown 报告。
- JSON 报告包含 `metadata`、`weather_quality`、`experiments`、`interpretation` 四个顶层字段。
- 报告明确记录 weather 来源、weather 列清单、缺失率、覆盖范围和是否降级。
- 报告包含 baseline_tier3 与 weather_tier4 的 MAE、RMSE、MAPE、feature_count、input_rows、sample_count。
- 报告包含指标 delta，且 `hard_threshold_applied=false`。
- weather cache 缺失且禁用 fetch 时，脚本不因 Tier4 缺失崩溃，而是在报告中记录 degraded。
- 新增测试覆盖报告结构、降级路径和指标计算。
- 未运行新脚本时，现有数据加载、特征工程、预测、测试行为不变。
