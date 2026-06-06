---
id: task-05
title: 运行 DM/GW 统计检验，输出对比结果
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P1
estimated_hours: 2
depends_on: [task-04]
blocks: [task-06]
allowed_paths:
  - ellectric/data/dmgw_results.json
---

# task-05: 运行 DM/GW 统计检验，输出对比结果

## 修改文件

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `ellectric/data/dmgw_results.json` | DM/GW 检验结果输出文件（JSON），供 task-06 仪表板读取 |

## 实现要求

1. **在 epftoolbox 虚拟环境（venv_epftoolbox）中执行**，不污染主环境
2. 从 `epftoolbox.evaluation` 导入 `dm_test` 和 `gw_test`
3. 对比对象：LEAR 模型（中国数据） vs epftoolbox 5 个基准数据集（EPEX-BE/FR/DE, NordPool, PJM）上预训练 LEAR 基准的预测误差
4. 误差序列以 MAE 为损失函数（loss='MAE'），horizon=24（日前预测）
5. 输出两份表格：
   - **DM 检验表**：含 DM 统计量 + p-value + 显著性判断（p<0.05 标记差异显著）
   - **GW 检验表**：含 GW 统计量 + p-value + 显著性判断
6. 将结果保存为 JSON 文件（`ellectric/data/dmgw_results.json`），供 task-06 仪表板 notebook 读取

## 接口定义

```python
# 核心调用（在 epftoolbox venv 中执行）
from epftoolbox.evaluation import dm_test, gw_test
import numpy as np

# dm_test / gw_test 签名（epftoolbox 原文）
# dm_test(e1, e2, h=1, crit='MAE')
#   e1, e2: 一维 ndarray，两个模型的预测误差序列
#   h: 预测步长，日前预测 = 24
#   crit: 损失函数，支持 'MAE', 'MSE'
#   返回: DM 统计量 (float), p-value (float)
#
# gw_test(e1, e2, h=1, crit='MAE')
#   参数同上
#   返回: GW 统计量 (float), p-value (float)

def run_statistical_tests(
    errors_chinese: np.ndarray,        # LEAR 模型在中国数据上的预测误差 (N,)
    errors_benchmarks: dict[str, np.ndarray],  # {数据集名: 误差序列}
    h: int = 24,
    crit: str = 'MAE'
) -> dict:
    """
    对中国 LEAR vs 5 个基准数据集执行 DM/GW 检验。
    返回:
    {
        'dm_results': [
            {'dataset': str, 'dm_stat': float, 'p_value': float, 'significant': bool},
            ...
        ],
        'gw_results': [
            {'dataset': str, 'gw_stat': float, 'p_value': float, 'significant': bool},
            ...
        ],
        'summary': str   # markdown 表格文本
    }
    """
```

## 边界处理

1. **空误差序列**: 如果 errors_chinese 或某个 errors_benchmarks 为空，跳过该基准，在结果中标记为 "SKIP — no data"
2. **误差序列长度不一致**: 如果中国数据和基准数据长度不同，截取到较短的长度（从尾部对齐，即丢弃最早的部分），并记录警告
3. **全零误差**: 如果误差序列全为 0（恒完美预测），DM/GW 统计量无意义，跳过并标记为 "SKIP — zero error"
4. **NaN/Inf 处理**: 检验前检查误差序列是否包含 NaN 或 Inf，包含则跳过该基准并标记
5. **p-value 边界**: 当 p-value 极小（如 < 1e-300）时，显示为 "< 0.001" 而非科学计数法溢出
6. **缺失基准数据集**: 如果某个基准数据集未下载/不可用（见 task-04），跳过并标记为 "SKIP — dataset unavailable"
7. **h=24 合理性验证**: 如果输入误差序列长度 < 24，抛出 ValueError 并提示最小长度要求

## 非目标

- ❌ 不训练 epftoolbox 模型（仅使用其 evaluation 模块）
- ❌ 不修改 epftoolbox 源码
- ❌ 不在主 Python 环境安装 tensorflow 或 epftoolbox
- ❌ 不实现自定义 DM/GW 算法（直接使用 epftoolbox 已有实现）
- ❌ 不要求 p-value 校正（如 Bonferroni），仅报告单次检验结果
- ❌ 不修改 07_model_comparison_dashboard.ipynb（task-06 唯一创建该 notebook）
- ❌ 不做 plotly 可视化渲染（task-06 负责图表渲染）

## 参考

- epftoolbox evaluation 源码: `https://github.com/jeslago/epftoolbox/blob/master/epftoolbox/evaluation.py`
- Diebold & Mariano (1995) "Comparing predictive accuracy", JBES
- Giacomini & White (2006) "Tests of conditional predictive ability", Econometrica
- 现有设计: `design.md §Wave 2 — epftoolbox 用法`, `design.md §仪表板 Tab 3 — 模型对比`

## TDD 步骤

```
1. [准备] 激活 venv_epftoolbox，验证 `from epftoolbox.evaluation import dm_test, gw_test` 可导入
2. [验证接口] 构造两个随机误差序列（正态分布），调用 dm_test 确认返回 (float, float)
3. [验证 p-value] 输入相同误差序列（e1 == e2），检验 p-value ≈ 1.0（无显著差异）
4. [验证显著性] 构造 e1 = 小误差, e2 = 大误差（e2 = e1 * 10），检验 p-value < 0.05
5. [实现 run_statistical_tests] 编写函数，输出 dict 含 dm_results, gw_results, summary
6. [边界测试] 传入空 dict → 返回空结果 + 合适错误提示
7. [边界测试] 传入含 NaN 的误差序列 → 跳过该基准 + 标记原因
8. [边界测试] 传入长度不等的误差序列 → 尾部对齐 + 记录警告
9. [集成验证] 使用 task-04 下载的 5 个基准数据集运行完整检验
10. [验证] 检查 `ellectric/data/dmgw_results.json` 存在且包含所有 5 个基准数据集的检验结果
```

## 验收标准

**DM 检验输出表**（示例行，实际值因数据而异）:

```
| 基准数据集          | DM 统计量 | p-value   | 显著差异? |
|---------------------|-----------|-----------|-----------|
| EPEX-BE             | 1.234     | 0.218     | No        |
| EPEX-FR             | 2.345     | 0.019     | Yes*      |
| EPEX-DE             | 0.987     | 0.324     | No        |
| NordPool            | 3.456     | 0.001     | Yes**     |
| PJM                 | -1.234    | 0.218     | No        |
```

**GW 检验输出表**（示例行）:

```
| 基准数据集          | GW 统计量 | p-value   | 显著差异? |
|---------------------|-----------|-----------|-----------|
| EPEX-BE             | 1.456     | 0.145     | No        |
| EPEX-FR             | 2.567     | 0.010     | Yes*      |
| EPEX-DE             | 0.789     | 0.430     | No        |
| NordPool            | 4.567     | 0.000     | Yes***    |
| PJM                 | -0.987    | 0.324     | No        |
```

- ✅ 5 个基准数据集全部参与对比（除非标记 SKIP）
- ✅ 显著性标记: * p<0.05, ** p<0.01, *** p<0.001
- ✅ p-value 显示格式: 小数点后 3 位（<0.001 显示为 "< 0.001"）
- ✅ `ellectric/data/dmgw_results.json` 存在且非空
- ✅ JSON 文件包含所有 5 个基准数据集的 dm_results 和 gw_results
- ✅ 每个条目包含 dm_stat, p_value, significant 字段
