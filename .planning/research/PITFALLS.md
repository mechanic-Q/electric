# 陷阱调研

**领域:** AI驱动的电力交易学习平台
**调研日期:** 2026-05-20
**置信度:** HIGH

> 来源: ASSUME 官方文档 (assume.readthedocs.io), epftoolbox docs, OpenSTEF GitHub, ASSUME 发布说明 v0.1.0–v0.6.1, JOSS paper (Harder et al. 2025), Energy and AI paper (Harder et al. 2023).

## 关键陷阱

导致悄无声息错误结果的错误 —— 预测看起来不错，仿真运行了，但结论是无效的。

### 陷阱 1: 时序数据准备中的 Look-Ahead Bias

**出了什么问题:**
模型在训练期间意外地看到了未来信息。在电力预测中，表现为:
- 在划分之前对整个数据集计算滚动统计 (移动平均, 标准差)
- 使用整个时间范围计算的均值和标准差来归一化/缩放特征
- 使用 `train_test_split(random_state=42)` 而非时序划分
- 将 "明天的天气预报" 作为特征包含在内，而该预报本身嵌入了未来信息

模型在验证时达到不切实际的高准确度，但在真实数据上完全失败。

**为什么发生:**
标准 ML 工具 (`sklearn.preprocessing.StandardScaler`, `sklearn.model_selection.train_test_split`) 是为 i.i.d. 数据设计的。能源时序数据不是 i.i.d. —— 小时 t 与小时 t-1 高度相关。初学者将他们从分类/图像问题中学到的 ML 工作流直接应用到时间能源数据上，而没有调整预处理管道。

**如何避免:**

```python
# 错误: 在划分前对整个数据集拟合 scaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_all)  # 将未来泄露到训练中!
X_train, X_test = train_test_split(X_scaled, shuffle=False)

# 正确: 仅在训练数据上拟合 scaler
split_idx = int(len(X_all) * 0.8)
X_train, X_test = X_all[:split_idx], X_all[split_idx:]

scaler = StandardScaler()
scaler.fit(X_train)  # 仅在训练期间拟合
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 正确: 使用 TimeSeriesSplit 进行交叉验证
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X):
    # train_idx 始终在时间上 < val_idx
    X_train, X_val = X[train_idx], X[val_idx]
```

**关键原则:** 任何从数据中推导统计量的操作 (scaling, imputation, feature engineering) 必须仅使用时间戳 ≤ 当前训练截止点的数据。

**警告信号:**
- 电价预测的验证 MAE 难以置信地低 (< 1%)
- 模型在测试集上比训练集表现更好
- 代码库中未出现 `TimeSeriesSplit` 或 `BlockingTimeSeriesSplit`
- 特征重要性显示 "明天" 的特征占主导

**应解决阶段:** 阶段 1 (PRED-01 / DATA-01)。在任何模型训练之前必须预防。

**恢复成本:** HIGH — 需要从头重做所有特征工程和重新训练。

---

### 陷阱 2: 将电价当作 "普通" 商品处理 —— 压平价格尖峰

**出了什么问题:**
电价展现出在其他商品中看不到的极端特征:
- **负价格** (生产者在可再生能源过剩时付费排出电力)
- **10-100 倍均值的价格尖峰** (例如 EPEX 日前: 均值 ~€50/MWh, 尖峰到 €500-3000/MWh)
- **零价格** (完美的可再生能源/负荷平衡)
- **多模态分布** (尖峰区间 vs. 正常区间 vs. 负价格区间)

初学者应用标准 ML 损失函数 (MSE, RMSE) 和预处理 (log-transform, clipping outliers) 会破坏交易中真正重要的信号。一个 RMSE 很好的模型可能错过每一个价格尖峰 —— 使其对交易毫无用处。

**为什么发生:**
初学者在行为良好的数据集 (房价, 图像分类) 上学习 ML，其中异常值是应该去除的噪声。在电力领域，"异常值" 就是信号 —— 尖峰是交易赚钱或亏钱的时候。

**如何避免:**

