---
author: lmr
created_at: 2026-06-06 19:00:00
---

# Proposal

## 动机

Phase 2 的目标是"中国电力市场预测与仿真"。Phase 1 已建立负荷预测管道，
Phase 2 需要将能力扩展到**电价预测**和**市场仿真**两个新维度。

经过 brainstorm 确认，Phase 2 的核心挑战是：

1. **数据切换** — 从 OWID 年级负荷数据切换到中国小时级现货电价（ZionLuo xlsx）
2. **算法切换** — 从 XGBoost 负荷预测切换到 sklearn Lasso 电价预测（LEAR 模型）
3. **框架引入** — 首次引入 ASSUME 电力市场仿真框架
4. **可视化升级** — 从单模型对比升级到多模型仪表板 + Grafana

## 方案选择

经 brainstorm 比较三种方案：

| 方案 | 策略 | 优点 | 缺点 |
|------|------|------|------|
| **A: 顺序递进** | W1 数据+预测 → W2 对比+仪表板 → W3 仿真 | 路径清晰、学习曲线平缓 | 仿真在最后 |
| B: 平行推进 | 预测和仿真同步开发 | 总工期短 | 上下文切换大、依赖混乱 |
| C: 仿真先 | 先装 ASSUME 再回做预测 | ASAP 出可视化 | 预测是仿真的输入，逻辑颠倒 |

**选定方案 A**：顺序递进，3 Wave，预测优先。

## 不在范围内

- PRED-02（OpenSTEF 自动化预测管道）—— 推迟到 Phase 2 之后评估
- 不安装 TensorFlow（epftoolbox 在独立 venv 中仅用基准数据+统计检验）
- 不实现深度神经网络电价预测（LEAR+Lasso 足够）
- 不修改 Phase 1 现有代码

## 成功标准

- NEEDS-01: `price_loader.py` 可加载 ZionLuo xlsx，返回标准 DataFrame（timestamp, price, load）
- NEEDS-02: `price_forecaster.py` 的 LEAR 模型在中国电价数据上完成训练和评估
- NEEDS-03: 预测 notebook 输出 MAE + overlay 图 + 误差分布
- NEEDS-04: epftoolbox 5 基准数据集的 DM/GW 检验输出统计显著性结果
- NEEDS-05: plotly 仪表板显示多模型对比（LEAR vs 基准 vs 持续法）
- NEEDS-06: ASSUME 仿真使用中国省间规则 YAML 启动，Grafana 显示出清价格
