# Structure — Ellectric

> **author**: lmr
> **created_at**: 2026-06-06T00:00:00+08:00
> **scan_type**: full
> **root**: `/mnt/e/Ellectric/`

## Directory Tree

```
Ellectric/
├── AGENTS.md                          # GSD + SillySpec workflow instructions (auto-source from .planning/)
├── INSTRUCTIONS.md                    # OpenCode CLI + Karpathy behavioral guidelines
├── .gitignore                         # Python, Jupyter, data, IDE, OS exclusions
├── .claude/                           # Claude configuration (GSD skills directory)
├── .opencode/                         # OpenCode tooling (node_modules, karpathy-guidelines.md, skills)
├── .sillyspec/                        # SillySpec state & scan documents
│   ├── .runtime/                      # Runtime DB, user-inputs, scan cache
│   ├── docs/Ellectric/scan/           # Scan output (this file + INTEGRATIONS.md)
│   ├── knowledge/                     # Archived knowledge (INDEX.md, uncategorized.md)
│   ├── projects/Ellectric.yaml        # Project metadata
│   └── workflows/                     # Workflow templates (archive-impact, scan-docs)
├── .planning/                         # GSD planning assets (read-only reference)
│   ├── PROJECT.md                     # Project charter & constraints
│   ├── REQUIREMENTS.md                # v1/v2 requirements with traceability matrix
│   ├── ROADMAP.md                     # 4-phase roadmap with success criteria
│   ├── STATE.md                       # Milestone state tracking
│   ├── config.json                    # GSD configuration toggles
│   ├── phases/01-data-foundation-basic-prediction/
│   │   ├── 01-01-PLAN.md             # Wave 1: Walking skeleton (setup, OWID, persistence forecast)
│   │   ├── 01-02-PLAN.md             # Wave 2: XGBoost + feature engineering + DataLoader
│   │   ├── 01-03-PLAN.md             # Wave 3: Docker skeleton, README, docs, notebook polish
│   │   ├── 01-CONTEXT.md             # Phase context & decisions
│   │   ├── 01-DISCUSSION-LOG.md      # Discussion history
│   │   ├── 01-RESEARCH.md            # Research findings
│   │   ├── 01-VERIFICATION.md        # Verification checklist
│   │   └── SKELETON.md               # Skeleton specification
│   └── research/
│       ├── ARCHITECTURE.md            # Architecture decisions (empty — Phase 1)
│       ├── FEATURES.md                # Feature analysis
│       ├── PITFALLS.md                # Known pitfalls & anti-patterns
│       ├── STACK.md                   # Technology stack with version pins
│       └── SUMMARY.md                 # Research summary
├── docs/
│   └── chinese-electricity-data-guide.md   # Guide to manually acquiring Chinese electricity data
└── ellectric/                         # Main Python package (Phase 1 deliverable)
    ├── README.md                      # Project README: quickstart, structure, schema, learning path
    ├── setup.sh                       # One-command environment bootstrap (checks Python 3.11+, creates venv, installs deps)
    ├── requirements.txt               # Pinned Python dependencies (8 packages)
    ├── docker-compose.yml             # Docker skeleton for Phase 2 (TimescaleDB + Grafana, commented out)
    ├── pipeline/                      # Core Python pipeline modules
    │   ├── __init__.py               # Package marker
    │   ├── data_loader.py            # Abstract DataLoader + OWIDChinaLoader + ChineseDataLoader + factory
    │   ├── cleaner.py                # Data cleaning: missing fill (ffill/bfill), IQR outlier detection (report-only), UTC timezone normalization
    │   ├── features.py               # Feature engineering: FeatureEngineer class with progressive tiered features (Tier 1/2/3)
    │   └── forecaster.py             # Forecasting engine: persistence_forecast(), XGBoostForecaster class, P&L calculation & viz
    ├── notebooks/                    # Jupyter learning notebooks (5-stage learning path)
    │   ├── 01_data_ingestion.ipynb   # Data acquisition: OWID auto-fetch + local file loading
    │   ├── 02_data_cleaning.ipynb    # Data cleaning: IQR detection, missing handling, schema validation
    │   ├── 03_feature_engineering.ipynb  # Feature generation: calendar features, lag features, rolling stats, cyclic encoding
    │   ├── 04_load_forecasting.ipynb # XGBoost model: TimeSeriesSplit training, hyperparameter tuning, metric evaluation
    │   └── 05_end_to_end_baseline.ipynb  # End-to-end baseline: persistence → P&L → interactive plotly visualization
    └── data/                         # Local data directory (gitignored except .gitkeep)
        └── .gitkeep
```

## Module Descriptions

### `ellectric/` — Main package root
Python package containing all Phase 1 deliverables. Designed as a self-contained learning environment with one-command setup, 5 progressive Jupyter notebooks, and a modular pipeline library. Python 3.11+ required.

### `ellectric/pipeline/` — Core pipeline library

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `__init__.py` | Package marker | — |
| `data_loader.py` | Data acquisition layer — abstracts data sources behind a uniform interface | `DataLoader` (ABC), `OWIDChinaLoader` (auto-fetch from GitHub raw CSV), `ChineseDataLoader` (local CSV/Excel/Parquet), `create_loader()` (factory) |
| `cleaner.py` | Data cleaning & validation — enforces a data contract for downstream modules | `clean_data()` (4-step pipeline: validate → fill → IQR report → UTC normalize), `validate_schema()` (runtime schema checker) |
| `features.py` | Feature engineering — progressive 3-tier feature generation designed for learning | `FeatureEngineer` (add_tier1/2/3_features()), `prepare_features()` (convenience) |
| `forecaster.py` | Forecasting & P&L — baseline persistence model + XGBoost with time-aware CV + interactive visualization | `persistence_forecast()` (t-24h baseline), `calculate_pnl()`, `plot_pnl()` (plotly), `XGBoostForecaster` (train_evaluate + predict with per-fold StandardScaler fit) |

### `ellectric/notebooks/` — 5-stage progressive learning path
Each notebook builds on the previous, following the data-science pipeline: Ingest → Clean → Engineer → Train → Deploy. All notebooks contain Markdown explanations, code cells, visual output, and reflection questions.

### `ellectric/data/` — Local data directory
Manual downloaded data (CSV/Excel/Parquet) stored here. Gitignored except for `.gitkeep`. The `ChineseDataLoader` reads from this directory.

### `ellectric/docker-compose.yml` — Docker skeleton
Commented-out TimescaleDB (latest-pg16) and Grafana (latest) services for Phase 2. Ready to uncomment when ASSUME market simulation is introduced.

### `.planning/` — GSD planning assets (read-only)
Contains the original Phase 1 roadmap, requirements, stack decisions, and three completed plan documents. Preserved as historical reference; active development uses SillySpec workflow.

### `.sillyspec/` — SillySpec runtime & docs
Active workflow state (`runtime/`), scan outputs (`docs/Ellectric/scan/`), archived knowledge, and project metadata. Driven by `/sillyspec:*` commands.