```python
# 错误: 裁剪 "异常值" 破坏了交易信号
prices_clipped = prices.clip(lower=prices.quantile(0.01),
                              upper=prices.quantile(0.99))

# 错误: Log-transform 使尖峰检测不可能
prices_log = np.log(prices)  # log(-50) 是什么意思?

# 正确: 使用捕获尖峰性能的指标
from epftoolbox.evaluation import MAE, sMAPE, MASE

# 还计算尖峰特定指标
spike_threshold = prices.quantile(0.95)
spike_mask = y_true > spike_threshold
spike_mae = np.mean(np.abs(y_true[spike_mask] - y_pred[spike_mask]))
spike_recall = np.sum((y_pred > spike_threshold) & spike_mask) / np.sum(spike_mask)

# 使用 pinball loss / quantile regression 进行
# 捕获尾部行为的概率预测
```

**电力交易关键指标 (RMSE 之外):**
| 指标 | 捕获内容 |
|--------|-----------------|
| sMAPE | 尺度无关误差 |
| MASE | 相对朴素预测 |
| Diebold-Mariano test | 相对于基线的统计显著性 |
| Spike MAE / Spike Recall | 极端事件上的性能 |
| 盈亏 (PnL) | 预测的真实经济价值 |

**警告信号:**
- 预处理管道中有 clipping 或异常值移除
- 仅使用 RMSE/MAE 作为评估指标
- 预测图从未超出训练数据的 ±2σ
- 在原始价格上使用 `np.log()` 或 `BoxCox` 而没有处理负值

**应解决阶段:** 阶段 1 (PRED-01)。在训练前建立正确的评估。

---

### 陷阱 3: RL 奖励函数设计优化了错误的东西

**出了什么问题:**
在电力交易的强化学习中，奖励函数定义了智能体优化的目标。常见失败:
- **纯利润最大化无风险惩罚** → 智能体学会退化策略 (以最高价投标, 仅在市场尖峰时被接受, 95% 时间零交易量但在尖峰上获得巨大奖励)
- **仅基于被接受的投标的奖励** → 智能体学会出价低于所有人, 高接受率但负利润
- **未使用容量无惩罚** → 智能体作为 "安全" 策略闲置
- **仅在 episode 结束时奖励** → 稀疏信号, 智能体无法学习

ASSUME 文档明确警告: *"不要仅依赖奖励。必须仔细检查行为本身。"* 并且 *"更大的总奖励并不意味着学到的行为更好。"*

**为什么发生:**
奖励函数设计出奇地困难。初学者从 Atari 游戏或机器人论文复制奖励结构，其中奖励是外生的。在市场环境中，奖励从智能体交互中涌现 —— 相同策略在不同对手面前获得不同奖励。高奖励可能来自 "临时利用其他智能体的弱点" 或 "偶然发生的协调效应"。

**如何避免:**

```python
# ASSUME 的学习奖励 (来自官方文档) 包含多项:
# reward = 已执行投标的利润
#          - 运营成本
#          - 机会成本 (惩罚未充分利用的容量)
#          - 后悔项 (最小化错过的收入机会)

# 从简单开始: 在添加 RL 之前从朴素/启发式策略开始
# 在 ASSUME 配置中:
bidding_EOM: "powerplant_energy_naive"  # 阶段 1: 基线
bidding_EOM: "powerplant_energy_heuristic_flexable"  # 阶段 2: 启发式
bidding_EOM: "powerplant_energy_learning"  # 阶段 3: RL 仅在基线之后

# 始终验证行为, 而不仅仅是奖励:
# 1. 绘制投标曲线随时间变化 — 它们合理吗?
# 2. 检查接受率 — 智能体实际参与了吗?
# 3. 比较 PnL 与朴素策略 — RL 是否增加了价值?
# 4. 使用 ASSUME 内置的 Grafana dashboards 进行行为检查
```

**ASSUME 特定的 RL 安全检查 (来自官方文档):**
- 使用 `validation_episodes_interval` 在没有探索噪声的情况下评估
- 使用 `early_stopping` 配合大型 episodes 以避免选择不稳定的高奖励快照
- 使用 **最终策略** (而非最佳奖励策略) 进行评估 — ASSUME 文档: *"框架使用最终策略进行评估，以避免选择可能远不稳定的高奖励快照"*
- 监控 TensorBoard 的奖励稳定性, 而不仅仅是奖励大小
- 对储能单元设置 `train_freq` > "72h" (它们需要时间耦合)

**警告信号:**
- 智能体奖励增加但投标接受率降至零
- 智能体学会始终以极端价格投标 (最小或最大)
- 奖励曲线高度波动且有突然尖峰
- 连续训练 episodes 之间智能体行为差异巨大

