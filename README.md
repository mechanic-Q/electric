# ⚡ Ellectric — AI + 电力交易技术学习平台

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Phase-4%20Complete-brightgreen.svg)]()

**Ellectric** 是一个动手实践性质的 AI + 电力交易技术学习项目。跑通"公开电力数据接入 → 负荷/电价预测 → 电力市场仿真 → 自动交易策略"的端到端技术闭环。

> 🔬 教育/学习用途，非生产系统。基于北京图迹科技技术画像，使用纯开源替代方案搭建可运行技术原型。

---

## 🎯 做了什么

从零构建了一个可完整运行的电力交易 AI 技术栈：

| 功能 | 技术实现 | 说明 |
|------|----------|------|
| **数据接入** | OWID 三级回退链路 + Ember + UCI | 自动获取中国电力公开数据，从年级 TWh 换算为逐时 MW |
| **数据清洗** | IQR 异常值检测 + 缺失填充 + UTC 标准化 | 异常值仅报告不删除 — 电力尖峰是有效信号 |
| **特征工程** | 三层渐进式特征 (Tier 1→2→3) | 从简单时间特征到循环编码+滚动统计，逐层递进 |
| **负荷预测** | XGBoost + TimeSeriesSplit CV | 5 折时序交叉验证，防未来信息泄露 (gap=24h) |
| **电价预测** | LEAR (Lasso L1 正则化) | Lasso 系数天然可解释，精度常超越复杂深度模型 |
| **市场仿真** | ASSUME 0.6.0 多智能体框架 | 日前市场/实时市场/平衡市场三层仿真 |
| **RL 交易智能体** | PPO / SAC / TD3 三种算法 | Gymnasium 环境，3 种奖励函数，Box 连续动作空间 |
| **历史回测** | BacktestRunner + 3 种基线策略 | persistence/mean/oracle 基线对比，夏普比率评估 |
| **模型可解释性** | SHAP TreeExplainer + LinearExplainer | waterfall 图 + 特征重要性排名 |
| **统计检验** | Diebold-Mariano + Giacomini-White | 预测模型精度显著性检验 |
| **REST API** | FastAPI + Pydantic v2 | 5 个端点: /predict, /simulate, /backtest, /explain, /chat/stream |
| **CLI 工具** | Typer + Rich 表格 | 5 个子命令: forecast, simulate, backtest, explain, ask |
| **LLM 对话助手** | LangChain + DeepSeek API + SSE 流式 | 自然语言查询电力数据，工具调用本地 API |
| **Web Chat UI** | 纯 HTML/CSS/JS 静态界面 | SSE 流式对话，Markdown 渲染，会话管理 |
| **学习 Notebooks** | 11 个渐进式 Jupyter notebooks | 从数据获取到模型可解释性，逐步动手 |

---

## 📊 项目历程

### 时间线

```
2026-05-20  ████████████████████████████  Phase 1: 数据基础 + XGBoost 负荷预测
            ├── 项目初始化、领域调研、路线图
            ├── OWID 数据自动拉取、清洗、特征工程
            ├── XGBoost 预测 + 持续法基线
            └── 5 个 Jupyter notebooks

2026-06-06  ████████████████████████████  Phase 2: 电价预测 + 市场仿真
            ├── LEAR (Lasso) 日前电价预测
            ├── ASSUME 多智能体电力市场仿真
            ├── Diebold-Mariano/Giacomini-White 统计检验
            └── 3 个 notebooks + Grafana 仪表板

2026-06-07  ████████████████████████████  Phase 3: RL 交易智能体 + 回测
            ├── ElectricityMarketEnv (Gymnasium)
            ├── PPO/SAC/TD3 三种 RL 智能体
            ├── BacktestRunner + 3 基线策略
            ├── SHAP 模型可解释性
            └── 3 个 notebooks + 多轮 bug 修复

2026-06-08  ████████████████████████████  Phase 4: 集成 + LLM 接口
            ├── FastAPI REST API (5 端点)
            ├── Typer CLI (5 子命令)
            ├── LangChain + DeepSeek LLM 对话
            └── Service 层统一 API/CLI/LLM 三通道

2026-06-10  ████████████████████████████  数据更新 + Web Chat UI
            ├── OWID 数据更新至 2025 年
            ├── Ember 碳排放数据探索
            ├── SSE 流式 Web Chat UI
            └── OWID 三级回退链路 (GitHub → GCS → 缓存)
```

### 迭代统计

