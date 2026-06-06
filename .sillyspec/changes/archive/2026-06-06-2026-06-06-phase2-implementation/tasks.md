---
author: lmr
created_at: 2026-06-06 19:00:00
---

# Tasks

## Wave 1: 数据接入 + LEAR 电价预测

| 序号 | 任务 | 文件 | 依赖 | 验收标准 |
|------|------|------|------|----------|
| 1.1 | 创建 `price_loader.py` — 加载 ZionLuo xlsx，标准化列名，返回标准 DataFrame | `ellectric/pipeline/price_loader.py` | — | `PriceDataLoader().load_data()` 返回 timestamp + price + load 的标准 DF |
| 1.2 | 实现 `price_loader` 的列映射和时区处理 | same as 1.1 | 1.1 | 列映射覆盖所有 7 个字段，时区标准化到 UTC |
| 1.3 | 创建 `price_forecaster.py` — LEARForecaster 类（特征 + 训练 + 可视化） | `ellectric/pipeline/price_forecaster.py` | — | 完整类：add_price_features + train_evaluate + plot_price_forecast |
| 1.4 | 实现 LEAR 特征工程（Tier 1-3，同 Phase 1 风格） | same as 1.3 | 1.3 | 日历特征 + 滞后特征 + 滚动统计 + 循环编码 |
| 1.5 | 实现 train_evaluate 方法（TimeSeriesSplit + Lasso + scaler 封装） | same as 1.3 | 1.4 | 内部 TimeSeriesSplit(n_splits=5, gap=24)，scaler fit-on-train-only |
| 1.6 | 实现 plot_price_forecast 可视化 | same as 1.3 | 1.5 | plotly overlay + 误差直方图，Phase 1 风格一致 |
| 1.7 | 更新 `pipeline/__init__.py` 导出新模块 | `ellectric/pipeline/__init__.py` | 1.1, 1.3 | 可 `from ellectric.pipeline import PriceDataLoader, LEARForecaster` |
| 1.8 | 创建 `06_price_forecasting.ipynb` — 完整预测 notebook | `ellectric/notebooks/06_price_forecasting.ipynb` | 1.2, 1.6 | 全部 cell 顺序执行无报错，输出 MAE + 图表 + 思考题 |

## Wave 2: epftoolbox 基准对比 + 仪表板

| 序号 | 任务 | 文件 | 依赖 | 验收标准 |
|------|------|------|------|----------|
| 2.1 | 创建独立 venv_epftoolbox 和安装脚本 | `ellectric/install_epftoolbox.sh` | — | `bash install_epftoolbox.sh` 创建 venv + pip install |
| 2.2 | 下载 5 个 epftoolbox 基准数据集，输出统计数据 | (notebook cell) | 2.1 | 各数据集的均值、中位数、标准差、缺失率 |
| 2.3 | 将中国 LEAR 预测结果与 epftoolbox 基准进行 DM/GW 检验 | (notebook cell) | 2.2, W1.done | DM 检验 p-value 输出 |
| 2.4 | 创建 `07_model_comparison_dashboard.ipynb` — 3 Tab 仪表板 | `ellectric/notebooks/07_model_comparison_dashboard.ipynb` | 2.3 | 3 个 Tab 完整渲染，hover 交互正常 |

## Wave 3: ASSUME 中国省间现货仿真

| 序号 | 任务 | 文件 | 依赖 | 验收标准 |
|------|------|------|------|----------|
| 3.1 | ASSUME 安装和验证 | (脚本) | — | `pip install assume-framework` 成功 |
| 3.2 | 创建 `assume_china_config.yaml` — 中国省间市场配置 | `ellectric/assume/configs/assume_china_config.yaml` | 3.1 | 报价上限/下限、偏差考核、新能源优先调度、5 种发电类型 |
| 3.3 | 创建 `assume_china_wind_high.yaml` — 高风电场景 | `ellectric/assume/configs/assume_china_wind_high.yaml` | 3.2 | 风电 30%、煤电减少 20% |
| 3.4 | 创建 `assume_china_summer_peak.yaml` — 夏季高峰场景 | `ellectric/assume/configs/assume_china_summer_peak.yaml` | 3.2 | 总需求 +20%、气电增加 |
| 3.5 | 运行 ASSUME 7 天仿真并输出结果 | (脚本/notebook) | 3.2 | 仿真完成，出清价格、调度、利润可查 |
| 3.6 | 配置 Grafana 显示仿真结果 | (docker-compose + grafana json) | 3.5 | 5 个面板渲染正常 |

## 依赖图

```
Wave 1:  1.1 → 1.2 → 1.7
         1.3 → 1.4 → 1.5 → 1.6 → 1.7
         1.2 + 1.6 → 1.8
         
Wave 2:  2.1 → 2.2 → 2.3 → 2.4
         2.4 依赖 W1.done (需要 LEAR 预测结果)

Wave 3:  3.1 → 3.2 → 3.3 + 3.4
         3.2 → 3.5 → 3.6
         预测和仿真无硬依赖，可独立推进
```
