---
author: lmr
created_at: 2026-06-06 18:00:52
---

# Requirements

## 角色

| 角色 | 说明 |
|------|------|
| 开发者 | Phase 2 学习者，已掌握 Phase 1 XGBoost 负荷预测 |
| 系统 | Ellectric 平台，提供数据、模型、仿真集成环境 |

## 功能需求

### FR-01: 中国电价数据接入

Given 开发者已克隆 Ellectric 项目
When 按照中国电价数据指南下载 ZionLuo/price data.xlsx 到 data/ 目录
Then DataLoader 支持加载电价数据，返回 timestamp + price + load 的标准 DataFrame

### FR-02: sklearn LEAR 电价预测

Given 中国电价数据已就绪
When 开发者运行 sklearn.Lasso 实现的 LEAR 模型
Then 模型在中国数据上训练完成，MAE 输出可解释的日前电价预测值

### FR-03: epftoolbox 基准对比

Given sklearn LEAR 在中国数据上训练完成
When 使用 epftoolbox 的 5 个 benchmark 数据集运行 DM/GW 统计检验
Then 对比结果显示中国模型与 EPEX 基准的统计显著性差异

### FR-04: 中国省间现货仿真

Given ASSUME 已安装
When 使用中国省间规则 YAML 配置启动仿真
Then Grafana 显示出清价格、各发电主体调度、省间联络线功率

### FR-05: 发电组合修改

Given 中国省间现货仿真在运行
When 修改发电组合 YAML（增大风电占比、减少煤电）
Then 出清价格和调度策略按预期变化

## 非功能需求

- 兼容性：Phase 1 代码无需任何修改
- 可回退：计划文档修改通过 git 管理，可回滚到修正前版本
- 可测试：每个成功标准都是可验证条件，修改后 grep 确认文档内容