- **40 次提交**，涵盖 5 个开发阶段
- **约 2,400 行** Pipeline 核心代码（12 个模块）
- **约 1,200 行** 接口层代码（API + CLI + Service + LLM）
- **11 个** Jupyter Notebooks，从零基础到 RL 智能体
- **3 种** RL 算法 + **3 种** 基线策略 + **3 层** 市场仿真
- **多轮密集 Bug 修复**：Phase 3 经历 7 轮修复（P&L 公式、SHAP 惰性导入、MultiInputPolicy、scaler 转换等）

---

## 🏗️ 架构

```
                        Interface Layer (三通道并行)
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│   FastAPI REST   │  │    Typer CLI     │  │  LangChain LLM       │
│  /predict        │  │  forecast        │  │  ask_agent(query)     │
│  /simulate       │  │  simulate        │  │   → DeepSeek API     │
│  /backtest       │  │  backtest        │  │   → 自然语言回答      │
│  /explain        │  │  explain         │  │                      │
│  /chat/stream    │  │  ask             │  │                      │
└────────┬─────────┘  └────────┬─────────┘  └───────────┬──────────┘
         └─────────────────────┼────────────────────────┘
                               │
                       Service Layer
              run_forecast() / run_simulate() /
              run_backtest() / run_explain()
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Pipeline Layer                              │
│                                                                    │
│  data_loader ──► cleaner ──► features ──► forecaster (XGBoost)   │
│       │                                        │                  │
│  price_loader ──► price_forecaster (LEAR)      │                  │
│       │                                        │                  │
│       └──────► backtester ◄── trading_env ◄────┘                  │
│                    │            │                                  │
│                    ▼            ▼                                  │
│              rl_trainer   shap_explainer                          │
│              (PPO/SAC/TD3) (Tree+Linear)                          │
└──────────────────────────────────────────────────────────────────┘
```

**关键设计原则**：
- **三明治架构**：API / CLI / LLM 三层并行，共享同一 Service 层，零重复逻辑
- **数据合约**：所有模块依赖统一的 `{timestamp, load_mw}` schema
- **延迟导入**：Service 层所有 pipeline 导入在函数内执行，避免循环依赖
- **可选依赖防护**：SHAP、epftoolbox、holidays 均 try/except 包裹，缺失时降级

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Git

### 一键安装

```bash
# 在 ellectric 子目录下创建虚拟环境 .venv（不在仓库根目录混入）
(cd ellectric && chmod +x setup.sh && ./setup.sh)
```

脚本自动：检查 Python 版本 → 创建虚拟环境 → 安装所有依赖（国内网络自动使用清华镜像）

### 激活环境

```bash
source ellectric/.venv/bin/activate
```

> ⚠️ 必须从**仓库根目录**（`Electric/`）激活环境，之后所有命令也在根目录执行。
> 勿 `cd ellectric` 后再激活——Python 包导入会失败。

### 启动服务

```bash
# 启动 FastAPI 服务
uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000 打开 Web Chat UI
# 访问 http://localhost:8000/docs 查看 API 文档

# CLI 命令
python -m ellectric.cli.main forecast load 24          # 负荷预测
python -m ellectric.cli.main simulate summer_peak --days 7  # 市场仿真
python -m ellectric.cli.main backtest 2022-08-01 2022-08-31 ppo  # 回测
python -m ellectric.cli.main explain xgboost 0           # SHAP 解释

# LLM 对话（需设置 DEEPSEEK_API_KEY）
python -m ellectric.cli.main ask "中国电力负荷有什么季节性特征？"

# 启动 Jupyter Notebooks
jupyter notebook ellectric/notebooks/
```

### Notebooks 学习顺序

| # | Notebook | 阶段 | 内容 |
|---|----------|------|------|
| 01 | `data_ingestion.ipynb` | Phase 1 | 从 OWID 自动获取中国电力数据 |
| 02 | `data_cleaning.ipynb` | Phase 1 | 缺失填充、异常值检测、时区标准化 |
| 03 | `feature_engineering.ipynb` | Phase 1 | 三层渐进式特征构建 |
| 04 | `load_forecasting.ipynb` | Phase 1 | XGBoost 训练评估 + 持续法基线 |
| 05 | `end_to_end_baseline.ipynb` | Phase 1 | 端到端管道 + P&L 模拟 |
| 06 | `price_forecasting.ipynb` | Phase 2 | LEAR Lasso 电价预测 |
| 07 | `model_comparison_dashboard.ipynb` | Phase 2 | 模型对比 + 统计检验 |
| 08 | `assume_results.ipynb` | Phase 2 | ASSUME 市场仿真结果分析 |
| 09 | `rl_trading_agent.ipynb` | Phase 3 | RL 智能体训练 (PPO/SAC/TD3) |
| 10 | `multi_agent_backtest.ipynb` | Phase 3 | 多策略回测对比 |
| 11 | `model_explainability.ipynb` | Phase 3 | SHAP 特征重要性 + waterfall |

