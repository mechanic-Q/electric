# Walking Skeleton — Ellectric (AI + 电力交易技术学习平台)

**阶段:** 1
**生成日期:** 2026-05-20

## 端到端能力验证

学习者运行 `setup.sh`，打开 `notebooks/05_end_to_end_baseline.ipynb`，执行所有 cell，看到：中国 OWID 能源数据从互联网加载、清洗（缺失值填充 + IQR 异常值检测）、persistence 预测（shift-24h），并通过 plotly 渲染累计 P&L 图——在引入任何复杂建模之前，证明完整的数据→预测→交易管道已连通。

## 架构决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 编程语言 | Python 3.11 | OpenSTEF 最低要求（阶段2）；NumPy 2.x + pandas 3.0.x Arrow 后端兼容性 |
| 开发环境 | Jupyter Notebook + 模块化 .py 管道模块 | Notebook 用于学习探索；.py 模块用于可复用的生产逻辑。薄的 notebook 包装层，厚的管道模块。 |
| 包管理 | pip + venv + requirements.txt（固定版本） | 一键安装: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`。目标 <30 分钟在干净机器上完成。不引入 Poetry/pipenv——对学习平台过度设计。 |
| 数据层 | pandas/pyarrow + Parquet 文件（无数据库服务器） | 便携、列式、pandas 原生、读写快速。阶段1 数据量 <100MB——SQLite/Postgres 多余。TimescaleDB 在阶段2 通过 Docker 为 ASSUME 仪表板添加。 |
| 数据源策略 | OWID 年度数据（自动拉取）+ 中国开放数据平台（手动下载） | 仅限中国数据。OWID 提供可靠的、可自动拉取的年度宏观数据。中国小时/日级数据需通过浏览器手动从和鲸/天池/地方平台下载（政府平台有 CAPTCHA/反爬屏障——见 RESEARCH.md §1）。统一 DataLoader 接口。不引入国际数据（无 PUDL、无 epftoolbox、无 PJM）。 |
| 数据格式 | 标准化列 schema: `timestamp` (datetime64[ns, UTC]), `load_mw` (float64), 附加元数据 (region, data_source) | 所有数据带时区。Parquet 为主要格式。 |
| 认证 | 无 | 本地 Jupyter 学习环境。无用户账号，无 API key。 |
| 部署目标 | 本地 Jupyter 服务器 (`setup.sh && jupyter notebook`) | 无需云端部署。学习者在自己的开发机上运行一切。 |
| 可视化 | plotly 6.7.0（交互式，Jupyter 原生） | 悬停查看数值、缩放、平移——对学习数据探索至关重要。 |
| 模型评估 | 仅 MAE（时间切分的测试集上的平均绝对误差） | 保持简单和可解释。阶段1 不使用 RMSE、MAPE、sMAPE——降低学习者的认知负荷。 |
| 目录布局 | `pipeline/`（模块），`notebooks/`（探索），`data/`（原始数据，gitignore） | 所有阶段的统一模式。pipeline/ 模块可导入；notebooks/ 为薄包装层。 |

## 阶段1涉及的技术栈

- [x] 项目脚手架 — `setup.sh`、`requirements.txt`、目录结构、`pipeline/__init__.py`
- [x] 数据加载 — 通过 `urllib` 自动拉取 OWID 中国数据，ChineseDataLoader 用于手动文件
- [x] 数据清洗 — 缺失值填充、IQR 异常值检测（仅报告）、UTC 时区标准化
- [x] 预测 — persistence 预测（shift-24h 基线）、最小化 P&L 计算
- [x] 可视化 — plotly 折线叠加图（实际 vs 预测）+ 累计 P&L 图
- [ ] 特征工程 — 推迟到计划 01-02（日历特征、滞后特征、滚动窗口）
- [ ] XGBoost 训练 — 推迟到计划 01-02（TimeSeriesSplit、模型持久化）
- [ ] Docker Compose — 推迟到计划 01-03（骨架 YAML，阶段2 取消注释）

## 不在范围内（推迟到后续切片）

- **XGBoost 负荷预测**（PRED-01 完整） — 计划 01-02 添加带 TimeSeriesSplit、渐进式特征、模型持久化和全部可视化的 XGBoost
- **Docker Compose**（ENV-02） — 计划 01-03 创建注释掉的骨架 YAML；实际服务在阶段2 为 ASSUME+TimescaleDB+Grafana 取消注释
- **OpenSTEF 自动预测**（PRED-02） — 阶段2
- **epftoolbox 电价预测**（PRED-03） — 阶段2
- **ASSUME 市场仿真**（SIM-01 至 SIM-04） — 阶段2
- **RL 交易智能体**（AGENT-01 至 AGENT-04） — 阶段3
- **SHAP 可解释性**（VIZ-02） — 阶段3
- **FastAPI + CLI + LangChain + Ollama** — 阶段4
- **中国电力小时/日级数据** — 手动下载流程已记录；数据文件本身被 gitignore（用户提供，不提交）
- **气象数据集成** — 阶段2（OpenSTEF 提供气象特征工程）
- **enda 能源库** — 推迟（H2O 依赖与项目约束冲突）
- **Grafana 仪表板** — 阶段2（通过 ASSUME+TimescaleDB Docker 服务）

## 后续切片计划

每个后续阶段在此骨架之上添加一个垂直切片，不改变其架构决策：

- **阶段2**: 深度预测（OpenSTEF vs XGBoost 对比）+ ASSUME 市场仿真，多种发电组合和 Grafana 仪表板
- **阶段3**: RL 交易智能体（PPO/TD3/SAC），自定义奖励函数，压力时段历史回测，SHAP 可解释性
- **阶段4**: FastAPI REST API、CLI 工具链、LangChain + Ollama 自然语言交易助手
