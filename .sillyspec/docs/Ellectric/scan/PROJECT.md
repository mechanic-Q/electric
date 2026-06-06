# PROJECT

> author: lmr | created_at: 2026-06-06T00:00:00+08:00

## 项目简介

**Ellectric** — AI + 电力交易技术学习平台。一个动手实践性质的 AI + 电力交易技术学习项目。

### 核心理念

基于北京图迹科技（GeekBidder）的技术画像——大数据平台 + AI 时序预测模型 + 电力市场仿真 + 自动交易智能体——使用开源替代方案搭建可运行的端到端技术原型。

**核心价值**: 跑通"公开电力数据接入 → 负荷/电价预测 → 电力市场仿真 → 自动交易策略"的完整技术闭环。

### 关键约束

- 仅使用公开可获取数据集（OWID、PUDL 等），不涉及商业数据
- 全部使用开源工具和框架
- 轻量级模型为主（XGBoost、LSTM、小型 RL），不训练大模型
- 单台开发机可运行（不需要 GPU 集群）
- Python 3.11+

### 开发阶段

| 阶段 | 名称 | 状态 | 内容 |
|------|------|------|------|
| Phase 1 | Data Foundation + Basic Prediction | **已完成** | OWID 数据接入、数据清洗、特征工程、XGBoost 负荷预测、端到端基线 |
| Phase 2 | Deep Prediction + Market Simulation | 计划中 | OpenSTEF、epftoolbox 电价预测、ASSUME 市场仿真、Grafana 仪表板 |
| Phase 3 | Trading Agents + Backtesting | 计划中 | RL 智能体（PPO/TD3/SAC）、历史回测、SHAP 可解释性 |
| Phase 4 | Integration + LLM Interface | 计划中 | FastAPI、CLI、LangChain + Ollama 自然语言交易助手 |

### 开发模式

本项目使用 **SillySpec** + **Karpathy Guidelines** 组合驱动开发。`.planning/` 目录保留 GSD 历史资产。

---

## 目录结构

```
/mnt/e/Ellectric/
├── AGENTS.md              # 开发指令 + 技术栈 + 架构约定
├── INSTRUCTIONS.md         # 项目入口说明
├── .gitignore
├── .planning/              # GSD 规划资产（ROADMAP.md、REQUIREMENTS.md）
├── docs/                   # 用户文档（chinese-electricity-data-guide.md）
├── .opencode/              # OpenCode CLI 配置
├── .claude/                # Claude CLI 配置
├── .sillyspec/             # SillySpec 规范和扫描输出
└── ellectric/
    ├── setup.sh            # 一键环境安装脚本
    ├── requirements.txt    # Python 依赖（5 个核心包）
    ├── docker-compose.yml  # Docker Compose（全部注释，Phase 2 启用）
    ├── README.md           # 项目使用说明
    ├── data/               # 本地数据存放
    ├── notebooks/          # 5 个 Jupyter 教学 Notebook
    │   ├── 01_data_ingestion.ipynb
    │   ├── 02_data_cleaning.ipynb
    │   ├── 03_feature_engineering.ipynb
    │   ├── 04_load_forecasting.ipynb
    │   └── 05_end_to_end_baseline.ipynb
    └── pipeline/           # Python 管道模块（~1,300 行）
        ├── __init__.py
        ├── data_loader.py  # DataLoader 抽象基类 + OWIDChinaLoader + ChineseDataLoader
        ├── cleaner.py      # 数据清洗（缺失填充、IQR 检测报告、时区标准化）
        ├── features.py     # 特征工程（Tier 1/2/3 渐进式特征）
        └── forecaster.py   # 预测引擎（持续法基线 + XGBoost + P&L 计算）
```

---

## 技术栈

### Phase 1 — 当前已安装

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 数据处理 | pandas + numpy + pyarrow | 3.0.3 / 2.0+ / 22.0.0 | 时序数据加载、清洗、特征工程 |
| 机器学习 | scikit-learn | 1.8.0 | TimeSeriesSplit、StandardScaler、评估指标 |
| 机器学习 | xgboost | 3.2.0 | 梯度提升树负荷预测（核心模型） |
| 可视化 | plotly | 6.7.0 | 交互式时序图表 |
| 开发环境 | jupyter | 1.1.1 | Notebook 交互式学习界面 |
| 数据源 | OWID (Our World in Data) | GitHub raw CSV | 中国年度发电/用电数据（自动拉取） |

### Phase 2-4 — 计划引入

| 阶段 | 技术 | 用途 |
|------|------|------|
| Phase 2 | OpenSTEF 3.4.93 | 自动化短期电力预测管道 |
| Phase 2 | epftoolbox | 日前电价预测（LEAR/DNN 模型） |
| Phase 2 | ASSUME 0.6.0 | 电力市场仿真（强化学习智能体） |
| Phase 2 | PyPSA + TimescaleDB + Grafana | 电网分析 + 仿真数据存储 + 仪表板 |
| Phase 3 | stable-baselines3 + gymnasium | RL 智能体训练（PPO/SAC/TD3） |
| Phase 3 | optuna | 超参数优化 |
| Phase 3 | SHAP | 模型可解释性 |
| Phase 4 | FastAPI + uvicorn | REST API 服务 |
| Phase 4 | LangChain + Ollama | 自然语言交易助手 |
| Phase 4 | MLflow | 实验跟踪和模型注册 |

### 数据架构

```
OWID GitHub (公开能源CSV)
     │
     ▼
DataLoader (抽象基类)
     │
     ├── OWIDChinaLoader  (自动拉取中国年数据，流式解析 ~25MB CSV)
     └── ChineseDataLoader (手动日/小时级本地 CSV/Excel/Parquet)
     │
     ▼
clean_data()  → 缺失填充 (ffill/bfill) + IQR 检测 (不删除) + 时区标准化 (UTC)
     │
     ▼
FeatureEngineer  → Tier 1 (hour/dow/month/weekend/lag24h)
                 → Tier 2 (is_holiday/lag168h)
                 → Tier 3 (rolling stats/sin-cos cyclic)
     │
     ▼
XGBoostForecaster  → TimeSeriesSplit (gap=24, scaler fit on train only)
     │
     ▼
persistence_forecast()  → 持续法基线 (t-24h)
calculate_pnl()         → 模拟交易盈亏
plot_pnl()              → Plotly 交互式可视化
```

### 代码量统计（Phase 1）

| 模块 | 行数 | 职责 |
|------|------|------|
| `data_loader.py` | 390 | 抽象基类 + OWID/本地数据加载 + 工厂函数 |
| `cleaner.py` | 178 | 缺失填充 + IQR 报告 + 时区标准化 + schema 验证 |
| `features.py` | 224 | 渐进式特征工程（3 Tiers）+ 便捷函数 |
| `forecaster.py` | 431 | 持续法基线 + XGBoost 训练评估 + P&L 计算 + 绘图 |
| 合计 | ~1,300 | 5 个模块，无外部业务逻辑依赖 |
