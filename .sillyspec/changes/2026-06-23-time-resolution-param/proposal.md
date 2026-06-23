---
author: lmr
created_at: 2026-06-23T19:10:00+08:00
---

# Proposal — 时间分辨率参数化

## 动机

Electric 项目代码当前完全是**小时级硬编码系统**：
- `trading_env.py`: `action_space = Box(shape=(24,))`、`price_history_168h`
- `features.py`: `shift(24)`、`shift(168)`、`rolling(24)`、`rolling(168)`
- `forecaster.py`/`price_forecaster.py`: 全部 `shift(24)` 和 `shift(168)`
- `cleaner.py`: `freq != "h"` 强制重采样为小时级

上一变更（shanxi-spot-data-access）已经把 15 分钟级现货数据接进 `ShanxiSpotDaLoader`、`ShanxiSpotRtLoader`、`ShanxiMonthSettleLoader`。但 pipeline 仍然吃不下 96 点/天，数据有了但下游用不上。

## 关键问题

为什么现在的方案不行？

1. **数据/系统不匹配**：山西 spot_da/spot_rt 是 96 点/天的 15min 曲线，但 `trading_env.py` 的 action_space 是 `(24,)`，特征工程 shift(24) 假设一天 24 点
2. **无法对标图迹**：GeekBidder OS 是 15min 现货决策系统，Electric 维持 24 点架构无法做相同维度的 demo
3. **无统一切换开关**：5 个 pipeline 文件互相独立硬编码，靠人工 grep-and-replace 风险高

## 变更范围

- 新建 `ellectric/config.py`：定义 `TimeConfig` 全局配置类（`points_per_day` / `points_per_week` / `freq`）
- 修改 5 个 pipeline 文件，把硬编码 24/168/`"h"` 替换为 `TimeConfig` 引用
- 默认值保持 24/168/`"h"`，与现有行为完全兼容
- 通过修改 `TimeConfig` 三个属性一行切换到 15min 模式

## 不在范围内

- ❌ 不做环境变量自动检测（`ELLECTRIC_TIME_RESOLUTION`）
- ❌ 不做运行时动态切换（不需要一个进程同时支持两种粒度）
- ❌ 不做特征自适应（Tier 特征的语义窗口不自动调整）
- ❌ 不做 TradingEnv 内 hour/bid 等概念的语义重命名
- ❌ 不做配置持久化（不写配置文件、不做 CLI/API 暴露）
- ❌ 不做 LEAR/PPO 模型在 15min 下的精度回归测试
- ❌ 不引入新依赖（不引入 pydantic-settings 等）

## 成功标准（可验证）

1. 默认 `TimeConfig.points_per_day=24` 下，运行 `04_load_forecasting.ipynb` 输出与变更前一致
2. 改 `TimeConfig.points_per_day=96` 后：
   - `trading_env.py` 的 `action_space.shape == (96,)`
   - `features.py` 的 `shift(...)` 接收 96
   - `pd.date_range(..., periods=..., freq="15min")` 生效
3. `cleaner.py` 不再硬编码判断 `freq == "h"`
4. `ellectric/pipeline/data_loader.py`、`ellectric/pipeline/shanxi_loader.py` 零修改
5. `requirements.txt` 不引入新依赖
6. `python ellectric/scripts/verify_shanxi_loader.py` 24/24 仍通过
