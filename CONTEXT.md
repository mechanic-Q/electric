# Context

## Project Domain

Electric is a hands-on AI + electricity trading learning platform. It is a learning prototype, not production trading software.

Core flow:

```text
public electricity data -> forecasting -> market simulation -> strategy/backtest -> explanatory WebUI
```

The current deployment discussion is scoped to the explanatory WebUI only.

## Glossary

### Showcase WebUI

The public website version of Electric. It is a presentation surface that autoplays precomputed Shandong electricity-market data and explains the project. It is not expected to run heavy algorithms live on the server.

Use this term instead of "production app" or "live trading system" for the current deployment.

### Rolling Demo

The pre-baked dashboard payload that drives the WebUI animation. It contains timestamps, load, price, renewable output, strategy ranking, and report summaries.

In showcase deployment it is served as static JSON, not generated on every page load.

### Showcase Explainer

The DeepSeek-backed Copilot role in the public site. It answers plain-language questions about the dashboard, project concepts, algorithms, datasets, and offline reports.

It may read lightweight report/dataset/capability metadata. It must not run live forecasts, market simulations, backtests, or strategy recommendations in showcase mode.

### Offline Report

Generated evidence already stored under `ellectric/reports/`. Reports are safe for showcase Copilot to reference because they do not require recomputation.

### Live Algorithm Execution

Any server-side operation that loads models, runs ASSUME, runs RL backtests, computes live recommendations, or performs realtime prediction. This is out of scope for the public showcase deployment.

### Hong Kong Showcase Server

The recommended hosting environment for the public demo: small Hong Kong VPS, Ubuntu LTS, FastAPI/uvicorn, static frontend, pre-baked JSON, and DeepSeek API key. Hong Kong avoids mainland ICP filing while keeping acceptable mainland access latency.

## Current Deployment Boundary

The public site should do these things:

- Load the WebUI.
- Autoplay the rolling demo.
- Keep Copilot chat available.
- Let Copilot explain concepts in beginner-friendly Chinese.
- Let Copilot query offline reports, datasets, and capability metadata.

The public site should not do these things:

- Run XGBoost/LEAR prediction live.
- Run ASSUME market simulation.
- Run RL backtesting.
- Run trading recommendations.
- Require model artifacts, GPU, ASSUME, PyTorch-heavy dependencies, or paid realtime data.

## Relevant Documents

- `docs/showcase-webui-deployment-plan.md` — operational plan for the showcase deployment.
- `docs/adr/0001-showcase-webui-hk-deployment.md` — decision record for the showcase architecture.
- `.planning/ROADMAP.md` — historical roadmap and project scope.
