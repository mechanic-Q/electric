# TESTING

> author: lmr | created_at: 2026-06-06T00:00:00+08:00 | updated_at: 2026-06-10T00:00:00+08:00

## 测试现状

**No automated tests found — project remains in learning/demo stage after Phase 1-4.**

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

### 源码中的模型评估（Phase 1-3，非结构化测试）

各预测器和 RL 训练过程中计算的性能指标属于模型训练流程的一部分，不是结构化测试：

| 模块 | 评估指标/验证 | 方法 |
|------|-------------|------|
| `forecaster.py` | MAE, RMSE, MAPE, R² per fold | `XGBoostForecaster.train_evaluate()` |
| `price_forecaster.py` | MAE, RMSE, MAPE, R² per fold | `LEARForecaster.train_evaluate()` |
| `trading_env.py` | Reward per step/episode | 环境内置跟踪 (`_track_episode_info`) |
| `rl_trainer.py` | Episode reward, loss curves | Sb3 `learn()` callback 日志 |
| `backtester.py` | Cumulative P&L, Sharpe ratio | `BacktestRunner.compare()` |
| `shap_explainer.py` | Shapley value convergence | SHAP 内置 |

### Jupyter Notebook 验证

11 个 Jupyter Notebook 提供交互式学习验证（非自动化测试）：

| Notebook | 阶段 | 文件路径 |
|----------|------|---------|
| 01_data_ingestion | Phase 1 | `ellectric/notebooks/01_data_ingestion.ipynb` |
| 02_data_cleaning | Phase 1 | `ellectric/notebooks/02_data_cleaning.ipynb` |
| 03_feature_engineering | Phase 1 | `ellectric/notebooks/03_feature_engineering.ipynb` |
| 04_load_forecasting | Phase 1 | `ellectric/notebooks/04_load_forecasting.ipynb` |
| 05_end_to_end_baseline | Phase 1 | `ellectric/notebooks/05_end_to_end_baseline.ipynb` |
| 06_price_forecasting | Phase 2 | `ellectric/notebooks/06_price_forecasting.ipynb` |
| 07_model_comparison_dashboard | Phase 2 | `ellectric/notebooks/07_model_comparison_dashboard.ipynb` |
| 08_assume_results | Phase 2 | `ellectric/notebooks/08_assume_results.ipynb` |
| 09_rl_trading_agent | Phase 3 | `ellectric/notebooks/09_rl_trading_agent.ipynb` |
| 10_multi_agent_backtest | Phase 3 | `ellectric/notebooks/10_multi_agent_backtest.ipynb` |
| 11_model_explainability | Phase 3 | `ellectric/notebooks/11_model_explainability.ipynb` |

### 验证脚本（非结构化测试）

| 脚本 | 用途 | 阶段 |
|------|------|------|
| `scripts/verify_assume.py` | 验证 ASSUME 环境安装 | Phase 2 |
| `scripts/verify_phase3.sh` | 验证 RL/backtest/SHAP 管道 | Phase 3 |
| `scripts/run_demo.py` | 端到端演示（覆盖所有模型） | Phase 4 |

### Schema 校验（Pydantic 自动验证）

Phase 4 的 `service/schemas.py` 通过 Pydantic v2 提供了运行时数据校验：

- `ForecastRequest`: `model_type` Literal 校验, `horizon` range (1-168)
- `SimulateRequest`: `config` Literal 校验, `days` range (1-30)
- `BacktestRequest`: `model_validator(mode="after")` 跨字段校验（start<end, RL strategy needs model_path）
- `ExplainRequest`: `sample_index >= 0`, `max_display` (1-50)

但这些是 API 参数校验，不是功能测试。

### 建议（与 Phase 1 一致，仍未实施）

- `pytest` + `pytest-cov` 的基础测试基础设施
- 对 `cleaner.py`、`features.py` 的数据合约单元测试（schema 验证）
- 对 `XGBoostForecaster.train_evaluate()` 和 `LEARForecaster.train_evaluate()` 的 smoke test
- `trading_env.py` 的 Gymnasium environment check (step/reset/seed)
- `backtester.py` 的基线策略一致性测试
- `shap_explainer.py` 的输出格式验证
- `handlers.py` 的输入/输出边界测试
- FastAPI endpoint integration test (httpx TestClient)
- CI pipeline（GitHub Actions，lint + test）
