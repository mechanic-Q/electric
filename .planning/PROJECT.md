# AI + 电力交易技术学习平台

## What This Is

一个动手实践性质的AI+电力交易技术学习项目。基于北京图迹科技(GeekBidder)的技术画像——大数据平台 + AI时序预测模型 + 电力市场仿真 + 自动交易智能体——使用开源替代方案搭建可运行的技术原型。目标是帮助开发者掌握"数据获取 → 负荷预测 → 市场仿真 → 自动交易"的完整技术闭环。

This is a hands-on learning platform for AI-driven electricity trading — it's NOT a production trading system. All data is public, all tools are open-source.

## Core Value

跑通"公开电力数据接入 → 负荷/电价预测 → 电力市场仿真 → 自动交易策略"的端到端技术闭环。

## Context

### 技术灵感来源
北京图迹科技(GeekBidder)是国内AI电力交易领域的代表性公司，其技术栈推测包括：
- **核心引擎**: 自研电力交易大模型GeekModel、深度状态空间模型(风功率预测)、DeepSeek集成
- **核心平台**: GeekBidder OS (数据+算法+策略综合操作系统)
- **数据基础**: 30TB+高质量电碳数据、Hadoop/Spark大数据架构
- **应用层**: 数据机器人、自动交易机器人、自然语言交互智能体"图小记"

### 开源替代方案
| 工具 | 用途 | GitHub |
|------|------|--------|
| ASSUME | 电力市场仿真 (强化学习) | github.com/assume-framework/assume |
| OpenSTEF | 短期负荷预测 (自动化ML管道) | github.com/OpenSTEF/openstef |
| enda | 能源时序数据处理 | github.com/enercoop/enda |
| HAMLET | 本地能源市场仿真 (ABM) | github.com/HAMLET-org/HAMLET |
| epftoolbox | 电价预测工具箱 | github.com/jeslago/epftoolbox |

### 公开数据源
- IEA Real-Time Electricity Tracker (多国电力需求/价格)
- PUDL (美国EIA清洗后数据, github.com/catalyst-cooperative/pudl)
- 国家能源局 (中国宏观电力统计数据)
- 菏泽市公共数据开放网 (区域电力公共数据)

### 学习路线 (4阶段)
1. **热身与基础预测**: Python基础 → 数据获取 → 简单预测模型 (2-4周)
2. **深入预测与市场仿真**: OpenSTEF + ASSUME 上手 (4-8周)
3. **交易智能体**: 预测+仿真整合 → RL策略 (8-12周)
4. **整合与大模型赋能**: FastAPI后端 + LangChain + LLM交互

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **ENV-01**: 搭建Python开发环境，安装核心依赖(pandas, numpy, scikit-learn, xgboost)
- [ ] **DATA-01**: 从PUDL或IEA接入公开电力数据，完成数据清洗
- [ ] **PRED-01**: 使用XGBoost构建短期负荷预测模型
- [ ] **PRED-02**: 运行OpenSTEF自动化预测管道，对比手动模型效果
- [ ] **SIM-01**: 安装并运行ASSUME电力市场仿真环境
- [ ] **SIM-02**: 使用epftoolbox进行电价预测
- [ ] **AGENT-01**: 将OpenSTEF预测结果接入ASSUME智能体决策
- [ ] **AGENT-02**: 修改ASSUME强化学习智能体的奖励函数和策略
- [ ] **INTG-01**: 搭建FastAPI后端，集成数据获取+预测+策略功能
- [ ] **INTG-02**: 集成LangChain + LLM API，实现自然语言交易指令解析

### Out of Scope

- 真实电力市场交易下单 — 仅模拟，不涉及真实资金
- 商业级生产系统 — 学习目的，不考虑高可用、安全合规
- 图迹GeekBidder OS复现 — 使用开源替代方案，不尝试逆向商业软件
- 实时交易数据接入 — 仅使用历史和公开数据集
- 多维度的碳交易市场 — 聚焦电力交易，碳市场作为延展方向

## Constraints

- **数据**: 仅使用公开可获取的数据集，不涉及商业数据购买
- **工具**: 全部使用开源工具和框架
- **模型**: 轻量级模型为主 (XGBoost, LSTM, 小型RL)，不训练大模型
- **硬件**: 普通开发机可运行 (不需要GPU集群)
- **语言**: Python 3.10+

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 使用ASSUME而非自建仿真 | 成熟的电力市场RL仿真框架，避免重复造轮子 | — Pending |
| 使用PUDL作为主要数据源 | 已清洗的美国电力数据，可直接用于建模 | — Pending |
| 4阶段垂直MVP结构 | 每个阶段产出可运行的端到端结果，符合学习目标 | — Pending |
| 优先XGBoost而非深度学习 | 快速验证预测可行性，降低入门门槛 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-20 after initialization*
