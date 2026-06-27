"""
Ellectric 全流程演示 — 从数据加载到 RL 交易 + SHAP 解释
=====================================================
数据源: epftoolbox PJM 市场 (6年小时级负荷+电价)
"""
import sys, os, time, json, warnings, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

import numpy as np
import pandas as pd
from ellectric.config import TimeConfig
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 120)

REPORT = []

def step(n, msg):
    print(f"\n{'='*70}")
    print(f"  Step {n}: {msg}")
    print(f"{'='*70}")
    sys.stdout.flush()
    REPORT.append(f"## {n}. {msg}")
    return time.time()

def ok(msg, val=None):
    tag = f"✅ {msg}"
    if val is not None:
        tag += f" — {val}"
    print(f"  {tag}")
    REPORT.append(f"- {tag}")
    sys.stdout.flush()

def warn(msg):
    tag = f"⚠️  {msg}"
    print(f"  {tag}")
    REPORT.append(f"- {tag}")

# ════════════════════════════════════════════════════════════
# Wave 1: 数据加载与准备
# ════════════════════════════════════════════════════════════
t0 = step(1, "数据加载 — epftoolbox PJM 市场")

df = pd.read_csv('ellectric/data/epft_PJM.csv')
df = df.rename(columns={
    'Date': 'timestamp',
    ' Zonal COMED price': 'price_da',
    ' System load forecast': 'load_mw'
})
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

n_total = len(df)
date_range = f"{df['timestamp'].min()} ~ {df['timestamp'].max()}"
ok(f"PJM 数据: {n_total:,} 行", date_range)
ok(f"列: {list(df.columns)}")
ok(f"负荷范围: {df['load_mw'].min():.0f} ~ {df['load_mw'].max():.0f} MW")
ok(f"电价范围: {df['price_da'].min():.2f} ~ {df['price_da'].max():.2f} 元/MWh")

# 分割训练/测试 (前80%训练, 后20%测试)
split = int(n_total * 0.8)
df_train = df.iloc[:split].copy()
df_test  = df.iloc[split:].copy()
ok(f"训练集: {len(df_train):,} 行", f"测试集: {len(df_test):,} 行")

# 保存测试数据到文件用于之后的 notebook
df_test.to_parquet('ellectric/data/demo_test_data.parquet')

# ════════════════════════════════════════════════════════════
# Wave 2: 双模型训练
# ════════════════════════════════════════════════════════════
t0 = step(2, "模型训练 — XGBoost 负荷预测 + LEAR 电价预测")

from ellectric.pipeline.forecaster import XGBoostForecaster
from ellectric.pipeline.features import FeatureEngineer
from ellectric.pipeline.price_forecaster import LEARForecaster

# ── XGBoost 负荷预测 ──────────────────────────────
fe = FeatureEngineer()
df_feat = fe.add_tier1_features(df_train)
feat_cols = fe.get_feature_columns('tier1')

xgb = XGBoostForecaster(n_estimators=200, max_depth=6)
t1 = time.time()
xgb_res = xgb.train_evaluate(
    df_feat[feat_cols].dropna(),
    df_train['load_mw'].loc[df_feat[feat_cols].dropna().index],
    n_splits=3, gap=TimeConfig.points_per_day
)
xgb.save_model('ellectric/data/demo_xgb.joblib')
ok(f"XGBoost 负荷预测 — MAE={xgb_res['metrics']['mae']:.0f} MW", f"训练耗时 {time.time()-t1:.1f}s")

# ── LEAR 电价预测 ────────────────────────────────
pf = LEARForecaster(alpha=0.05)
pdf = pf.add_price_features(df_train, 'tier1')
t1 = time.time()
pf_res = pf.train_evaluate(pdf, 'tier1', n_splits=3, gap=TimeConfig.points_per_day)
pf.save_model('ellectric/data/demo_lear.joblib')
ok(f"LEAR 电价预测 — MAE={pf_res['metrics']['mae']:.2f} 元/MWh", f"训练耗时 {time.time()-t1:.1f}s")

# 加载模型（模拟 notebook 中的加载流程）
xgb2 = XGBoostForecaster()
xgb2.load_model('ellectric/data/demo_xgb.joblib')
pf2 = LEARForecaster()
pf2.load_model('ellectric/data/demo_lear.joblib')

# 验证 predict() 一致性
pred_check = xgb2.predict(df_feat[feat_cols].iloc[-100:])
ok(f"XGBoost predict() 验证 — 输出 {len(pred_check)} 个预测值")

