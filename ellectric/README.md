---
author: lmr
created_at: 2026-06-27 19:12:11
---

# Ellectric — AI + 电力交易技术学习平台

> 🎯 以山东 15min 现货数据为 MVP 的 AI+电力交易学习原型。
> 跑通"数据获取 → 负荷/电价预测 → 市场仿真 → 自动交易"的端到端技术闭环。

**当前 MVP：山东** — 745 天 × 96 点/日 15min 真实出清价 + 风光核水出力，2024-01 ~ 2026-01。

## 🚀 快速开始

```bash
chmod +x setup.sh && ./setup.sh      # 一键安装 (<30分钟)
source .venv/bin/activate            # 激活虚拟环境
jupyter notebook notebooks/          # 启动 Jupyter
```

**Notebook 学习顺序:**
1. `01_data_ingestion.ipynb` — 数据获取（山东 15min CSV）
2. `02_data_cleaning.ipynb` — 数据清洗（IQR 检测、缺失值处理）
3. `03_feature_engineering.ipynb` — 特征工程（时间特征、滞后特征、气象）
4. `04_load_forecasting.ipynb` — 负荷预测（XGBoost 训练与评估）
5. `05_end_to_end_baseline.ipynb` — 端到端管道（数据→预测→盈亏→图表）
6. `06_price_forecasting.ipynb` — 电价预测（LEAR Lasso）
7. `07_model_comparison_dashboard.ipynb` — 模型对比仪表板（DM/GW 检验）
8. `08_assume_results.ipynb` — ASSUME 电力市场仿真
9. `09_rl_trading_agent.ipynb` — RL 交易智能体（PPO/TD3/SAC）
10. `10_multi_agent_backtest.ipynb` — 多策略回测对比
11. `11_model_explainability.ipynb` — SHAP 可解释性

## 🏗️ 项目结构

```
ellectric/
├── setup.sh                  # 一键安装脚本
├── requirements.txt          # Python 依赖
├── README.md                 # 本文件
├── config.py                 # TimeConfig — 时间分辨率全局配置 (96/672/15min)
├── pipeline/                 # 核心 Python 模块
│   ├── data_loader.py        # DataLoader ABC + 工厂 (owid/manual/ember/shandong)
│   ├── shandong_loader.py    # ShandongDataLoader — 山东 15min CSV (21列)
│   ├── cleaner.py            # 数据清洗管道
│   ├── features.py           # 特征工程（渐进式，4 层）
│   ├── forecaster.py         # XGBoost 负荷预测
│   ├── price_forecaster.py   # LEAR 电价预测 (Lasso)
│   ├── price_loader.py       # PriceDataLoader — 电价数据
│   ├── backtester.py         # BacktestRunner — 多策略回测
│   ├── trading_env.py        # ElectricityMarketEnv — Gymnasium RL 环境
│   ├── rl_trainer.py         # PPO/TD3/SAC 训练适配器
│   ├── shap_explainer.py     # SHAP 可解释性
│   └── statistical_tests.py  # Diebold-Mariano / Giacomini-White 检验
├── fetch/                    # 数据抓取层
│   ├── weather.py            # WeatherFetcher — Open-Meteo 免费气象 (济南/青岛)
│   └── __init__.py
├── notebooks/                # 11 个 Jupyter 学习笔记本
├── data/                     # 数据目录
│   └── shandong/
│       ├── 山东_2024-2026_15min.csv  # 核心数据 (11.3 MB, 71520行)
│       └── README.md                 # 数据资产说明
└── docs/
    └── chinese-electricity-data-guide.md
```

## 📊 数据源

| 数据源 | 粒度 | 时间范围 | 列数 | 用途 |
|--------|------|----------|------|------|
| **山东 15min CSV**（核心） | 15 分钟 (96点/日) | 2024-01 ~ 2026-01, 745天 | 21列 | 负荷预测、电价预测、RL训练、回测 |
| **Open-Meteo 气象** | 小时级 | 2024-01 ~ 2026-01 | 12列 (2城×6变量) | 特征增强（气温、辐照度、风速、湿度） |
| OWID | 年度 | 2000–2025 | 7列 | 宏观趋势参考（教学遗留） |
| Ember | 小时 | 近年 | 探索性 | 全球电力数据 |

