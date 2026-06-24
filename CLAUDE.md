# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

AI + 电力交易技术学习平台。跑通"山东 15min 现货数据接入 → 负荷/电价预测 → 电力市场仿真 → 自动交易策略"的端到端技术闭环。非生产系统，教育/学习用途。

**Python 3.11+。** 位于 `ellectric/` 目录下。

**当前 MVP：山东 15min 数据**（745 天 × 96 点 / 日，2024-01 ~ 2026-01，真实出清价 + 风光核水出力）

## 常用命令

```bash
# 一键环境安装
cd ellectric && chmod +x setup.sh && ./setup.sh

# 激活虚拟环境
source ellectric/.venv/bin/activate

# 安装 ASSUME 仿真框架
pip install "assume-framework[learning]==0.6.0"

# 启动 Jupyter（学习 notebooks）
jupyter notebook ellectric/notebooks/

# 启动 FastAPI 服务
uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000

# CLI 命令
python -m ellectric.cli.main forecast load 24
python -m ellectric.cli.main simulate summer_peak --days 7
python -m ellectric.cli.main backtest 2022-08-01 2022-08-31 ppo --model-path model.zip
python -m ellectric.cli.main explain xgboost 0

# ASSUME 仿真验证
python ellectric/scripts/verify_assume.py

# Phase 3 验证
bash ellectric/scripts/verify_phase3.sh
```

## 架构

### 包层次

```
ellectric/
├── pipeline/       # 核心机器学习/交易管道
│   ├── data_loader.py      # DataLoader ABC, OWIDChinaLoader, ChineseDataLoader, ShandongDataLoader, create_loader()
│   ├── shandong_loader.py  # ShandongDataLoader — 山东 15min CSV (21列 extended schema)
│   ├── cleaner.py          # clean_data(), validate_schema(), 数据质量评分
│   ├── features.py         # FeatureEngineer 类, Tier 1-3 渐进式特征
│   ├── forecaster.py       # XGBoostForecaster, persistence_forecast(), P&L 计算
│   ├── price_forecaster.py # LEARForecaster (Lasso), 电价预测
│   ├── price_loader.py     # PriceDataLoader — Excel/CSV 电价数据
│   ├── backtester.py       # BacktestRunner, 基线策略 (persistence/mean/oracle)
│   ├── trading_env.py      # ElectricityMarketEnv — Gymnasium RL 环境
│   ├── rl_trainer.py       # BaseRLAgent ABC, PPO/TD3/SAC 适配器, RLAgentFactory
│   ├── shap_explainer.py   # SHAP TreeExplainer (XGBoost) + LinearExplainer (LEAR)
│   ├── statistical_tests.py # Diebold-Mariano + Giacomini-White 检验 (需 epftoolbox)
│   └── __init__.py
├── fetch/           # 数据抓取层
│   ├── weather.py          # WeatherFetcher — Open-Meteo 免费气象 (济南/青岛)
│   └── __init__.py
├── api/server.py    # FastAPI app — /predict, /simulate, /backtest, /explain, /health
├── service/         # 请求处理层（桥接 API/CLI 到 pipeline）
│   ├── schemas.py      # Pydantic v2 请求/响应模型
│   └── handlers.py     # run_forecast(), run_simulate(), run_backtest(), run_explain()
├── cli/main.py      # Typer CLI — 4 子命令 + ask (LLM 对话)
├── llm/             # LangChain agent (DeepSeek API)
│   ├── agent.py        # create_agent_executor(), ask_agent()
│   ├── tools.py        # @tool 函数 — 通过 HTTP 调用本地 API
│   └── chat.py
├── assume/          # ASSUME 仿真脚本 + 配置
├── notebooks/       # 01-10 渐进式 Jupyter notebooks
├── scripts/         # 验证/演示脚本
└── data/            # 数据文件 (.parquet, .xlsx, .joblib, .zip)
```