**应解决阶段:** 阶段 3 (AGENT-01, AGENT-02)。使用阶段 1-2 的朴素/启发式基线来验证 RL 学习。

**恢复成本:** HIGH — 可能需要完全重新设计奖励并重新训练。

---

### 陷阱 4: 不切实际的市场假设 —— 运行一个 "完美" 市场

**出了什么问题:**
初学者用现实中不成立的假设仿真电力市场:
- **无输电约束** → 每个发电机可以服务每个负荷 (真实市场有阻塞)
- **无市场力** → 所有智能体都是价格接受者 (真实市场有寡头发电商)
- **仅单一市场** → 仅日前能量市场 (现实: 日前 + 日内 + 实时 + ancillary services + 容量市场)
- **无可再生能源间歇性** → 风电/光伏完美预见 (现实: 预测误差产生平衡需求)
- **无双重结算** → 忽略日前 vs 实时价格差异
- **到处单一出清价格** → 忽略节点/区域价格差异

结果: 在仿真中运行完美的交易策略在现实中会亏钱。

**为什么发生:**
简化假设在学习时是自然的。但电力市场有特定的结构特征，从根本上改变了最优策略。为无阻塞、单一价格市场优化的策略会在有输电瓶颈的市场中失败。

**如何避免:**

```python
# ASSUME 支持现实的市场配置:
# config.yaml 示例:
market_config:
  market_id: "EOM"
  market_mechanism: "pay_as_clear"  # 或 "pay_as_bid", "complex_clearing"
  # 对于带输电约束的区域定价:
  # market_mechanism: "complex_clearing" + grid data
  # 对于节点定价:
  # market_mechanism: "nodal_clearing" + PyPSA network

# 始终至少包含:
# 1. 基于排序法的出清 (非统一定价假设)
# 2. 多种具有不同边际成本的机组类型
# 3. 某种形式的需求弹性
# 4. 具有现实可用性曲线的可再生能源发电

# 从 ASSUME 的内置示例场景开始 (example_01a, example_03):
# 这些已包含现实的德国市场配置
```

**渐进现实主义方法:**
1. **阶段 2 (SIM-01):** 单区域, 统一出清价, 无阻塞 — 学习市场机制
2. **阶段 3 (SIM-02/AGENT-01):** 添加输电约束, 区域定价, 多个市场
3. **阶段 4 (高级):** 复杂出清含 block/linked bids, 再调度, 节点定价

**警告信号:**
- 仿真中所有发电机总是被调度
- 价格始终在狭窄区间内
- 区域/节点之间无价格差异
- 100% 可再生能源利用无弃风弃光
- 从未出现负价格

**应解决阶段:** 阶段 2 (SIM-01) 和阶段 3 (SIM-02, AGENT-01)。

---

### 陷阱 5: 不早日进行端到端运行 —— "完美模型, 无集成" 陷阱

**出了什么问题:**
学习者花费数周时间完善负荷预测模型 (RMSE 优化, 超参数调优, 花哨的架构), 然后才将其连接到市场仿真或交易智能体。当他们最终集成时发现:
- 预测格式不符合仿真期望 (24h 窗口 vs. 1h, 不同时区)
- 模型针对准确度指标进行了优化，但这些指标不能转化为交易 PnL
- 管道延迟使预测在到达智能体之前就已过时
- 真实数据有模型无法处理的缺失/节假日/时区变化

**为什么发生:**
学术 ML 文化奖励准确度排行榜。行业奖励工作的系统。学习者默认为学术模式，因为这是教程和 Kaggle 竞赛强化的模式。

**如何避免:**

```python
# 阶段 1: 在一天内端到端
# 第 1 天工作流:
# 1. 加载 PUDL 数据 (2 小时)
# 2. 训练一个简单模型: 预测下一小时 = 上一小时 (10 分钟)
# 3. 将朴素预测插入最小市场仿真 (1 小时)
# 4. 查看价格, 查看用朴素预测 "交易" 是否赚/亏钱
# 结果: 你已经跑通了完整闭环。现在改进每一块。

# 这种 "朴素端到端" 验证了:
# - 数据管道工作
# - 预测格式匹配仿真输入
# - 你知道 "更好" 意味着什么 (击败朴素基线 PnL)
# - 你在第 1 天就发现了集成问题, 而非第 8 周
```

