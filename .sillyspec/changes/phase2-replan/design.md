# Phase 2 计划重设计 — 完全中国化

author: lmr
created_at: 2026-06-06T17:30:00+08:00

## 背景

Phase 1 已建立中国电力负荷预测管道（OWID + XGBoost）。Phase 2 原计划基于 epftoolbox + ASSUME 的进口工具组合，经 explore 审计发现：

1. **epftoolbox 不可安装** — 依赖 TensorFlow/Keras，与 ASSUME 的 PyTorch 冲突
2. **数据全是欧美** — epftoolbox 5 个数据集（EPEX-BE/FR/DE, NordPool, PJM）无一中国
3. **中国电价数据已有** — 发现 ZionLuo/Electricity-Price-Forecasting 含中国省级现货电价 `price data.xlsx`

结论：Phase 2 必须从「学进口工具」转为「中国电力市场预测与仿真」。

## 设计目标

1. 电价预测完全基于中国数据
2. LEAR 模型用 sklearn.Lasso 替代 epftoolbox 的 TF 实现
3. ASSUME 仿真配置适配中国省间现货规则
4. Phase 1-4 全局统一"中国电力数据优先"原则

## 非目标

- 不实现 LEAR 代码（本次只改计划文档）
- 不安装 ASSUME（Phase 2 执行时才做）
- 不修改现有 Python 源码
- 不新增 notebook

## 总体方案

修正 5 份计划文档，建立"完全中国化"的 Phase 2-4 框架：

```
┌──────────────────────────────────────────────────────────┐
│                    数据层                                 │
│  Phase 1: OWID 中国负荷 + 手动日/小时数据                  │
│  Phase 2: 新增 DATA-05 — 中国现货电价 (ZionLuo xlsx)       │
├──────────────────────────────────────────────────────────┤
│                    预测层                                 │
│  Phase 1: XGBoost 负荷预测 (已有)                         │
│  Phase 2: PRED-03 — sklearn LEAR 电价预测                  │
│           epftoolbox 5 数据集仅用于基准对比 + DM/GW 检验    │
├──────────────────────────────────────────────────────────┤
│                    仿真层                                 │
│  Phase 2: SIM — ASSUME 配置中国省间现货规则                 │
│  Phase 3: AGENT — RL 回测用中国市场事件                    │
├──────────────────────────────────────────────────────────┤
│                    UI 层                                  │
│  Phase 4: LLM — 中文电力市场术语 + 中国电力知识库           │
└──────────────────────────────────────────────────────────┘
```

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `.planning/REQUIREMENTS.md` | 新增 DATA-05, 重写 PRED-03, 修正 SIM-02 |
| 修改 | `.planning/ROADMAP.md` | 重写 Phase 2 目标和成功标准（全部中国化） |
| 修改 | `.planning/research/STACK.md` | epftoolbox 降级为数据源, 新增 sklearn.Lasso |
| 修改 | `.planning/research/SUMMARY.md` | 关闭 epftoolbox gap, 标记 ASSUME 中国配置 |
| 修改 | `.planning/phases/.../01-RESEARCH.md` | 关闭 "epftoolbox LEAR reimplementation" gap |

### 不变的文件

- PITFALLS.md — 反模式与中国化无关，保持不变
- ARCHITECTURE.md — 架构层次不变，数据源替换不改变分层
- FEATURES.md — 功能列表不变，LEAR 实现是 PRED-03 的具体化

## 需求映射

### REQUIREMENTS.md 新增/修改

```
DATA-05: 中国电价数据接入
  来源: ZionLuo/Electricity-Price-Forecasting-with-Hybrid-Transformer
        price data.xlsx
  字段: 日前价格, 实时价格, 统调负荷, 新能源出力, 省间联络线
  量级: ~2000 条小时级数据
  Phase: 2

PRED-03 (重写): 使用 sklearn.Linear_model.Lasso 实现 LEAR 日前电价预测
  方法: LASSO 回归 + 滞后特征 + 日历特征
  训练: 中国现货电价数据 (DATA-05)
  基准: epftoolbox 5 数据集 (EPEX-BE/FR/DE, NordPool, PJM)
        仅用于: DM 检验、GW 检验、跨市场对比
  指标: MAE (Phase 1 已统一)
  Phase: 2

SIM-02 (修正): 通过 YAML 配置修改发电组合和出清机制
  原: 不指定市场
  新: 优先配置中国省间现货市场规则（报价上下限、偏差考核、新能源优先调度）
  Phase: 2
```

### ROADMAP.md Phase 2 重写

```
Phase 2: 中国电力市场预测与仿真
  目标: 
    - 基于 sklearn LEAR 实现中国日前电价预测
    - 使用 epftoolbox 基准数据集验证方法正确性
    - 配置 ASSUME 中国省间现货仿真环境
    - 建立多模型对比仪表板

  成功标准:
    1. sklearn LEAR 在中国电价数据上 MAE < epftoolbox LEAR baseline
    2. 多模型对比仪表板显示 XGBoost vs LEAR 误差按时段分布
    3. ASSUME 7 天仿真使用中国省间规则，Grafana 显示出清价格
    4. 修改发电组合 YAML 后出清价格合理变化
    5. 中国电价数据的 DM/GW 检验结果对比 EPEX 基准

  风险:
    - 中国电价数据量有限 (~2000 条)，可能影响深度模型效果
    - ASSUME 中国省间规则需额外配置，无官方模板
```

## 自审

| 检查项 | 结果 |
|--------|------|
| 需求覆盖 | ✅ DATA-05/PRED-03/SIM-02 全部覆盖 |
| 约束一致性 | ✅ MAE 唯一指标、中文命名、plotly 可视化 |
| 真实性 | ✅ 数据源 ZionLuo 已确认存在，epftoolbox 5 数据集已确认 |
| YAGNI | ✅ 只改计划文档，不新增功能 |
| 验收标准 | ✅ LEAR MAE < baseline, 中国规则仿真可运行 |
| 非目标清晰 | ✅ 不实现代码，不安装 ASSUME |
| 兼容策略 | ✅ 纯文档修改，不影响现有代码 |
| 风险识别 | ✅ 数据量、ASSUME 配置风险已登记 |
