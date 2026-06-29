---
author: lmr
created_at: 2026-06-28 04:50:00
---

# Roadmap: Ellectric (AI + 电力交易技术学习平台)

> **2026-06-28 更新：路线图已根据图迹对齐后的 Phase 4 Closeout 结论重写。**
> 历史 Phase 2/3 计划已过时（基于山西数据和非回归路线），详见 wiki `entities/lmr-electric.md`。

## Overview

一个动手实践性质的 AI+电力交易技术学习项目。核心价值是跑通"公开电力数据接入 → 负荷/电价预测 → 电力市场仿真 → 自动交易策略"的端到端技术闭环。

**数据已切换到山东 15min 真实出清数据**（745 天 × 96 点 = 71,520 行），山西调研结论归档。
**Phase 4 主线已基本完成，进入持续改进阶段。**

## Phases

### Phase 1: Data Foundation + Basic Prediction ✅

**状态:** shipped (2026-06-06)
**核心交付:**
- 项目脚手架 (setup.sh, requirements.txt)
- OWID/Chinese/Shandong 三级 DataLoader
- 数据清洗管道 (缺失填充、IQR 报告、UTC 标准化)
- 渐进式特征工程 (Tier1→Tier2→Tier3→Tier4 可选)
- XGBoost 负荷预测 + TimeSeriesSplit
- 11 个渐进式学习 Notebook

### Phase 2: 中国电力市场预测与仿真 ⚠️ 已过时

**原计划已终止。** 原始设计基于：
- OpenSTEF 自动化预测管道 → 未实施，且与山东 15min 数据不兼容
- ASSUME 中国省间现货仿真 → 未实施，依赖 Grafana/TimescaleDB 太重
- epftoolbox 基准对比 → 学习价值有限

**现有替代能力:**
- `price_forecaster.py` — LEAR Lasso 电价预测（山东日前/实时价格）
- `statistical_tests.py` — DM/GW 统计检验

### Phase 3: Trading Agents + Backtesting ⚠️ 已过时

**原始计划已终止。** 原设计基于 ASSUME 多智能体仿真框架。

**现有替代能力（代码层面已实现，等待 96 维全量训练验证）:**
- `trading_env.py` — ElectricityMarketEnv (gym.Env)，观测/动作/奖励已设计
- `rl_trainer.py` — PPO/SAC/TD3 智能体 + 工厂模式
- `backtester.py` — backtest runner + 3 基线策略 (persistence/mean/oracle)
- `shap_explainer.py` — XGBoost/LEAR 可解释性

### Phase 4: Integration + LLM Interface ✅ 持续改进

**状态:** 主线已完成，持续改进中

**已完成:**
- FastAPI 三层接口 (REST API + SSE Web Chat)
- Typer CLI 命令行框架
- LangChain + DeepSeek LLM Agent
- SHAP 模型可解释性
- WeatherFetcher Tier4 气象特征集成
- Weather Tier4 验证脚本与报告 ✅ (2026-06-28 归档)

**持续改进项（优先级排序）:**
1. ✅ 完整 96 维 RL training on full dataset — `python -m ellectric.scripts.train_rl_full_dataset`（见 `ellectric/reports/rl_full_dataset/training_report.md`）
2. Weather 特征精度影响量化（首轮报告已完成，后续随模型迭代持续观察）

**显式排除（不可协商）:**
- 准实时 T+15min 调度 — 数据源结构性不支持
- 中长期合约串 pipeline — 增强项，当前不做
- 多省/多节点市场覆盖 — MVP 保持单省山东
- 真实交易/付费数据源 — 学习原型，不涉及真实资金

## Progress

| Phase | Status | Completed | Notes |
|-------|--------|-----------|-------|
| 1. Data Foundation + Basic Prediction | ✅ Shipped | 2026-06-06 | 山西/山东数据管道 + XGBoost |
| 2. 中国电力市场预测与仿真 | ⚠️ Obsolete | — | 目标已吸收至 Phase 4，OpenSTEF/ASSUME 不跟进 |
| 3. Trading Agents + Backtesting | ⚠️ Obsolete | — | RL 环境/训练器/回测器代码已存在，等待 96 维全量训练 |
| 4. Integration + LLM Interface | ✅ Shipped (CB) | 2026-06-28 | API/CLI/LLM/SHAP/Tier4 全部完成，进入持续改进 |

## 相关 Wiki

- entities/lmr-electric.md — 项目实体与详细技术架构
- synthesis/electric-phase4-closeout-20260627 — Phase 4 收尾决策
- synthesis/electric-data-requirements-vs-tuji-20260622 — 图迹数据粒度对标
- synthesis/shandong-mvp-switch-20260625 — 山东切换记录
