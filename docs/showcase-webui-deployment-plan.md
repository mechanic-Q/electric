# Showcase WebUI Deployment Plan

## Goal

Deploy Electric as a public showcase website on a Hong Kong cloud server.

This deployment is for demonstration only. It should show the WebUI, autoplay pre-baked data, and let DeepSeek explain dashboard concepts in plain language. It should not run heavy prediction, simulation, RL training, or live trading workflows on the server.

## Agreed Scope

### In Scope

- Serve the current WebUI as a public website.
- Autoplay the rolling dashboard using pre-baked Shandong demo data.
- Keep the Copilot panel.
- Use DeepSeek as a plain-language explainer for the page, terms, algorithms, and reports.
- Keep lightweight report/dataset/capability lookup tools for Copilot.
- Deploy first by server IP, domain/HTTPS later.

### Out Of Scope

- Live model prediction on the server.
- ASSUME market simulation on the server.
- RL backtesting or strategy recommendation on the server.
- GPU, PyTorch-heavy stack, ASSUME, or model artifact deployment.
- Real trading, realtime data, or production-grade operations.

## Current WebUI Reality

The current WebUI does not directly expose most backend algorithm endpoints.

Direct frontend calls:

- `GET /dashboard/rolling-demo` in the original app, now planned as static `GET /rolling-demo.json`.
- `POST /chat/stream` for Copilot streaming responses.

Not directly used by the WebUI:

- `/predict`
- `/simulate`
- `/backtest`
- `/recommend`
- `/explain`

These heavier endpoints can remain in code, but the showcase Copilot should not call them.

## Target Architecture

```text
Browser
  -> Hong Kong cloud server, Ubuntu 22.04 LTS, 2 vCPU / 2 GB RAM
     -> uvicorn :8000, FastAPI
        -> /                    static WebUI
        -> /rolling-demo.json    pre-baked demo data
        -> /chat/stream          DeepSeek streaming chat
        -> /reports              offline report catalog
        -> /reports/{id}         offline report detail
        -> /datasets             dataset metadata
        -> /capabilities         capability metadata
```

Required server assets:

- Built frontend under `ellectric/api/static/`.
- Pre-baked JSON at `ellectric/api/static/rolling-demo.json`.
- Report files under `ellectric/reports/`.
- Shandong data files only if retained for future local regeneration.
- `DEEPSEEK_API_KEY` environment variable.

Not required:

- `.joblib` model files.
- ASSUME.
- GPU.
- Docker.
- nginx/Caddy for first IP-only launch.

## Copilot Behavior

Copilot role: showcase explainer.

Tone: plain-language, beginner-friendly Chinese explanations.

Allowed capabilities:

- Explain dashboard sections.
- Explain terms such as XGBoost, LEAR, PPO, SAC, TD3, SHAP, load forecasting, price forecasting, and electricity trading concepts.
- Query offline report catalog.
- Read offline report details.
- Explain dataset and capability metadata.

Disabled capabilities:

- Running live forecast.
- Running simulation.
- Running backtest.
- Generating live strategy recommendation.

When a user asks for disabled live execution, Copilot should explain that this is a showcase deployment and point to the precomputed reports/data shown on the page.

## Prepared Local Changes

These changes have already been prepared in the working tree and should be kept if this plan proceeds:

- `ellectric/scripts/prebake_demo.py` generates pre-baked rolling demo JSON.
- `ellectric/web/public/rolling-demo.json` stores the pre-baked data source.
- `ellectric/web/src/api.ts` reads `/rolling-demo.json` instead of `/dashboard/rolling-demo`.
- `ellectric/llm/agent.py` changes Copilot into a showcase explainer and removes heavy tool calls.
- `ellectric/web/src/App.tsx` updates Copilot welcome text and API contract copy.
- `ellectric/api/static/` contains the rebuilt production frontend.

## Server Recommendation

Recommended purchase:

- Provider: Alibaba Cloud Lightweight Application Server, Hong Kong region, or Tencent Cloud Lighthouse, Hong Kong region.
- OS: Ubuntu 22.04 LTS.
- Spec: 2 vCPU, 2 GB RAM, 40 GB SSD.
- Network: 3 Mbps or higher bandwidth.

Reason:

- Hong Kong avoids mainland ICP filing.
- Mainland China access is usually faster than US/EU VPS.
- DeepSeek API access should be normal.
- 2 GB RAM is enough because the server does not run heavy models.

## Deployment Phases

### Phase 1: Local Build Package

Verify locally before uploading:

```bash
cd ellectric/web
npm run build
```

Expected output:

- `ellectric/api/static/index.html`
- `ellectric/api/static/assets/*.js`
- `ellectric/api/static/assets/*.css`
- `ellectric/api/static/rolling-demo.json`

### Phase 2: Server Bootstrap

On the Hong Kong server:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Clone or upload the repo:

```bash
git clone https://github.com/mechanic-Q/electric.git
cd electric
```

Create virtualenv:

```bash
python3 -m venv .venv
. .venv/bin/activate
```

Install minimal runtime dependencies. Exact dependency file still needs final cleanup before server launch because dependency files are split across `ellectric/requirements.txt` and `ellectric/requirements-phase4.txt`.

### Phase 3: Runtime Configuration

Set DeepSeek key:

```bash
export DEEPSEEK_API_KEY='your-deepseek-api-key'
```

Optional callback URL:

```bash
export ELLECTRIC_API_URL='http://127.0.0.1:8000'
```

For single-server deployment, the default `http://localhost:8000` is acceptable.

### Phase 4: Start Service

Start FastAPI:

```bash
. .venv/bin/activate
uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://SERVER_IP:8000
```

### Phase 5: Process Guard

After manual verification passes, create a `systemd` service to keep uvicorn running after SSH disconnect or reboot.

### Phase 6: Domain And HTTPS Later

After IP launch works:

- Buy a domain if needed.
- Point DNS `A` record to Hong Kong server IP.
- Use Caddy for automatic HTTPS.
- Avoid nginx first unless there is a specific reason.

## Verification Checklist

- `http://SERVER_IP:8000` loads the dashboard.
- Rolling playback starts automatically.
- `http://SERVER_IP:8000/rolling-demo.json` returns HTTP 200 JSON.
- Copilot initial message says it can explain dashboard terms and offline reports.
- Asking `XGBoost 是什么？` returns a plain-language explanation.
- Asking `PPO 策略表现怎么样？` uses report lookup and references offline report data.
- Asking `帮我跑个实时仿真` gets a clear showcase-mode limitation message.

## Known Risks

- Dependency files need cleanup before server launch. Current project has split requirements and may include heavier dependencies than needed.
- If reverse proxy is added later, `/chat/stream` needs SSE-friendly buffering settings. Caddy is preferred because it handles streaming well by default.
- If a domain is hosted on a mainland China server, ICP filing would be required. Hong Kong avoids this.
- Do not expose DeepSeek API keys in git or frontend code. Keep keys only as server environment variables.
- The showcase site is not production trading software and should keep the learning-prototype disclaimer visible.

## Definition Of Done

The deployment is complete when a visitor can open the public IP or domain, watch the dashboard autoplay, and ask Copilot plain-language questions about the page and reports without triggering heavy model execution.
