# TESTING

> author: lmr | created_at: 2026-06-06T00:00:00+08:00

## 测试现状

**No automated tests found — project is in Phase 1 learning stage.**

### 搜索清单

| 模式 | 搜索范围 | 结果 |
|------|---------|------|
| `pytest` / `unittest` | 全项目 `*.py` | 0 个测试文件 |
| `test*.py` | 全项目 glob | 0 个测试文件 |
| `test_*.py` | 全项目 glob | 0 个测试文件 |
| `assert` / `describe` | 源码 `*.py` | 0 处（仅注释/文档中的说明） |
| `.github/` | 项目根目录 | 不存在（无 CI/CD） |
| `pyproject.toml` | 项目根目录 | 不存在（无 pytest 配置） |
| `Makefile` | 项目根目录 | 不存在（无测试目标） |
| `.gitlab-ci.yml` | 项目根目录 | 不存在 |

### 源码中的模型评估（非测试）

`ellectric/pipeline/forecaster.py` 的 `XGBoostForecaster.train_evaluate()` 方法在训练过程中计算了 MAE、RMSE、MAPE、R²，但这些是模型训练流程的一部分，不是结构化测试：

- `forecaster.py:378` — fold 内 MAE 日志输出
- `forecaster.py:386-397` — 聚合指标计算（mae / rmse / mape / r2）

### Jupyter Notebook 验证

5 个 Jupyter Notebook 提供交互式学习验证（非自动化测试）：

| Notebook | 文件路径 |
|----------|---------|
| 01_data_ingestion | `ellectric/notebooks/01_data_ingestion.ipynb` |
| 02_data_cleaning | `ellectric/notebooks/02_data_cleaning.ipynb` |
| 03_feature_engineering | `ellectric/notebooks/03_feature_engineering.ipynb` |
| 04_load_forecasting | `ellectric/notebooks/04_load_forecasting.ipynb` |
| 05_end_to_end_baseline | `ellectric/notebooks/05_end_to_end_baseline.ipynb` |

### 建议

Phase 2 或 Phase 3 应考虑添加：
- `pytest` + `pytest-cov` 的基础测试基础设施
- 对 `cleaner.py`、`features.py` 的数据合约单元测试（schema 验证）
- 对 `XGBoostForecaster.train_evaluate()` 的 smoke test（确保管道不崩溃）
- CI pipeline（GitHub Actions，lint + test）
