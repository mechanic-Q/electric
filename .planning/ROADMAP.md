# Roadmap: Ellectric (AI + 电力交易技术学习平台)

## Overview

A hands-on learning journey through AI-driven electricity trading — from pulling public energy data to training reinforcement learning agents that compete in realistic market simulations. Each phase delivers a complete, verifiable learning outcome: Phase 1 proves the pipeline works with simple tools, Phase 2 introduces domain-specific frameworks (OpenSTEF, ASSUME), Phase 3 adds RL trading strategies and backtesting, and Phase 4 wraps everything in CLI, API, and natural language interfaces. Every phase builds on the previous; none can be skipped or reordered.

## Phases

- [x] **Phase 1: Data Foundation + Basic Prediction** — Working Jupyter environment, PUDL data pipeline, XGBoost load forecasting, end-to-end baseline run
- [ ] **Phase 2: 中国电力市场预测与仿真** — sklearn LEAR 电价预测 + epftoolbox 基准对比 + ASSUME 中国省间现货仿真 + Grafana 仪表板
- [ ] **Phase 3: Trading Agents + Backtesting** — RL agent training with custom reward functions, historical backtesting on stress periods, SHAP model explainability
- [ ] **Phase 4: Integration + LLM Interface** — FastAPI REST API, CLI toolchain, LangChain + Ollama natural language trading assistant

## Phase Details

### Phase 1: Data Foundation + Basic Prediction

**Goal:** Learners can install the environment in one command, pull public energy data, run an XGBoost load forecast with proper temporal splitting, and execute an end-to-end pipeline run (naive forecast → simulation → P&L) — proving all layers connect before adding sophistication.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** ENV-01, ENV-02, ENV-03, DATA-01, DATA-02, DATA-03, DATA-04, PRED-01, VIZ-01
**Success Criteria** (what must be TRUE):

  1. Learner runs a single install script and opens a Jupyter notebook with all core dependencies (pandas, scikit-learn, XGBoost, enda, matplotlib) importable — within 30 minutes on a clean Python 3.11 machine
  2. Learner executes the data ingestion notebook: downloads PUDL data, runs the cleaning pipeline (missing value imputation, IQR outlier detection, UTC timezone normalization), and outputs validated `cleaned_load.parquet` with documented column schemas
  3. Learner executes the feature engineering notebook: generates calendar features (hour, day-of-week, holiday flags), lag features (t-24h, t-168h), and rolling window statistics — with all scalers fit ONLY on training data (TimeSeriesSplit, no look-ahead bias)
  4. Learner executes the load forecasting notebook: trains an XGBoost model, views MAE/RMSE/MAPE on a proper temporal test split, and sees load-vs-prediction overlay plots and error distribution histograms in the notebook output
  5. Learner executes the end-to-end baseline notebook: runs a naive persistence forecast through a minimal simulation, calculates P&L, and sees a cumulative profit chart — proving all five pipeline layers exist and connect