### 山东数据

`create_loader("shandong").load_data()` → 71,520 行 × 23 列 DataFrame:

| 核心列 | 说明 | 覆盖率 |
|--------|------|--------|
| `timestamp` | datetime64[ns, UTC] | 100% |
| `load_mw` | 直调负荷 (MW) | 100% |
| `rt_price` | 实时出清价格 (元/MWh) | 99.9% |
| `da_price` | 日前出清价格 (元/MWh) | 25% (每小时1点) |
| `wind_actual_mw` | 风电实际出力 | 100% |
| `solar_actual_mw` | 光伏实际出力 | 100% |
| `nuclear_actual_mw` | 核电实际出力 | 100% |
| `tie_line_actual_mw` | 联络线受电 | 100% |
| `is_holiday` / `is_weekend` | 节假日/周末标记 | 100% |

### 数据合约

所有 DataLoader 产出必须包含：
- `timestamp`: datetime64[ns, UTC]
- `load_mw`: float64 (MW)

山东 DataLoader 在此合约基础上**宽松附加** 21 列。

## 🔧 技术栈

| 层级 | 工具 | 版本 | 用途 |
|------|------|------|------|
| 数据处理 | pandas | 3.0.3 | 核心 DataFrame 操作 |
| 机器学习 | scikit-learn | 1.8.0 | TimeSeriesSplit, StandardScaler |
| 负荷预测 | XGBoost | 3.2.0 | 梯度提升树 |
| 电价预测 | scikit-learn Lasso | 1.8.0 | LEAR 模型 |
| RL | stable-baselines3 | 2.x | PPO/TD3/SAC |
| 可视化 | plotly | 6.7.0 | 交互式时序图表 |
| 仿真 | ASSUME | 0.6.0 | 电力市场仿真框架 |
| 可解释性 | SHAP | — | 模型解释 |
| 环境 | Jupyter | 1.1.1 | 学习笔记本 |
| 气象 | Open-Meteo API | 免费 | 历史气象数据 |

## 🎯 学习路径

### Phase 1: 数据基础与预测
- [x] 山东 15min 数据接入 (ShandongDataLoader)
- [x] 数据清洗管道
- [x] 特征工程 (3层渐进式)
- [x] XGBoost 负荷预测 → MAE=5526MW (8.0%)
- [x] LEAR 电价预测

### Phase 2: 市场仿真与交易
- [x] ASSUME 电力市场仿真
- [x] RL 交易智能体 (PPO/SAC/TD3)
- [x] 多策略回测对比

### Phase 3: 整合与可解释性
- [x] FastAPI + CLI + LLM 三层接口
- [x] Web Chat UI (SSE 流式)
- [x] SHAP 模型可解释性

### Phase 4: 持续改进
- [x] WeatherFetcher 气象特征集成到 features（已接入，验证待完成）
- [ ] 完整 96 维 RL training on full dataset
- [ ] 中长期合约/新能源预测特征

**本轮显式排除：**
- 准实时 T+15min 调度 — 不引入 cron/daemon/queue
- 中长期合约串 pipeline — 增强项，当前不做
- 多省/多节点市场覆盖 — MVP 保持单省山东
- 真实交易/付费数据源 — 学习原型不涉及真实资金

## 🔌 ASSUME 电力市场仿真

```bash
pip install "assume-framework[learning]==0.6.0"
python scripts/verify_assume.py
```

## 📚 参考文献

- [Zenodo: Hourly electric power load China (Wu & Kan, 2023)](https://zenodo.org/records/8322210) — 31省小时级负荷
- [Open-Meteo Historical Weather API](https://open-meteo.com/) — 免费历史气象
- [XGBoost 文档](https://xgboost.readthedocs.io/)
- [ASSUME 框架](https://github.com/assume-framework/assume) — 电力市场仿真
