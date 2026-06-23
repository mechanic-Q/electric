---
author: lmr
created_at: 2026-06-23T19:10:00+08:00
---

# Decisions — 时间分辨率参数化

## D-001@v1 — 全局配置单例（方案 A）

**决策**：新建 `ellectric/config.py` 定义 `TimeConfig` 类，所有 pipeline 模块统一引用。

**备选**：
- 方案 B：模块级注入（被拒：5 个文件每个 init 都改一遍，调用点全部改）
- 方案 C：环境变量驱动（被拒：调试困难，魔法太多）

**理由**：Electric 是学习项目非生产，全局配置最简。切换 15min 时只需改 3 个属性值，不需要重启进程或改环境变量。

**覆盖**：FR-001

## D-002@v1 — 逐文件精确替换（方案 1）

**决策**：每个文件逐个 grep 找硬编码 24/168/`"h"`，精确替换为 `TimeConfig.points_per_day` / `points_per_week` / `freq` 引用。

**备选**：
- 方案 2：批量替换脚本（被拒：批量可能漏边界，比如 docstring/注释中的 24 不该替换）
- 方案 3：保留默认值 24 + 加新值通道（被拒：默认值不明确，使用方易迷惑）

**理由**：trading_env.py 91 处提及 24/168 但只有约 30 处真的需要替换（其余是 docstring/注释），需要逐处人工判断。

**覆盖**：FR-002~FR-006

## D-003@v1 — 默认值保持小时级

**决策**：`TimeConfig.points_per_day=24`、`points_per_week=168`、`freq="h"` 为默认值，与现有硬编码完全等价。

**理由**：brownfield 必须保证不修改 TimeConfig 时现有 notebook、CLI、API、模型行为完全不变。改默认值=隐式破坏现有行为。

**覆盖**：FR-007