# ════════════════════════════════════════════════════════════
# Wave 3: RL 交易智能体训练
# ════════════════════════════════════════════════════════════
t0 = step(3, "RL 交易智能体 — PPO 训练")

from ellectric.pipeline.trading_env import ElectricityMarketEnv, RewardRegistry
from ellectric.pipeline.rl_trainer import RLAgentFactory

# 用测试数据创建环境
load_data = df[['timestamp', 'load_mw']].copy()
price_data = df[['timestamp', 'price_da']].copy()
max_cap = float(df['load_mw'].max())

env = ElectricityMarketEnv(
    load_data, price_data,
    load_forecaster=xgb2,
    price_forecaster=pf2,
    max_capacity=max_cap,
    reward_fn='profit_only'
)

obs, _ = env.reset()
ok(f"环境初始化 — obs 空间 {list(obs.keys())}", f"动作空间 Box({env.action_space.shape[0]},)")

# PPO 训练 (10K steps for demo)
t1 = time.time()
agent = RLAgentFactory.create('ppo', env, verbose=0)
result = agent.train(total_timesteps=5000)
ok(f"PPO 训练完成 — total_timesteps={result['total_timesteps']}", f"训练耗时 {time.time()-t1:.1f}s")

# 评估
ev = agent.evaluate(env, n_episodes=5)
ok(f"PPO 评估 — mean_reward={ev['mean_reward']:.0f}", f"std_reward={ev['std_reward']:.0f}")

agent.save('ellectric/data/demo_ppo.zip')
ok("PPO 模型已保存")

# ════════════════════════════════════════════════════════════
# Wave 4: 回测对比
# ════════════════════════════════════════════════════════════
t0 = step(4, "历史回测 — oracle vs RL vs baseline")

from ellectric.pipeline.backtester import BacktestRunner

# 用 7 天测试数据做回测 (前 168 小时)
test_ldf = df_test[['timestamp', 'load_mw']].iloc[:336].copy()
test_pdf = df_test[['timestamp', 'price_da']].iloc[:336].copy()

ef = lambda: ElectricityMarketEnv(
    test_ldf, test_pdf,
    load_forecaster=xgb2, price_forecaster=pf2,
    max_capacity=max_cap, reward_fn='profit_only'
)
runner = BacktestRunner(ef)

t1 = time.time()
results = {}
results['oracle'] = runner.replay('oracle', test_ldf, test_pdf,
    start='2017-10-20', end='2017-10-25', strategy_name='oracle')
results['rl_ppo'] = runner.replay(agent, test_ldf, test_pdf,
    start='2017-10-20', end='2017-10-25', strategy_name='rl_ppo')
results['baseline'] = runner.replay('baseline_persistence', test_ldf, test_pdf,
    start='2017-10-20', end='2017-10-25', strategy_name='baseline')
bt = time.time() - t1

comparison = runner.compare(results)
print(f"\n  回测耗时 {bt:.1f}s")
print(f"\n  📊 策略对比:")
for _, row in comparison.iterrows():
    print(f"    {row['策略']:20s}  总收益={row['总收益']:>10.2f}  夏普={row['夏普比率']:>8.2f}  胜率={row['胜率']:.0%}")

# 生成回测图
fig = BacktestRunner.plot_comparison(results, title="Phase 3 回测 — 策略对比 (PJM 市场)")
fig.write_html('ellectric/data/demo_backtest.html',
    include_plotlyjs='cdn',
    config={'responsive': True, 'displaylogo': False})
ok("回测完成 — 结果已保存到 demo_backtest.html")

# ════════════════════════════════════════════════════════════
# Wave 5: SHAP 可解释性
# ════════════════════════════════════════════════════════════
t0 = step(5, "SHAP 可解释性 — 瀑布图 + 特征排名")

from ellectric.pipeline.shap_explainer import (
    explain_xgboost_sample, explain_lear_sample, feature_importance_ranking
)

# XGBoost SHAP
fig_xgb = explain_xgboost_sample(xgb2, df_feat[feat_cols].iloc[:200], sample_idx=0)
fig_xgb.write_html('ellectric/data/demo_shap_xgb.html',
    include_plotlyjs='cdn',
    config={'responsive': True, 'displaylogo': False})
ok("XGBoost SHAP 瀑布图已保存")

# LEAR SHAP
lear_features = pf2.get_feature_columns('tier1')
fig_lear = explain_lear_sample(pf2, pdf[lear_features].iloc[:200], sample_idx=0)
fig_lear.write_html('ellectric/data/demo_shap_lear.html',
    include_plotlyjs='cdn',
    config={'responsive': True, 'displaylogo': False})
