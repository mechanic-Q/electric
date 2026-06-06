# Ellectric — AI + 电力交易技术学习平台

> 🎯 基于北京图迹科技 (GeekBidder) 的技术画像，使用开源工具搭建的 AI+电力交易学习原型。
> 跑通"数据获取 → 负荷预测 → 市场仿真 → 自动交易"的端到端技术闭环。

## 🚀 快速开始

```bash
chmod +x setup.sh && ./setup.sh      # 一键安装 (<30分钟)
source .venv/bin/activate             # 激活虚拟环境
jupyter notebook notebooks/            # 启动 Jupyter
```

**学习顺序:**
1. `01_data_ingestion.ipynb` — 数据获取（OWID 中国电力数据）
2. `02_data_cleaning.ipynb` — 数据清洗（IQR 检测、缺失值处理）
3. `03_feature_engineering.ipynb` — 特征工程（时间特征、滞后特征）
4. `04_load_forecasting.ipynb` — 负荷预测（XGBoost 训练与评估）
5. `05_end_to_end_baseline.ipynb` — 端到端管道（数据→预测→盈亏→图表）

## 🏗️ 项目结构

```
ellectric/
├── setup.sh                  # 一键安装脚本
├── requirements.txt          # Python 依赖（版本锁定）
├── docker-compose.yml        # Docker 骨架（Phase 2 启用）
├── README.md                 # 本文件
├── pipeline/                 # 核心 Python 模块
│   ├── __init__.py
│   ├── data_loader.py        # 数据加载器（OWID 自动 + 手动本地）
│   ├── cleaner.py            # 数据清洗管道
│   ├── features.py           # 特征工程（渐进式，3 层）
│   └── forecaster.py         # 预测引擎（持续法 + XGBoost + P&L）
├── notebooks/                # Jupyter 学习笔记本
│   ├── 01_data_ingestion.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_load_forecasting.ipynb
│   └── 05_end_to_end_baseline.ipynb
├── data/                     # 本地数据目录（手动下载的数据放这里）
│   └── .gitkeep
└── docs/
    └── chinese-electricity-data-guide.md  # 中国电力数据获取指南
```

## 📊 数据 Schema

| 列名 | 类型 | 含义 | 数据源 |
|------|------|------|--------|
| `timestamp` | datetime64[ns, UTC] | 时间戳 | OWID / 本地文件 |
| `load_mw` | float64 | 日均用电负荷 (MW) | OWID |
| `generation_twh` | float64 | 年发电量 (TWh) | OWID |
| `demand_twh` | float64 | 年用电量 (TWh) | OWID |
| `solar_twh` | float64 | 太阳能发电 (TWh) | OWID |
| `wind_twh` | float64 | 风电发电 (TWh) | OWID |
| `coal_twh` | float64 | 煤电发电 (TWh) | OWID |
| `region` | str | 区域标识 | OWID / 本地文件 |

## 🔧 技术栈

| 层级 | 工具 | 版本 | 用途 |
|------|------|------|------|
| 数据处理 | pandas | 3.0.3 | 核心 DataFrame 操作 |
| 机器学习 | scikit-learn | 1.8.0 | TimeSeriesSplit, StandardScaler |
| 预测模型 | XGBoost | 3.2.0 | 梯度提升树负荷预测 |
| 可视化 | plotly | 6.7.0 | 交互式时序图表 |
| 环境 | Jupyter | 1.1.1 | 学习笔记本 |
| 数据存储 | Parquet | pyarrow 22.0.0 | 列式存储 |

## 🎯 学习路径

### Phase 1: 数据基础与预测（当前阶段）
- [x] 环境搭建与依赖安装
- [x] OWID 中国电力数据自动拉取
- [x] 数据清洗管道
- [x] 持续法基线预测
- [x] XGBoost 负荷预测
- [x] 端到端 P&L 可视化

### Phase 2: 深度预测与市场仿真（下一阶段）
- OpenSTEF 自动化预测管道
- ASSUME 电力市场仿真
- 多模型对比仪表板

### Phase 3: 交易智能体
- 强化学习交易策略
- 端到端回测

### Phase 4: 整合与大模型
- FastAPI 后端服务
- LLM 交易助手

## 🔌 ASSUME 电力市场仿真

### 安装

```bash
pip install "assume-framework[learning]==0.6.0"
```

这将安装 ASSUME 核心框架 + PyTorch (CPU) + stable-baselines3 + gymnasium。

### 验证安装

```bash
python scripts/verify_assume.py
```

预期输出：

```
==================================================
  ASSUME 安装验证报告
==================================================

[1/4] Python 版本检查
[2/4] 导入验证
  [PASS] ASSUME 导入成功
  [PASS] PyTorch 导入成功 -> version: 2.x.x (CPU only)
  [PASS] stable-baselines3 导入成功 -> version: 2.x.x
  [PASS] gymnasium 导入成功 -> version: 1.x.x

[3/4] 版本检查
  ASSUME 版本: 0.6.0

[4/4] 最小仿真运行
  [PASS] 最小仿真运行成功

==================================================
  状态: 全部通过 ✓
==================================================
```

### 依赖锁定文件

`requirements-assume.txt` 包含已锁定的 ASSUME 及相关依赖版本。

### 注意

- ASSUME 独立于 Phase 1 的 `requirements.txt`，安装在同一个 venv 中
- 仿真结果默认输出为 CSV 文件（无需 Docker）
- Docker Compose TimescaleDB + Grafana 集成见 task-10

## 📚 参考文献

- [OWID Energy Data](https://github.com/owid/energy-data) — 全球能源数据库
- [XGBoost 文档](https://xgboost.readthedocs.io/) — 梯度提升框架
- [ASSUME 框架](https://github.com/assume-framework/assume) — 电力市场仿真框架
