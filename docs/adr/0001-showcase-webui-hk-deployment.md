# ADR 0001: Deploy Showcase WebUI On A Hong Kong Server

## Status

Accepted

## Context

Electric has a WebUI that presents a dashboard-first learning prototype for AI + electricity trading. The current public deployment goal is not to expose all algorithmic backend features. The goal is to make the existing WebUI available as a public website that autoplays precomputed data and uses DeepSeek to explain what visitors are seeing.

The original deployment risk scan identified heavy backend capabilities:

- live prediction endpoints
- ASSUME simulation
- RL backtesting
- strategy recommendation
- model artifacts
- local paths and server runtime assumptions

The user clarified that the public site should be a showcase, not a live algorithm service. The server is expected to be small. Hong Kong hosting is preferred to avoid mainland ICP filing and speed up launch.

## Decision

Deploy Electric as a showcase WebUI on a small Hong Kong Ubuntu server.

Use this runtime shape:

- FastAPI + uvicorn serves the built WebUI.
- The rolling dashboard reads pre-baked static JSON.
- DeepSeek remains available through the Copilot panel.
- Copilot acts as a beginner-friendly showcase explainer.
- Copilot may use lightweight report/dataset/capability lookup tools.
- Copilot must not call live forecast, simulation, backtest, or recommendation tools in showcase mode.

Use IP-based launch first. Add domain and HTTPS later after the server is reachable.

## Consequences

Positive:

- Small 2 vCPU / 2 GB RAM server is enough.
- No GPU is needed.
- No ASSUME/PyTorch-heavy runtime is needed for the public site.
- No model artifact deployment is needed for the initial showcase.
- Hong Kong hosting avoids mainland ICP filing.
- DeepSeek can still explain terms such as XGBoost, LEAR, PPO, SAC, TD3, SHAP, load forecasting, and price forecasting.

Negative:

- Visitors cannot trigger live prediction, simulation, backtest, or recommendation from the showcase site.
- Copilot must clearly explain showcase-mode limitations when asked to run heavy workflows.
- If live algorithm execution becomes a future requirement, the deployment architecture must be revisited.

## Alternatives Considered

### Full Backend Deployment

Rejected for the showcase phase. It requires model artifacts, heavier dependencies, and potentially ASSUME/PyTorch/RL runtime support. This conflicts with the small-server and fast-launch goal.

### Pure Static Site Without Copilot

Rejected because the user wants DeepSeek to explain webpage content and technical terms.

### Mainland China Server

Rejected for the first public launch because binding a domain would require ICP filing. Hong Kong is faster to launch.

### PaaS Hosting

Not chosen for the first plan. PaaS can simplify operations, but SSE streaming and file/runtime constraints are less predictable than a small VPS.

## Follow-Up Work

- Keep `docs/showcase-webui-deployment-plan.md` aligned with implementation details.
- Before server deployment, clean up minimal runtime dependencies.
- Add a process guard, such as systemd, after manual IP-based verification passes.
- Add Caddy and HTTPS only after a domain exists.
