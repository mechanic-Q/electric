---
id: task-05
title: 接入 DM/GW 统计检验
author: lmr
created_at: 2026-06-30 11:33:15
priority: P1
depends_on: [task-04]
blocks: [task-06]
requirement_ids: [FR-05]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/scripts/compare_price_models.py
  - ellectric/pipeline/statistical_tests.py
---

goal: >
  将四模型预测误差输入 DM/GW 检验并生成 pairwise table。
implementation:
  - 复用现有 DM/GW helper
  - 对模型两两比较生成 p-value 和 verdict
  - 检验不可用时写 degraded note
acceptance:
  - comparison result 含 statistical_tests
  - 每个模型 pair 有明确状态
  - 缺 epftoolbox 不阻塞 metrics 输出
verify:
  - rtk pytest tests/test_compare_price_models.py
constraints:
  - 不强制安装 epftoolbox
  - 不改变 statistical_tests 既有接口除非必要
