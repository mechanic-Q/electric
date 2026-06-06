# Phase 1: 数据基础 + 基础预测 — 上下文

**收集日期:** 2026-05-20
**状态:** 准备规划

<domain>
## Phase 边界

交付一个可运行的 Jupyter 学习环境，用户能够：(1) 一键安装所有依赖，(2) 从本地开放数据平台获取并清洗中国电力负荷数据（小时级粒度），(3) 训练含正确时间验证的 XGBoost 负荷预测模型，(4) 运行端到端基线管道（持久性预测 → 仿真 → P&L），证明所有系统层已连通。这是"证明骨架可用"的阶段 — 在 Phase 2 引入领域特定框架（OpenSTEF、ASSUME）之前先跑通完整管道。
</domain>

<decisions>
## 实现决策

### 数据源选择
- **D-01:** 使用**中国电力负荷数据**，来自地方政府开放数据平台（如菏泽市公共数据开放网、广东省公共数据开放平台）。目标：**小时级负荷数据**。这与学习图迹科技的国内电力交易思路一致。
- **D-02:** 如果从开放平台获取不到小时级数据，降级使用 epftoolbox 内置数据集（EPEX/PJM），保持管道可运行，同时继续寻找中国数据源。数据加载层必须抽象化，使数据源可以无缝切换而不影响下游代码。
- **D-03:** 构建数据抓取模块，处理选定中国数据平台的具体格式/API。预期为手动下载 + 解析工作流（而非像 PUDL 那样的 pip 可安装包）。在 notebook 中清晰记录数据获取步骤。

### 数据存储与格式
- **D-04:** Parquet 作为主要数据格式 — 便携、列式、pandas 原生、快速读写，无需数据库服务器。
- **D-05:** 标准化列 schema：`timestamp`（datetime64[ns, UTC]）、`load_mw`（float64），外加元数据列（region, data_source）。所有时间戳均为 UTC，pandas dtype 带时区感知。

### 环境搭建
- **D-06:** pip + venv 配合 `requirements.txt`（固定版本）。一键搭建：`python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`。目标：干净机器上 < 30 分钟。
- **D-07:** Docker Compose 可选（用于 TimescaleDB + Grafana）— Phase 1 不需要。仅创建骨架 YAML，标记为"Phase 2 依赖"。

### 特征工程方案
- **D-08:** 渐进式特征设计 — 从 3-5 个核心特征开始（hour、day-of-week、month、is_weekend、lag-24h），验证模型可运行，然后添加 holiday flags、lag-168h、rolling windows。每个特征添加应有独立的 notebook cell，附有添加前后指标对比。
- **D-09:** **关键**：所有 scaler（StandardScaler 等）仅在使用 `TimeSeriesSplit` 的训练数据上 fit。绝不在完整数据集上调用 `fit()`。这是调研中发现的 #1 陷阱，必须由 notebook 结构本身强制执行。

### Notebook 架构
- **D-10:** 模块化结构：轻量 Jupyter notebook 导入可复用的 `.py` 模块（`pipeline/data_loader.py`、`pipeline/cleaner.py`、`pipeline/features.py`、`pipeline/forecaster.py`）。Notebook 用于探索和可视化；`.py` 模块用于生产逻辑。
- **D-11:** Notebook 命名规范：`01_data_ingestion.ipynb`、`02_data_cleaning.ipynb`、`03_feature_engineering.ipynb`、`04_load_forecasting.ipynb`、`05_end_to_end_baseline.ipynb`。顺序化、自文档化。

### 端到端基线
- **D-12:** 基线使用持久性预测（昨天的负荷 = 今天的预测）加最小 P&L 计算（假设固定电价，按预测买入，按实际结算）。不依赖 ASSUME — 纯 Python。目的：在 < 50 行代码内证明数据 → 预测 → 交易管道可用。
- **D-13:** 基线 P&L 图验证：(a) 预测流入交易逻辑，(b) 累计利润图渲染成功，(c) 管道层已连通。P&L 数值不必为正 — 重点是集成，而非盈利。