ok("LEAR SHAP 瀑布图已保存")

# 特征排名
ranking = feature_importance_ranking(
    {"XGBoost": xgb2, "LEAR": pf2},
    list(set(feat_cols + lear_features))
)
print(f"\n  📊 特征重要性排名 (Top 10):")
for _, row in ranking.head(10).iterrows():
    print(f"    {row['model']:10s} | {row['feature']:25s} | 重要性={row['importance']:.4f}")
ok("特征排名完成")

# ════════════════════════════════════════════════════════════
# Wave 6: 报告汇总
# ════════════════════════════════════════════════════════════
t0 = step(6, "报告汇总")

BUILD_NOTE = f"""
# Ellectric 全流程运行报告

## 概要

| 指标 | 值 |
|------|-----|
| 数据源 | PJM 电力市场 ({date_range}) |
| 数据量 | {n_total:,} 行小时级数据 |
| 训练/测试 | {len(df_train):,} / {len(df_test):,} 行 |
| XGBoost MAE | {xgb_res['metrics']['mae']:.0f} MW |
| LEAR MAE | {pf_res['metrics']['mae']:.2f} 元/MWh |
| PPO 训练步数 | {result['total_timesteps']:,} |
| PPO 评估奖励 | {ev['mean_reward']:.0f} ± {ev['std_reward']:.0f} |

## 回测结果

```
{comparison.to_string()}
```

## 生成文件

| 文件 | 说明 |
|------|------|
| `data/demo_xgb.joblib` | 训练好的 XGBoost 负荷预测模型 |
| `data/demo_lear.joblib` | 训练好的 LEAR 电价预测模型 |
| `data/demo_ppo.zip` | 训练好的 PPO 交易智能体 |
| `data/demo_backtest.html` | 回测对比交互图 (plotly) |
| `data/demo_shap_xgb.html` | XGBoost SHAP 瀑布图 |
| `data/demo_shap_lear.html` | LEAR SHAP 瀑布图 |
| `data/demo_test_data.parquet` | 测试数据 (notebook 使用) |

## Notebook 学习路径

| Notebook | 内容 | 当前状态 |
|----------|------|----------|
| 01-05 | Phase 1: 数据加载 → 负荷预测 → 基线 | 需要 OWID 年数据 (非小时级) |
| 06_price_forecasting | Phase 2: LEAR 电价预测 | 需要中国电价数据 |
| 09_rl_trading_agent | Phase 3: RL 环境走查 + PPO 训练 | 参考本脚本 |
| 10_multi_agent_backtest | Phase 3: 三算法对比 + 回测 | 参考本脚本 |
| 11_model_explainability | Phase 3: SHAP 解释 | 参考本脚本 |

## 指标词汇表 (Glossary)

| 指标 | 英文 | 含义 | 解读 |
|------|------|------|------|
| MAE | Mean Absolute Error | 平均绝对误差 | 预测值与真实值差距的平均绝对值。越小越好 |
| RMSE | Root Mean Squared Error | 均方根误差 | 对大误差惩罚更重。RMSE > MAE 说明有异常大误差 |
| P&L | Profit & Loss | 盈亏 | 模拟交易的累计盈利/亏损。正=赚,负=亏 |
| 总收益 | Total Return | 回测期间总盈亏 | oracle≈0 说明完美投标无偏差，RL 和 baseline 为负说明偏离实际负荷 |
| 夏普比率 | Sharpe Ratio | 风险调整后收益 | =(平均收益-无风险利率)/波动率。越大越好(>1良,>2优) |
| 胜率 | Win Rate | 盈利小时占比 | 盈利小时数/总小时数。越高越好 |
| 最大回撤 | Max Drawdown | 从峰值到谷值最大跌幅 | 策略历史最高点以来的最大亏损幅度。越小越好 |
"""

with open('ellectric/data/RUN_REPORT.md', 'w') as f:
    f.write(BUILD_NOTE)

ok("运行报告已保存到 data/RUN_REPORT.md")
print(f"\n{'='*70}")
print(f"  🎉 全流程演示完成！")
print(f"{'='*70}")
print(f"\n  报告: ellectric/data/RUN_REPORT.md")
print(f"  回测图: ellectric/data/demo_backtest.html (在浏览器中打开)")
print(f"  SHAP图: ellectric/data/demo_shap_xgb.html")
print(f"  模型: demo_xgb.joblib / demo_lear.joblib / demo_ppo.zip")
print(f"{'='*70}")