### 数据流

```
OWID GitHub / 本地文件
  → DataLoader.load_data() → DataFrame[timestamp, load_mw]  (数据合约)
  → clean_data()           → 缺失值填充, 异常值报告不删除, UTC 标准化
  → FeatureEngineer        → Tier 1→2→3 特征工程
  → XGBoostForecaster / LEARForecaster  → 训练 + 评估
  → BacktestRunner / ElectricityMarketEnv  → 回测 + 策略对比
```

### 关键设计模式

- **抽象基类 + 工厂**: `DataLoader` ABC → `OWIDChinaLoader`, `ChineseDataLoader`; `BaseRLAgent` ABC → PPO/TD3/SAC 适配器
- **数据合约**: `REQUIRED_COLUMNS = {"timestamp", "load_mw"}` 定义固定的 module 级 schema
- **三层特征**: Tier 1 (核心) → Tier 2 (中级) → Tier 3 (高级)，渐进式学习
- **延迟导入**: `service/handlers.py` 所有 pipeline 导入均为函数内延迟导入，避免模块级循环依赖
- **可选依赖防护**: 非核心包 (holidays, shap, epftoolbox) 以 `try/except ImportError` 包裹
- **三明治架构**: API → Service (handlers) → Pipeline → 模型。API/CLI/LLM 三层并行调用同一 Service 层
- **时区**: 所有 timestamp 强制 UTC

## 代码规范

完整规范见 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md`。要点：

- **模块级 docstring**: 中英双语，`=====` 下划线分隔标题，`~~~~` 波浪线分隔段落
- **段落分隔**: `# ═════════════` (顶级分界) / `# ── ... ──` (子级分界)
- **日志**: 每个模块 `logger = logging.getLogger(__name__)` — 独立 logger，中文描述
- **类型标注**: 所有函数签名使用完整类型标注
- **内部方法**: `_` 前缀，`self._` 前缀追踪实例状态
- **Git commit**: `<类型>(<范围>): <中文描述>` — 类型: 新增/修复/重构/文档/清理

## 数据合约

所有 DataLoader 产出、下游模块消费的 DataFrame 必须包含:
- `timestamp`: datetime64[ns, UTC]
- `load_mw`: float64 (MW)

禁止别名: `date`, `datetime`, `load`, `demand`, `power`, `日期`, `用电量`

## 测试与当前状态

**无自动化测试**。验证方式：
- Jupyter notebooks 逐步骤学习 + 验证
- `train_evaluate()` 计算 MAE/RMSE/MAPE/R² 作为训练期间评估
- `python ellectric/scripts/verify_assume.py` 验证 ASSUME 安装

## 工作流

开发流程使用 **SillySpec** + **Karpathy Guidelines**。GSD 历史资产位于 `.planning/`。

当前已完成 4 个阶段:
1. **Phase 1**: OWID 数据接入 → 清洗 → 特征 → XGBoost 预测
2. **Phase 2**: LEAR 电价预测 + ASSUME 电力市场仿真
3. **Phase 3**: RL 交易智能体 (PPO/SAC/TD3) + Backtesting + SHAP 可解释性
4. **Phase 4**: FastAPI + CLI + LangChain/DeepSeek LLM 接口

执行开发任务前先读取 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md`（代码风格）和 `.sillyspec/docs/Ellectric/scan/ARCHITECTURE.md`（架构）。详细的模块文档见 `.sillyspec/docs/Ellectric/modules/`。

## 环境变量

- `DEEPSEEK_API_KEY` — LLM agent 所需 (Phase 4)
- `ELLECTRIC_API_URL` — LLM tools 连接 API (默认 `http://localhost:8000`)
- `ELLECTRIC_MODEL_DIR` — 模型文件目录 (默认 `ellectric/models/`)
- `ELLECTRIC_DATA_DIR` — 数据文件目录 (默认 `ellectric/data/`)