### 模型评估
- **D-14:** 主要指标：**MAE**（Mean Absolute Error），在时间测试切分上计算（最后 20% 数据）。保持简单，易于学习理解。

### 可视化
- **D-15:** 使用 **plotly** 做交互式可视化 — 负荷 vs 预测叠加（可缩放）、误差分布、时变残差。plotly 支持悬停查看精确数值，对学习很有价值。

### 留给 Claude 的自由裁量
- XGBoost 超参数具体值（n_estimators、max_depth、learning_rate）— 从默认值开始，后续调优
- 缺失数据或下载失败时的错误消息措辞
- plotly 图表的配色方案和图形尺寸
- `requirements.txt` 的具体结构（扁平 vs 带注释分组）
- 优先选择哪个中国开放数据平台（在实现过程中调研决定）
</decisions>

<canonical_refs>
## 规范参考

**下游代理在规划或实现之前必须阅读以下内容。**

### 项目定义
- `.planning/PROJECT.md` — 核心价值、约束条件、不在范围内的边界
- `.planning/REQUIREMENTS.md` — 全部 24 项 v1 需求；Phase 1 覆盖 ENV-01..03、DATA-01..04、PRED-01、VIZ-01

### 技术栈
- `.planning/research/STACK.md` — 固定版本技术栈：Python 3.11、pandas 3.0.3、scikit-learn 1.8.0、XGBoost 3.2.0、plotly 6.7.0

### 陷阱（必读）
- `.planning/research/PITFALLS.md` — **Look-ahead bias**（在完整数据上调用 scaler、随机切分）、**spike-as-noise**（对价格取对数会破坏信号）、以及**不早做端到端**的陷阱。Phase 1 必须主动防范第一个和第三个。

### 架构
- `.planning/research/ARCHITECTURE.md` — 分层管道：数据层 → 预测层 → 市场层 → 智能体层。Phase 1 交付数据层 + 手动预测层连接器。

### 特性
- `.planning/research/FEATURES.md` — 基本特性列表、依赖链。

### 路线图
- `.planning/ROADMAP.md` § Phase 1 — 9 项需求、5 项成功标准、MVP 模式
</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用资产
- 暂无 — 绿地项目。Phase 1 所有代码均为新代码。

### 已建立的模式
- `pipeline/` 目录存放 `.py` 模块（本阶段建立为项目规范）
- `notebooks/` 目录存放 Jupyter 探索内容（本阶段建立）
- `requirements.txt` 含固定版本（本阶段建立）

### 集成点
- Phase 1 `DataLoader` 类将被 Phase 2 消费（OpenSTEF + ASSUME 输入）
- Phase 1 `cleaned_load.parquet` 输出 schema 将成为下游阶段的契约
- Phase 1 `Forecaster.predict()` 接口将在 Phase 2 被 OpenSTEF 替换 — 按抽象设计
</code_context>

<specifics>
## 具体想法

- 你想学图迹科技的实战技术，所以优先使用中国电力市场数据而非美国数据
- 使用 plotly 做交互式可视化，方便学习中探索数据细节
- 评估指标保持简单（仅 MAE），降低学习门槛
</specifics>

<deferred>
## 已推迟的想法

- 美国 PJM 数据 (PUDL) — 作为备用数据源，当中国数据不可用时降级使用
- enda 能源时序数据处理工具 — 研究发现其 H2O 依赖与项目约束冲突，推迟到 Phase 2 评估
- 天气数据集成 — 推迟到 Phase 2（OpenSTEF 自带天气特征工程）
- HAMLET 本地市场仿真 — repo 可能不可用（404），优先级低于 ASSUME
</deferred>

---
*Phase: 01-data-foundation-basic-prediction*
*上下文收集于: 2026-05-20*