**渐进集成原则:**
| 阶段 | 模型复杂度 | 集成深度 |
|-------|---------------------|-------------------|
| 阶段 1 (第 1-2 周) | 朴素 persistence | 完整管道运行 |
| 阶段 2 (第 3-8 周) | XGBoost + OpenSTEF | 配合 ASSUME simulation |
| 阶段 3 (第 8-12 周) | RL agent | 预测 → 仿真 → 交易 |
| 阶段 4 (第 12 周+) | LLM + advanced | 完整平台后端 |

**警告信号:**
- 你已经 "改进模型" 2+ 周而没有运行下游仿真
- 你的评估脚本没有从仿真/交易模块导入任何东西
- 你有 5 个模型变体但有 0 次端到端运行

**应解决阶段:** 阶段 1。这是过程纪律, 不是代码修复。

---

### 陷阱 6: 混淆日前结算与实时 —— 双重结算差距

**出了什么问题:**
电力市场运行在双重结算系统上: 日前市场 (DAM) + 实时市场 (RTM)。初学者只建模日前市场, 假设:
- 日前价格 = 实时价格 (它们显著分歧)
- 所有电力都在日前交易 (实际约 80-90%, 其余在日内/实时)
- 结算是单一交易 (现实: 日前是金融承诺, 实时结算物理偏差)

在日前看起来盈利的策略可能在实时结算时因偏差费用而损失惨重, 尤其是对间歇性发电机。

**为什么发生:**
大多数公开数据集和教程聚焦于日前价格, 因为它们更易获取。实时市场数据更难找到。双重结算机制也确实复杂且容易被忽视。

**如何避免:**

```python
# 需要建模的关键市场概念 (即使近似):

# 1. DAM 价格 != RTM 价格
# 在 PJM 2019-2023, DAM-RTM 价差标准差约 $8/MWh
# 极端事件期间出现过 $100+/MWh 的价差

# 2. 偏差结算: 发电机为偏差付费
# 如果你在日前投标 100 MW 但只发了 80 MW (风速下降):
# 你必须以可能高得多的价格在实时市场购买 20 MW

# 3. ASSUME 支持顺序市场参与:
# 配置多个市场 (EOM day-ahead + CRM/intraday)
# ASSUME 中学习智能体现在可以参与顺序市场
# (在 v0.4.0 中添加: "Learning agents to participate in sequential markets")

# 最低现实设置:
market_configs = [
    {"market_id": "EOM", "product_type": "energy_day_ahead"},
    {"market_id": "CRM_pos", "product_type": "capacity_reserve_pos"},
    {"market_id": "CRM_neg", "product_type": "capacity_reserve_neg"},
]
```

**警告信号:**
- 你的仿真只有一个市场
- 你从不计算偏差成本/费用
- 你假设发电 = 投标量完全匹配
- 你的 PnL 就是 `price × volume` 无调整

**应解决阶段:** 阶段 2 (SIM-01) — 引入双重结算概念。阶段 3 — 在仿真中实现。

---

## 中等严重度陷阱

### 陷阱 7: 使用 XGBoost 无时间意识 —— 在整个数据集上做特征工程

**出了什么问题:**
工程师正确地创建滞后特征 (price_t-1, price_t-24, price_t-168), 然后在完整的数据集 (包括测试期) 上做特征选择或重要性排名。这通过特征选择过程本身泄露了未来信息。

**如何避免:**
```python
# 错误: 划分前的特征选择
from sklearn.feature_selection import mutual_info_regression
mi = mutual_info_regression(X_all, y_all)  # 泄露

# 正确: 在每个时序 fold 内做特征选择
for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_t, y_t = X[train_idx], y[train_idx]
    mi = mutual_info_regression(X_t, y_t)  # 仅在训练数据上
    selected_features = features[mi > threshold]
```

**警告信号:** 特征选择代码未引用 `train_idx`/`val_idx`。

**应解决阶段:** 阶段 1 (PRED-01)。

---

### 陷阱 8: 回测中的幸存者偏差 —— 仅在 "正常" 期间测试

**出了什么问题:**
在 2017-2019 (稳定市场) 上回测交易策略并得出结论它有效。该策略在以下时期会灾难性地失败:
- 德州 2021 年冬季风暴 (ERCOT 价格达到 $9,000/MWh 上限)
- 欧洲能源危机 2022 年 (EPEX 价格达到历史平均的 5-10 倍)
- 任何极其干燥的可再生能源或输电故障期间

