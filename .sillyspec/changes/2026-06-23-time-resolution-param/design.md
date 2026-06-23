---
author: lmr
created_at: 2026-06-23T18:50:00+08:00
---

# 时间分辨率参数化 — 设计文档

## 背景

Electric 项目当前是**小时级系统**，所有时间维度硬编码：
- `trading_env.py`: `action_space = Box(shape=(24,))`, `price_history_168h`
- `features.py`: `shift(24)`, `shift(168)`, `rolling(24)`, `rolling(168)`
- `forecaster.py`: `persistence_forecast()` 用 `shift(24)`
- `price_forecaster.py`: `shift(24)`, `shift(168)` × 价格/负荷/风电/光伏
- `cleaner.py`: `freq != "h"` → 强制重采样为小时级

上一变更（shanxi-spot-data-access）已接入 15min 现货数据，但 pipeline 仍只能处理小时级——数据有了但系统吃不下。

## 设计目标

1. 新建 `ellectric/config.py`，定义 `TimeConfig` 全局配置类
2. 将所有硬编码时间点替换为 `TimeConfig.points_per_day` / `TimeConfig.points_per_week` / `TimeConfig.freq`
3. 默认值保持小时级（24/168/"h"），改置一处即可切换 15 分钟（96/672/"15min"）
4. **不修改** 现有 DataFrame 合约（`timestamp`/`load_mw` 不）

## 非目标

- ❌ 不做环境变量自动检测（`ELLECTRIC_TIME_RESOLUTION`）
- ❌ 不做运行时动态切换（不需要一个进程同时支持两种粒度）
- ❌ 不做特征自适应（Tier 特征的 shift 语义窗口不自动调整）
- ❌ 不做 TradingEnv 中的 hour/bid 语义重命名
- ❌ 不做配置持久化（不写配置文件、不做 CLI 参数、不做 API endpoint）
- ❌ 不引入新依赖

## 拆分判断

本变更单一变更，不拆分为多个子变更。涉及 6 个文件，其中 1 个新增（config.py），5 个修改（逐个替换硬编码）。任务之间无分支依赖，适合在一个 change 中完成。

## 总体方案

### I. 全局配置：TimeConfig

新增 `ellectric/config.py`：

```python
class TimeConfig:
    """电力时间分辨率全局配置。"""
    points_per_day = 24        # 每天点数：24 (hourly) / 96 (15min)
    points_per_week = 168      # 每周点数：168 (hourly) / 672 (15min)
    freq = "h"                 # pandas 频率别名：'h' (hourly) / '15min'
```

所有 pipeline 模块 `from ellectric.config import TimeConfig` 后引用。

### II. 逐文件替换清单

| 文件 | 涉及行 | 替换 |
|---|---|---|
| `ellectric/config.py` | 新增 | TimeConfig 类 |
| `ellectric/pipeline/trading_env.py` | ~30 处（共 91 处提及 24/168，含 docstring/注释不需替换） | `(24,)` → `(TimeConfig.points_per_day,)`; `168h` → `TimeConfig.points_per_week`; `freq="h"` → `freq=TimeConfig.freq`; `pd.date_range(..., periods=24, freq="h")` → 用 TimeConfig |
| `ellectric/pipeline/features.py` | 2 处 | `shift(24)` → `shift(TimeConfig.points_per_day)`; `shift(168)` → `shift(TimeConfig.points_per_week)` |
| `ellectric/pipeline/forecaster.py` | 1 处 | `shift(24)` → `shift(TimeConfig.points_per_day)` |
| `ellectric/pipeline/price_forecaster.py` | 5 处 | `shift(24)`/`shift(168)` → TimeConfig 引用 |
| `ellectric/pipeline/cleaner.py` | 2 处 | `freq != "h"` → 与 TimeConfig.freq 比较；重采样目标用 TimeConfig.freq |

### III. 兼容策略（brownfield）

- **默认值保持 24/168/"h"**：不改一行，现有网络行为完全不变
- 改 `TimeConfig.points_per_day = 96` → 整个系统切换到 15 分钟
- 现有 API/CLI/DataFrame 合约不受影响
- 现有 validate_schema / clean_data / FeatureEngineer / forecaster 只读 `TimeConfig` 值，不修改

### IV. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | `trading_env.py` 44 处引用可能漏改 1-2 处 | P0 | 逐个 grep 确认 + 验证脚本：改 TimeConfig.points_per_day=96 后运行 verify_shanxi_loader |
| R-02 | LEAR price_forecaster 的 shift 语义窗口变化可能影响模型精度 | P1 | 默认 24 不变，15min 切换后由用户自行重新训练 |
| R-03 | `cleaner.py` 的 `freq != "h"` 比较逻辑可能和 TimeConfig.freq 类型冲突 | P1 | 统一用 pandas freq 字符串 |
| R-04 | Hour/bid 等语义在 96 点场景下不再准确 | P2 | 不在本变更处理，留给后续语义清理 |

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | ellectric/config.py | TimeConfig 全局配置 |
| 修改 | ellectric/pipeline/trading_env.py | 44 处 24/168/freq 替换 |
| 修改 | ellectric/pipeline/features.py | 2 处 shift 替换 |
| 修改 | ellectric/pipeline/forecaster.py | 1 处 shift 替换 |
| 修改 | ellectric/pipeline/price_forecaster.py | 5 处 shift 替换 |
| 修改 | ellectric/pipeline/cleaner.py | 2 处 freq 替换 |

## 接口定义

### TimeConfig

```python
class TimeConfig:
    points_per_day: int = 24
    points_per_week: int = 168
    freq: str = "h"
```

### 使用示例

```python
from ellectric.config import TimeConfig

# 小时级（默认）
env = ElectricityMarketEnv()  # Box(shape=(TimeConfig.points_per_day,)) = (24,)

# 切到 15min
TimeConfig.points_per_day = 96
TimeConfig.points_per_week = 672
TimeConfig.freq = "15min"
env = ElectricityMarketEnv()  # Box(shape=(96,))
```

### 无生命周期契约

不涉及 session/lease/agent_run/daemon 等运行时生命周期管理 — 本变更纯参数化重构，不引入任何状态机或长生命周期对象。

## 验收标准

1. ✅ 默认 24/168/"h" 下，现有 notebook (`04_load_forecasting.ipynb`) 运行结果不变
2. ✅ 改 `TimeConfig.points_per_day=96` 后，`trading_env` 的 action_space 变成 `(96,)`
3. ✅ `features.py` 的 `shift()` 参数跟随 `TimeConfig.points_per_day`
4. ✅ `cleaner.py` 不再判断 `freq != "h"` 而是 `freq != TimeConfig.freq`
5. ✅ 不引入新依赖
6. ✅ `verify_shanxi_loader.py` 仍 24/24 通过

## 决策追踪

| ID | 决策 | 覆盖章节 |
|---|---|---|
| D-001@v1 | 全局配置单例 (TimeConfig) | §I |
| D-002@v1 | 逐个文件精确替换 (方案1) | §II |
| D-003@v1 | 默认小时级保持兼容 | §III |

## 自审

- 矛盾 1（已确认）：`trading_env.py` 44 处引用量多 → R-01 记录并用验证脚本兜底
- 矛盾 2（已确认）：LEAR 模型敏感 → 默认 24 不变
- 一致性 1：文件变更清单与代码扫描一致（5 文件 + 1 新增）
- 一致性 2：验收标准可量化（notebook 输出不变、shape 变化、验证脚本仍通过）
- 无 lifecycle 关键词