**Plans:** 3 plans

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Walking Skeleton: project scaffold (setup.sh, requirements.txt), OWID China data auto-fetch via OWIDChinaLoader, data cleaning (missing fill, IQR report-only, UTC timezone), persistence forecast + P&L chart (Notebooks 01 + 05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — XGBoost load forecasting with TimeSeriesSplit(n_splits=5, gap=24), progressive feature engineering (Tiers 1-3 via FeatureEngineer), scaler fit-on-train-only enforcement, plotly visualizations (actual-vs-predicted overlay + error histogram), DataLoader full implementation (ChineseDataLoader + data versioning), Notebooks 02/03/04

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Docker Compose skeleton (commented-out TimescaleDB+Grafana for Phase 2), README data dictionary + project structure, Chinese data acquisition guide (docs/chinese-electricity-data-guide.md), notebook polish (思考题 reflection questions, error handling, learning objectives)

### Phase 2: Deep Prediction + Market Simulation

**Goal:** 基于中国电价数据（ZionLuo/price data.xlsx），使用 sklearn Lasso 实现 LEAR 日前电价预测；用 epftoolbox 5 个基准数据集 + DM/GW 统计检验验证方法正确性；配置 ASSUME 中国省间现货仿真环境；通过 Grafana 可视化市场出清结果。
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** DATA-05, PRED-02, PRED-03, PRED-04, SIM-01, SIM-02, SIM-03, SIM-04
**Success Criteria** (what must be TRUE):

  1. Learner runs OpenSTEF automated forecasting pipeline and sees a side-by-side comparison table: manual XGBoost (Phase 1) vs OpenSTEF — MAE — with model win summary
  2. Learner trains sklearn Lasso-based LEAR model on Chinese day-ahead price data, achieving MAE comparable to epftoolbox LEAR baseline; DM/GW test confirms statistical validity
  3. Learner opens an interactive plotly dashboard showing multi-model comparison: error-by-hour heatmaps, forecast overlay for the past week, and model ranking by metric
  4. Learner launches a 7-day ASSUME simulation using Chinese provincial market rules, then opens Grafana to view clearing prices per hour, dispatch per unit, and cumulative profit per agent
  5. Learner modifies the generation mix YAML (e.g., increasing wind to 30%, removing coal), re-runs the simulation, and observes how clearing prices change under Chinese market constraints

**Plans:** TBD
**UI hint:** yes

### Phase 3: Trading Agents + Backtesting

**Goal:** Learners connect prediction outputs to trading strategies, train RL agents (PPO/TD3/SAC) with custom reward functions, run historical backtests on stress periods, and evaluate strategy performance through P&L and explainability tools.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** AGENT-01, AGENT-02, AGENT-03, AGENT-04, VIZ-02
**Success Criteria** (what must be TRUE):

  1. Learner connects Phase 1/2 forecast output to an ASSUME agent's bidding strategy and observes the agent submitting price-sensitive bids (not just marginal cost) in Grafana bid curve visualization
  2. Learner modifies the RL agent's reward function (e.g., profit-only → risk-adjusted with penalty for zero-volume hours) and observes different emergent bidding behavior in TensorBoard — verified by bid curve shape, not just reward magnitude
  3. Learner runs an end-to-end historical backtest on a stress period (e.g., August 2022 energy crisis), views a cumulative P&L chart comparing RL agent vs rule-based baseline vs oracle strategy, and sees which strategy produces the highest risk-adjusted return
  4. Learner opens TensorBoard and sees training curves: episode reward, acceptance rate, and profit distribution — with the RL agent's behavior metrics improving over episodes relative to the naive baseline
  5. Learner generates SHAP waterfall plots explaining why XGBoost predicted a specific load value for a given hour, and views feature importance rankings across all trained models

**Plans:** TBD
**UI hint:** yes

### Phase 4: Integration + LLM Interface

**Goal:** Learners access all platform capabilities through CLI commands, REST API endpoints, and a natural language trading assistant powered by a local LLM (Qwen2.5-7B via Ollama).
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** INTG-01, INTG-02, INTG-03
**Success Criteria** (what must be TRUE):

  1. Learner starts the FastAPI server and calls `GET /predict?horizon=24h`, receiving a JSON forecast response with timestamped load predictions and confidence intervals from their trained model
  2. Learner runs `ellectric simulate start --scenario summer_peak` from the CLI and receives clearing prices, dispatch summary, and per-agent profit in terminal output
  3. Learner runs `ellectric backtest run --start 2022-08-01 --end 2022-08-31` and receives cumulative P&L, Sharpe ratio, and strategy comparison in tabular CLI output
  4. Learner asks the LLM trading assistant "What was the peak load forecast for yesterday?" and receives a response with actual forecast data queried live from the prediction service via LangChain tool-calling
  5. Learner issues a natural language trading command: "Bid 50MW at $35/MWh for hours 8-16 tomorrow" — the assistant parses it into a structured bid configuration, confirms the parameters, and stores the configuration for the next simulation

**Plans:** TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation + Basic Prediction | 3/3 | Shipped | 2026-06-06 |
| 2. 中国电力市场预测与仿真 | 0/TBD | Planned | - |
| 3. Trading Agents + Backtesting | 0/TBD | Not started | - |
| 4. Integration + LLM Interface | 0/TBD | Not started | - |
