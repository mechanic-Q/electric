---
author: lmr
created_at: 2026-06-30 04:00:47
---

# Proposal: 电价模型对比报告

## 动机

Ellectric 已有 LEAR(Lasso) 电价预测与统计检验模块，但尚未把 LEAR、DNN、naive baseline 放在山东数据上做统一对比。图迹业务强调多模型预测与策略评估，本变更补齐“电价预测模型选择”这一教学环节。

本轮采用 PyTorch MLP 作为 DNN baseline，避免 TensorFlow/epftoolbox 与主环境冲突；数据范围先限定山东。

## 变更范围

- 新增 PyTorch DNN 电价预测器。
- 新增比较脚本：LEAR / DNN / persistence / weekly_avg。
- 复用 `statistical_tests.py` 做 DM/GW 显著性检验。
- 输出 JSON、Markdown、Plotly 残差图、运行日志。
- 可选扩展 service/CLI 支持 `model_type="price_dnn"`。

## 不在范围内

- 不引入 TensorFlow。
- 不跑 epftoolbox 5 个海外市场基准数据集。
- 不调参刷榜。
- 不替代现有 LEAR 默认模型。
- 不做生产级模型注册。

## 成功标准

- 同一山东数据切分下输出四类模型指标。
- DM/GW 表显示 LEAR/DNN/naive 的显著性对比。
- `comparison.json`, `comparison.md`, `residuals.html`, `comparison.log` 生成。
- 单元测试覆盖 DNN 快速训练、比较脚本 schema、统计检验调用。
