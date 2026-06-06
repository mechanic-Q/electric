---
author: lmr
created_at: 2026-06-06 18:00:52
---

# Proposal

## 动机

Phase 1 已建立中国电力负荷预测管道。Phase 2 原计划基于 epftoolbox + ASSUME 的进口工具组合，但 explore 审计发现两个关键问题：

1. epftoolbox 依赖 TensorFlow/Keras，与 ASSUME 的 PyTorch 冲突，无法安装
2. epftoolbox 5 个数据集（EPEX-BE/FR/DE, NordPool, PJM）无一覆盖中国市场

## 关键问题

- **epftoolbox 不可用**：PRED-03 原计划"使用 epftoolbox 进行电价预测"无法执行，LEAR 模型需要替代方案
- **数据全是欧美**：进口工具成熟但数据与中国脱节，学习者无法将方法应用到中国场景
- **市场规则不匹配**：ASSUME 预设德国 EPEX 规则，中国省间现货市场（报价上下限、偏差考核、新能源优先调度）需要自定义配置

## 变更范围

修正 5 份 Phase 2 计划文档，实现"完全中国化"：

1. REQUIREMENTS.md — 新增 DATA-05（中国电价数据），重写 PRED-03（sklearn LEAR），修正 SIM-02（中国省间规则）
2. ROADMAP.md — Phase 2 目标、成功标准、风险全面中国化
3. STACK.md — epftoolbox 降级为基准数据源，新增 sklearn.Lasso
4. SUMMARY.md — 关闭 epftoolbox gap
5. 01-RESEARCH.md — 标记 LEAR gap 已解决

## 不在范围内（显式清单）

- 不实现 LEAR 代码（Phase 2 执行时才做）
- 不安装 ASSUME 或 epftoolbox
- 不修改现有 Python 源码
- 不新增 notebook
- 不修改 PITFALLS.md、ARCHITECTURE.md、FEATURES.md

## 成功标准（可验证）

- NEEDS-01: REQUIREMENTS.md 含 DATA-05，明确中国电价数据源和数据格式
- NEEDS-02: PRED-03 描述从 "epftoolbox 预测" 改为 "sklearn LEAR + epftoolbox 基准对比"
- NEEDS-03: STACK.md epftoolbox 用途从 "价格预测" 改为 "基准数据 + 评估工具"
- NEEDS-04: Phase 2 成功标准 3 提及中国省间现货规则
- NEEDS-05: SUMMARY.md 的 "epftoolbox LEAR reimplementation" gap 标记为 ✅ 已解决