**如何避免:**
```python
# 始终在压力期上测试
test_periods = [
    ("2017-01-01", "2019-12-31"),  # 正常
    ("2020-01-01", "2020-06-30"),  # COVID 需求冲击
    ("2021-06-01", "2021-09-30"),  # 欧洲天然气价格尖峰开始
    ("2022-01-01", "2022-12-31"),  # 全面能源危机
]

for name, (start, end) in test_periods:
    results[name] = backtest(strategy, prices[start:end])

# 策略应在所有期间存活 (不一定盈利)
```

**应解决阶段:** 阶段 3 (AGENT-02) — 包含压力测试场景。

---

### 陷阱 9: 忽略排序法效应 —— 假设平坦供给曲线

**出了什么问题:**
学习者将电力供给建模为简单的生产函数: `price = f(demand, fuel_cost)`。这忽略了基本的市场机制: 排序法。发电机从最便宜到最昂贵调度。随着需求增加, 更贵的发电机 (燃气调峰, 燃油) 设定了价格。当跨越排序法 "台阶" 时, 小幅需求增加可能导致巨大的价格跳跃。

**如何避免:**
```python
# ASSUME 通过其投标机制自然地实现排序法
# 每个机组按其边际成本投标 — 市场出清找到交点

# 理解排序法有助于调试仿真结果:
# 如果你的仿真价格过于平坦, 检查:
# 1. 你是否包含了调峰机组 (高边际成本)?
# 2. 你的需求变化是否足够跨越排序法台阶?
# 3. 你是否在建模可再生必发 (零边际成本)?

# ASSUME 可视化包括 Grafana dashboard 上的排序法图
# (在 v0.5.1 中添加) — 使用这些来验证现实的排序法行为
```

**应解决阶段:** 阶段 2 (SIM-01)。

---

### 陷阱 10: 管道耦合 —— 预测和交易在同一进程中

**出了什么问题:**
预测模型和交易智能体紧密耦合 —— 智能体直接调用 `model.predict()`。这使得:
- 无法在不重启智能体的情况下更新模型
- 无法用同一智能体比较不同模型
- 无法仿真预测延迟或误差
- 无法用 "完美预见" 测试智能体 (对建立上界有用)

**如何避免:**
```python
# 基于接口的分离:
class ForecastProvider(Protocol):
    def get_forecast(self, timestamp: pd.Timestamp,
                     horizon_hours: int) -> pd.DataFrame:
        """从 timestamp 开始返回接下来 horizon_hours 的预测。"""
        ...

# 交易智能体消费任何 ForecastProvider:
class TradingAgent:
    def __init__(self, forecast_provider: ForecastProvider):
        self.forecast = forecast_provider

    def decide(self, timestamp: pd.Timestamp):
        pred = self.forecast.get_forecast(timestamp, horizon_hours=24)
        # 使用 pred 做交易决策...

# 现在你可以替换:
# - NaiveForecastProvider (基线)
# - XGBoostForecastProvider
# - PerfectForesightProvider (作弊 — 建立上界)
# - OpenSTEFForecastProvider
# - DelayedForecastProvider (仿真 1 小时数据延迟以增加现实性)
```

**应解决阶段:** 阶段 3 (AGENT-01) — 设计接口, 阶段 4 (INTG-01) — 正式化。

---

## 技术债模式

看似合理但产生长期问题的捷径。

| 捷径 | 即时收益 | 长期成本 | 何时可接受 |
|----------|-------------------|----------------|-----------------|
| 在代码中硬编码市场参数 (价格上限, 爬坡率) | 编写快 | 切换市场时必须改代码 (例如 PJM→EPEX) | 仅在探索性 notebooks 中 |
| 在模型代码中直接使用 `pd.read_csv()` | 无抽象开销 | 不能交换数据源 (PUDL → IEA → live API) | 仅阶段 1 |
| 将预测存储为 CSV 文件 | 简单, 人类可读 | 格式漂移时管道断裂; 无版本控制 | 仅阶段 1 发现 |
| 在一年上训练, 同一年上测试 (随机划分) | "好" 指标 | 模型无用; 你未测试泛化 | 永不 |
| 忽略时区处理 (假设处处 UTC) | 少一样要考虑的事 | 欧洲市场数据在 CET/CEST; 美国数据在多个时区; DST 转换产生 23h 或 25h 的一天 | 对多市场永不 |
| 使用全局 `random.seed(42)` 而不控制 PyTorch seeds | 可复现-ish | ASSUME 文档: "在不同 PyTorch 版本、硬件或 CUDA 配置之间不保证完全可复现的结果。" 固定 seeds 降低 RL 性能。 | XGBoost 可接受; 在 ASSUME 配置中使用 `seed: null` 用于 RL |
| 在单一 episode 类型上训练 RL | 快速迭代 | Agent 过拟合到该场景; 在市场制度变化时失败 | 仅首次 RL 实验 |

