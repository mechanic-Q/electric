# _env-detect.md — Ellectric 构建环境探测 (临时)

## 构建工具
- **语言**: Python 3.11+
- **包管理**: pip + venv
- **安装入口**: `ellectric/setup.sh` (一键安装脚本)

## 依赖分层

### 核心依赖 (requirements.txt)
- pandas 3.0.3, numpy >=2.0.0, pyarrow 22.0.0
- scikit-learn 1.8.0, xgboost 3.2.0
- gymnasium 1.2.3, stable-baselines3 2.8.0
- plotly 6.7.0, shap >=0.46
- jupyter 1.1.1, tensorboard 2.18.0

### ASSUME 仿真框架 (requirements-assume.txt)
- assume-framework 0.6.0, torch 2.12.0

### Phase 4 扩展 (requirements-phase4.txt)
- fastapi >=0.136.1, uvicorn >=0.47.0
- pydantic >=2.13.4, typer >=0.15
- langchain >=1.3.1, langchain-openai >=0.3, httpx >=0.27

## Docker
- `ellectric/docker-compose.yml` — TimescaleDB + Grafana (ASSUME 集成)

## 无 CI/CD