---

## 📁 项目结构

```
ellectric/
├── pipeline/              # 核心 ML 管道 (12 模块, ~2,400 行)
│   ├── data_loader.py     #   DataLoader ABC + OWID/Chinese/Ember loaders
│   ├── cleaner.py         #   数据清洗 + schema 验证
│   ├── features.py        #   FeatureEngineer (Tier 1→2→3)
│   ├── forecaster.py      #   XGBoost 负荷预测 + P&L 计算
│   ├── price_loader.py    #   电价数据加载 (ZionLuo dataset)
│   ├── price_forecaster.py #  LEAR Lasso 电价预测
│   ├── trading_env.py     #   Gymnasium 电力市场交易环境
│   ├── rl_trainer.py      #   BaseRLAgent ABC + PPO/SAC/TD3
│   ├── backtester.py      #   回测引擎 + 基线策略
│   ├── shap_explainer.py  #   SHAP TreeExplainer + LinearExplainer
│   ├── statistical_tests.py # Diebold-Mariano + Giacomini-White 检验
│   └── ember_loader.py    #   Ember 碳排放数据加载
├── api/
│   ├── server.py          #   FastAPI app (5 路由 + SSE streaming)
│   └── static/            #   Web Chat UI 静态文件
├── service/
│   ├── schemas.py         #   Pydantic v2 请求/响应模型
│   └── handlers.py        #   4 个业务 handler (API/CLI/LLM 共用)
├── cli/
│   └── main.py            #   Typer CLI (5 子命令)
├── llm/
│   ├── agent.py           #   LangChain + DeepSeek agent
│   ├── tools.py           #   @tool 函数 (httpx → FastAPI)
│   └── chat.py            #   终端对话入口
├── chat/
│   └── streaming.py       #   SSE 流式 agent 封装
├── assume/                #   ASSUME 仿真配置 + 脚本
├── notebooks/             #   11 个渐进式 Jupyter notebooks
├── data/                  #   数据文件 (.parquet, .xlsx, .joblib)
├── models/                #   训练好的模型文件
├── scripts/               #   验证/演示脚本
├── setup.sh               #   一键环境安装
├── requirements.txt       #   Python 依赖
└── docker-compose.yml     #   Grafana 仪表板 (ASSUME)
```

---

## 🛠️ 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 数据处理 | pandas 3.0.3 + pyarrow 22.0 | DataFrame 操作，Parquet 后端 |
| 机器学习 | scikit-learn 1.8 + xgboost 3.2 | 时序分割、XGBoost 回归 |
| 电价预测 | scikit-learn Lasso | LEAR 模型 (L1 正则化线性回归) |
| 强化学习 | stable-baselines3 2.8 + gymnasium 1.2 | PPO/SAC/TD3 交易智能体 |
| 市场仿真 | ASSUME 0.6.0 | 多智能体电力市场仿真 |
| 可解释性 | SHAP ≥0.46 | TreeExplainer + LinearExplainer |
| 统计检验 | epftoolbox | Diebold-Mariano + Giacomini-White |
| API | FastAPI + Pydantic v2 + uvicorn | REST + SSE streaming |
| CLI | Typer + Rich | 命令行工具 |
| LLM | LangChain + DeepSeek API | 自然语言对话助手 + 工具调用 |
| 可视化 | Plotly 6.7 | 交互式图表 |
| 开发 | Jupyter 1.1.1 | 渐进式学习 notebooks |

---

## 🔑 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | LLM Agent 所需（Phase 4） |
| `ELLECTRIC_API_URL` | `http://localhost:8000` | LLM tools 连接 API 地址 |
| `ELLECTRIC_MODEL_DIR` | `ellectric/models/` | 模型文件目录 |
| `ELLECTRIC_DATA_DIR` | `ellectric/data/` | 数据文件目录 |

---

## ⚠️ 注意事项

- **非生产系统**：所有模型和策略仅供学习参考，不构成交易建议
- **数据限制**：OWID 公开数据为年度级，需折算为日均值，精度有限
- **仿真简化**：ASSUME 仿真为简化市场模型，与中国实际电力市场规则存在差异
- **仅支持 Python 3.11+**

---

## 📄 License

MIT