## 集成陷阱

连接组件时的常见错误。

| 集成 | 常见错误 | 正确方法 |
|-------------|----------------|------------------|
| PUDL → Forecast Model | 使用原始 PUDL 表而不理解 EIA 数据模型 (发电机 ID, 燃料类型, 时区处理) | 阅读 PUDL 文档; 使用 PUDL 的内置数据验证; 预期 6-12 个月数据延迟 |
| Forecast → ASSUME | 预测格式不匹配: ASSUME 期望特定的列名和带时区的 DatetimeIndex | 使用 ASSUME 的 `forecast_df.csv` 格式; 验证列名匹配 `forecast_algorithms` config |
| ASSUME → Grafana | 期望长时间仿真期间的实时仪表板更新 | ASSUME 写入 TimescaleDB; Grafana 按可配置间隔刷新; 使用 TensorBoard 查看 RL 训练进度 (实时) |
| OpenSTEF pipeline | 安装时不阅读仅 CPU 的 XGBoost 备注 | `pip install openstef[cpu]` 在 x86_64 Linux; 完整 XGBoost 在 macOS Apple Silicon 需要特殊设置 (brew libomp) |
| Multiple learning agents | 每个时间步过多的梯度步进 | ASSUME 文档: "对于有许多智能体的环境，不应使用太多梯度步进，因为其他智能体的策略也被更新，使当前最佳策略过时" |
| RL across episodes | Buffer/update 顺序 bug (在 v0.6.1 修复) | 更新到最新 ASSUME; 如果卡在旧版本, 验证 buffer 写入发生在策略更新之前 |

## 性能陷阱

在小规模时工作但在规模增长时失败的模式。

| 陷阱 | 症状 | 预防 | 何时出问题 |
|------|----------|------------|----------------|
| 在 CPU 上使用许多 RL agents 运行 ASSUME simulation | 训练时间超线性增加 | 如果可用则使用 CUDA; 限制并发学习智能体; 使用 v0.5.1+ (2x-5x speedup) | >4 learning agents |
| 每次市场出清进行完整的 PyPSA network optimization | 年度场景仿真缓慢 | ASSUME v0.6.0+: 求解器实例在出清间复用 (重大优化) | >1 month simulation horizon |
| 在仿真热循环中使用 Pandas `.loc[]` | 仿真比必要慢 10x | ASSUME v0.5.0+ 使用自定义 FastIndex/FastSeries (2-3x speedup)。自定义代码: 在核心循环中使用 numpy arrays。 | >100 units |
| 在内存中存储所有 RL replay buffer data | 多智能体、年度训练 OOM | `replay_buffer_size: 500000` 是默认值; 对内存受限设置减少 | >5 agents, >1 year horizon |
| `batch_size: 128` 配合许多 learning agents | GPU memory exhaustion | ASSUME 文档: "在有多个学习智能体的环境中，我们建议小的 batch sizes" | >8 agents on consumer GPU |

## "看起来做完但还没" 检查清单

看起来完成但缺少关键部分的事情。

