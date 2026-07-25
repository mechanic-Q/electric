# ADR 0002: ASSUME Reclassification to Standalone Learning Experiment

## Status

Accepted

## Context

ASSUME 0.6.0 was installed and explored early in the project. Scripts exist at `ellectric/assume/run_simulation.py` (15KB) and `verify_simulation.py` (13KB) with configs and a Docker Compose file for TimescaleDB + Grafana. The project READMEs list ASSUME as a completed "市场仿真" feature alongside the other pipeline stages.

However, ASSUME was never integrated into the pipeline that produces the Showcase WebUI data. The assertion `import assume` does not appear in any `ellectric/pipeline/` module. The architecture diagram in the root README already omits ASSUME from the pipeline box. The `.planning/ROADMAP.md` records Phase 2 ASSUME as "未实施" (not implemented as integrated). The CONTEXT.md deployment boundary explicitly excludes ASSUME from the showcase.

This creates a contradiction between what the documentation claims and what the code delivers. A visitor reading the README expects ASSUME to be a functioning integrated stage, but the integrated pipeline replaces it with `ElectricityMarketEnv` + `BacktestRunner` (the speculator-spread model from PR #42).

## Decision

Reclassify ASSUME from "delivered pipeline stage" to **Standalone Learning Experiment**. In all documentation:

- ASSUME is removed from the Integrated Pipeline feature table and tech stack.
- ASSUME appears as a footnote: a standalone exploratory experiment, not part of the integrated pipeline.
- The canonical flow is the 7-stage Integrated Pipeline that produces the showcase data.

The `ellectric/assume/` directory is preserved — it remains as a learning artifact. No code changes are made to ASSUME scripts.

## Consequences

Positive:

- Documentation now matches the code — no more ASSUME claims without `import assume` in the pipeline.
- The shared 7-stage Integrated Pipeline is now the authoritative flow for both the Showcase WebUI and the GitHub README.
- Visitors are not misled about which tools are integrated.
- The ASSUME scripts remain available for learners to explore independently.

Negative:

- Learning visitors who find the project through ASSUME's domain (agent-based electricity market simulation) may be disappointed it is not a live integrated stage.
- The ASSUME installation and Docker Compose steps in the READMEs still work but are no longer promoted as a pipeline feature.

## Alternatives Considered

### Keep ASSUME as a delivered feature in the documentation

Rejected. It contradicts the code — the product (showcase data) does not go through ASSUME. If ASSUME were integrated later, the reclassification could be revisited.

### Delete all ASSUME files and references

Rejected. ASSUME was a genuine learning exercise with working scripts. Deleting it would lose legitimate educational value. Leaving the scripts with an honest label is the right balance.

### Merge ASSUME into the pipeline as originally planned

Rejected as out of scope. The showcase deployment does not run ASSUME per the CONTEXT.md deployment boundary. Integrating ASSUME would require model artifacts, PyTorch-heavy dependencies, and violate the small-server constraint of ADR 0001.
