# CONCERNS

> author: lmr | created_at: 2026-06-06T00:00:00+08:00

扫描发现的工程质量关注点和依赖风险，按严重程度排序。

---

## 代码质量

### 🔴 无自动化测试覆盖

0 个测试文件，0 个 CI/CD pipeline。`forecaster.py` 中有内联模型评估指标（MAE/RMSE/MAPE），但缺乏独立的单元测试或集成测试。5 个 Jupyter Notebook 提供交互式验证，但不可自动化运行。

**影响**: 重构或升级依赖时有回归风险。

### 🔴 无 CI/CD 配置

项目缺少 `.github/workflows/`、`.gitlab-ci.yml`，无止单检查、无自动测试、无自动构建。

**影响**: 所有质量保证依赖开发者手动执行。

### 🟡 无 pyproject.toml / linter 配置

仅有 `requirements.txt`（19 行，5 个直接依赖），无 `pyproject.toml`、无 `ruff`/`mypy`/`pylint` 配置。代码风格规范未自动化。

**影响**: 多人协作时风格漂移风险。

### 🟡 Docker Compose 全部注释掉

`ellectric/docker-compose.yml` 中 TimescaleDB + Grafana 配置全部注释（`#` 前缀），标注"Phase 2 使用"。当前不可用。

**影响**: Phase 2 启动前需取消注释并验证。

### 🟢 Phase 1 完成度与代码量

Phase 1（数据基础 + 预测）**已完成**。源码仅 5 个 Python 模块（`pipeline/`） + 5 个 Jupyter Notebook，共 ~1,300 行 Python 代码。结构简洁，注释教学性强（中文教学注释占比 >60%）。

**影响**: 低。Phase 1 作为 MVP 的代码量符合预期。

### 🟢 TODO / FIXME 零存量

全项目 `TODO` / `FIXME` / `HACK` / `XXX` 搜索返回空。代码中无未完成标记。

**影响**: 低。说明代码中无已知技术债务标记。

---

## 依赖风险

### 🔴 epftoolbox — TensorFlow 依赖冲突（Phase 2 前置风险）

STACK.md 明确记录：epftoolbox 依赖旧版 TensorFlow，而 ASSUME 依赖 PyTorch。两者共存可能产生依赖冲突，需独立 venv 或隔离安装。

**影响**: Phase 2 若同时使用 epftoolbox 和 ASSUME，可能造成环境问题。

### 🟡 pandas 3.0.3 Arrow 后端兼容性

`requirements.txt` 固定 pandas 3.0.3 + pyarrow 22.0.0。Arrow 后端可能破坏依赖旧 pandas API 的库（enda、OpenSTEF 等 Phase 2 依赖）。

**影响**: Phase 2 引入新依赖时需验证兼容性。

### 🟡 ASSUME + PyTorch 未安装

Phase 2 核心依赖 ASSUME（AGPL-3.0）及其 PyTorch 传递依赖均未安装。当前 `requirements.txt` 仅 Phase 1 依赖。

**影响**: Phase 2 环境搭建是第一个门槛。

### 🟡 holidays 包为可选依赖

`features.py:121-128` 中的 `is_holiday` 特性对 `holidays` 包做了 `try/except ImportError` 容错降级（缺失时填 0）。降级行为正确但 lose 了实际功能。

**影响**: 分级很低——`holidays` 主要用于日/小时级数据的节假日标记，年级数据中无意义。

### 🟢 项目约束与 Python 版本

`requirements.txt` 未声明 `python_requires`，但 STACK.md 明确要求 Python 3.11+（OpenSTEF 要求 ≥3.11，ASSUME 兼容 3.10-3.14）。

**影响**: 低。`setup.sh` 可检测 Python 版本。

### 🟢 依赖数量极低

Phase 1 仅 5 个直接运行时依赖（pandas、numpy、pyarrow、scikit-learn、xgboost）+ 2 个开发/可选依赖（plotly、jupyter）。依赖树浅，安全审计面小。

**影响**: 低。反而是优点。