- [ ] **负荷预测模型:** 经常缺少在样本外期间的 backtest — 验证时序划分, 非随机划分
- [ ] **电价预测模型:** 经常仅用 RMSE 评估 — 验证 spike recall, PnL 影响, 和统计显著性 (Diebold-Mariano test)
- [ ] **市场仿真:** 经常运行而不验证相对于历史价格 — 验证仿真价格与同期真实市场数据相关 (日前均价 r > 0.6)
- [ ] **RL trading agent:** 经常仅凭奖励曲线判断 — 验证行为 (投标曲线, 接受率, PnL vs naive baseline)
- [ ] **数据管道:** 经常假设数据是干净的 — 验证处理: 缺失时间戳, DST 转换 (23h 和 25h 天), 时区无意识 vs 有意识 datetimes
- [ ] **端到端集成:** 经常每个组件单独工作 — 验证一次完整运行: Data → Forecast → Simulation → Agent Decision → PnL Calculation
- [ ] **ASSUME configuration:** 经常从示例复制而不修改 — 验证 `forecast_algorithms` 匹配你的数据, `learning_config` 为你的场景调优, `train_freq` 根据仿真长度调整 (ASSUME 文档: "如果仿真长度不是 train_freq 的倍数, train_freq 会动态调整")

## 恢复策略

尽管预防但陷阱仍然出现时如何恢复。

| 陷阱 | 恢复成本 | 恢复步骤 |
|---------|---------------|----------------|
| Look-ahead bias (陷阱 1) | HIGH | 1. 审计所有预处理的时间泄露 2. 使用 TimeSeriesSplit 重新划分数据 3. 仅在训练期间上重新拟合所有 scalers 4. 重新训练所有模型 5. 丢弃所有之前的评估结果 |
| Wrong metrics (陷阱 2) | MEDIUM | 1. 将尖峰特定指标添加到评估中 2. 用新指标重新评估现有模型 3. "看起来不错" 的模型现在可能看起来很糟糕 — 那是正确的 4. 如果模型架构无法捕获尖峰则重新训练 |
| RL reward collapse (陷阱 3) | HIGH | 1. 回退到已知良好的基线 (朴素/启发式策略) 2. 分别检查奖励组件 (利润, 成本, 后悔) 3. 简化奖励: 从纯利润开始, 逐步添加惩罚 4. 减少学习智能体数量 (更容易的环境) 5. 遵循 ASSUME 文档: "early stopping with a very large number of episodes" |
| No end-to-end (陷阱 5) | MEDIUM | 1. 立即停止模型优化 2. 用当前 (即使不好) 的模型构建最小集成 3. 运行完整循环, 测量端到端 PnL 4. 现在用集成反馈优化各个部分 |
| Unrealistic market (陷阱 4) | MEDIUM | 1. 一次添加一个现实特征 (阻塞, 然后双重市场, 然后辅助服务) 2. 每次添加后重新测试策略 3. 在简化环境下存活但在现实中失败的策略 — 重新设计 |
| Pipeline coupling (陷阱 10) | LOW | 1. 定义 ForecastProvider 接口 2. 将现有模型包装在接口中 3. 根据需要交换实现 |

## 陷阱到阶段映射

路线图各阶段应如何处理这些陷阱。

| 陷阱 | 预防阶段 | 验证 |
|---------|------------------|--------------|
| Look-ahead bias (P1) | 阶段 1 (PRED-01) | 训练脚本中的 TimeSeriesSplit; scaler 仅在训练集上拟合 |
| 尖峰作为信号 (P2) | 阶段 1 (PRED-01) | Spike MAE + sMAPE 在评估中; 无 outlier clipping |
| RL reward design (P3) | 阶段 3 (AGENT-01/02) | 行为图 (不仅仅是奖励); PnL vs naive baseline |
| Unrealistic market (P4) | 阶段 2 (SIM-01) | 价格与真实数据相关 (r > 0.6); 出现负价格 |
| No end-to-end (P5) | 阶段 1 (总体) | 在第 1 周用朴素模型运行完整管道 |
| Dual settlement (P6) | 阶段 2 (SIM-01) | 模型包含日内/平衡市场概念 |
| Feature leakage (P7) | 阶段 1 (PRED-01) | 交叉验证 fold 内的特征选择 |
| Survivorship bias (P8) | 阶段 3 (AGENT-02) | 回测包含危机期 (2022, 2021) |
| Merit order ignorance (P9) | 阶段 2 (SIM-01) | Grafana 中排序法图显示现实台阶 |
| Pipeline coupling (P10) | 阶段 3 (AGENT-01) | 预测接口可交换; 完美预见测试工作 |
| XGBoost 无时间意识 | 阶段 1 (PRED-01) | 仅有滞后特征; 无未来泄露特征 |
| ASSUME config 误用 | 阶段 2 (SIM-01) | 先运行 example_01a; 增量修改 |

