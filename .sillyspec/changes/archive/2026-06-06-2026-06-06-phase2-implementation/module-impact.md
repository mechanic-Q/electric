---
author: lmr
created_at: 2026-06-06T21:36:10+08:00
---

# 模块影响分析

## 三重交叉验证

| 维度 | 范围 |
|------|------|
| 声明范围 (design.md) | price_loader.py, price_forecaster.py, __init__.py, 3 notebooks, ASSUME YAML, Grafana |
| 真实变更 (git diff + untracked) | 4 个管道模块 + 3 notebooks + 5 脚本 + 3 YAML + 4 Grafana + docker-compose + README |
| 一致性 | ✅ 一致 (task-07 新增 README 更新, task-10 新增 docker-compose 修改, 均符合设计) |

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| (新增) price-loader | 新增 | `pipeline/price_loader.py` | ZionLuo xlsx 加载, 列标准化, UTC 时区 | false |
| (新增) price-forecaster | 新增 | `pipeline/price_forecaster.py` | LEARForecaster: Lasso + Tier 1-3 特征 + train_evaluate | false |
| (新增) statistical-tests | 新增 | `pipeline/statistical_tests.py`, `data/dmgw_results.json` | DM/GW 统计检验封装, 含 epftoolbox 回退 | false |
| (新增) assume-simulation | 新增 | `assume/run_simulation.py`, `verify_simulation.py`, `configs/*.yaml` | 7天仿真 CLI, 中国省间规则, 结果验证 | false |
| (新增) assume-verify | 新增 | `scripts/verify_assume.py`, `requirements-assume.txt` | ASSUME 安装验证脚本 | false |
| (新增) grafana-dashboard | 新增 | `assume/grafana/**`, `docker-compose.yml` | 5 面板 Grafana, TimescaleDB 数据源 | false |
| (新增) epftoolbox-install | 新增 | `install_epftoolbox.sh` | 独立 venv 安装, 5 数据集下载 | false |
| (修改) notebooks | 新增 | `notebooks/06_price_forecasting.ipynb` | LEAR 电价预测教学 notebook | false |
| (修改) notebooks | 新增 | `notebooks/07_model_comparison_dashboard.ipynb` | 3 Tab 模型对比仪表板 | false |
| (修改) notebooks | 新增 | `notebooks/08_assume_results.ipynb` | ASSUME 仿真结果可视化 | false |
| (修改) pipeline | 接口变更 | `pipeline/__init__.py` | 新增 PriceDataLoader + LEARForecaster + run_statistical_tests 导出 | false |
| (修改) docker-compose | 配置变更 | `docker-compose.yml` | 启用 TimescaleDB + Grafana, 添加 provisioning 挂载 | false |
| (修改) README | 文档 | `README.md` | 追加 ASSUME 安装验证章节 | false |

## 未匹配文件

所有文件均已匹配到模块或归类为新增模块。

## 影响总结

- **新增模块**: 6 个 (price-loader, price-forecaster, statistical-tests, assume-simulation, assume-verify, grafana-dashboard, epftoolbox-install)
- **修改模块**: 3 个 (notebooks, pipeline, docker-compose)
- **Phase 1 模块未受影响**: data-loader, cleaner, feature-engineer, forecaster 未被修改