## ASSUME 特定陷阱 (来自官方文档和发布说明)

这些直接来自 ASSUME 框架自己的文档和 bug 修复历史:

1. **Seed 设置:** ASSUME 文档: "我们建议在使用学习时不要在通用配置中设置 seed (`seed=null`), 因为它会降低性能。" 确定性模式损害 RL 训练。

2. **输出限幅 bug (在 v0.5.5 修复):** "action clamping 被更改... 之前, 输出范围仅根据输入错误假设, 当 Xavier initialization 使权重为负时失败。" 教训: 验证智能体动作范围确实被尊重。

3. **Buffer/update ordering (在 v0.6.1 修复):** "修复了 buffer 写入和策略更新的顺序... 这个 bug 会在非常异构的机组上 compromise 学习。" 教训: 在多智能体 RL 中, 操作顺序至关重要。

4. **train_freq 不匹配:** "修复了一个 bug, 如果仿真长度不是 train_freq 的倍数, 剩余仿真步骤不被用于训练。" 现在 ASSUME 自动调整。教训: 验证你的时间对齐。

5. **投标洗牌偏差 (在 v0.4.0 修复):** "改进了带投标洗牌的出清, 以避免对 order book 中较早机组的出清偏差。" 教训: 市场出清中的排序效应可能偏差结果。

6. **Continue learning 限制:** "当加载的 critic 和新的 critic 之间隐藏层数量不同时, 此过程将失败。" 教训: 在开始多阶段训练前规划你的智能体架构。

7. **PyTorch 可复现性警告:** "在不同 PyTorch 版本、硬件或 CUDA 配置之间不保证完全可复现的结果。" 教训: 不要期望 RL 实验中逐位完全可复现。

8. **Complex clearing paradoxically accepted bids:** 复杂出清算法迭代解决 paradoxically accepted bids (PABs) —— 以低于其投标价格被接受的投标。教训: 出清算法有边界情况; 验证你的出清结果。

9. **DMAS bidding strategies 是可选的:** Pyomo 不是必需的依赖; 基于优化的策略需要它。教训: 在使用高级策略前检查依赖。

## 来源

- **ASSUME Official Documentation** — https://assume.readthedocs.io/en/latest/
  - [Bidding Strategies](https://assume.readthedocs.io/en/latest/bidding_strategies.html) — 策略类型, naive/heuristic/learning/optimization
  - [Market Mechanisms](https://assume.readthedocs.io/en/latest/market_mechanism.html) — Pay-as-clear, pay-as-bid, complex clearing, nodal, redispatch
  - [Reinforcement Learning](https://assume.readthedocs.io/en/latest/learning.html) — Multi-agent MATD3, centralized critic, reward interpretation warnings
  - [RL Algorithms](https://assume.readthedocs.io/en/latest/learning_algorithm.html) — TD3, buffer design, config parameters
  - [Unit Forecasts](https://assume.readthedocs.io/en/latest/unit_forecasts.html) — Forecast lifecycle, algorithm resolution, registries
  - [Release Notes](https://assume.readthedocs.io/en/latest/release_notes.html) — Bug fixes and lessons learned across v0.1.0–v0.6.1
- **ASSUME JOSS Paper** — Harder et al. (2025), "ASSUME: An agent-based simulation framework for exploring electricity market dynamics with reinforcement learning," *SoftwareX*, Vol. 30, Article 102176.
- **ASSUME Energy and AI Paper** — Harder, Qussous & Weidlich (2023), "Fit for purpose: Modeling wholesale electricity markets realistically with multi-agent deep reinforcement learning," *Energy and AI*, Vol. 14, 100295.
- **epftoolbox** — Lago et al. (2021), "Forecasting day-ahead electricity prices: A review of state-of-the-art algorithms, best practices and an open-access benchmark," *Applied Energy*, Vol. 293, 116983. https://github.com/jeslago/epftoolbox
- **OpenSTEF GitHub** — https://github.com/OpenSTEF/openstef — Automated ML pipeline for short-term energy forecasting, LF Energy project
- **PUDL** — https://github.com/catalyst-cooperative/pudl — Public Utility Data Liberation, cleaned US EIA power data

---

*陷阱调研: AI驱动的电力交易学习平台*
*调研日期: 2026-05-20*
*置信度: HIGH — 基于官方框架文档和已发表研究*
