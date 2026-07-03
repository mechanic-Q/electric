---
id: task-05
title: 落实非交易边界和风险文案
author: lmr
created_at: 2026-07-03 17:06:03
priority: P0
depends_on: [task-03, task-04]
blocks: [task-06]
requirement_ids: [FR-011, FR-012]
decision_ids: [D-003@v1]
allowed_paths: [ellectric/web/src/App.tsx, ellectric/web/src/styles.css]
---
goal: >
  Make every trading-adjacent UI phrase clearly frame the system as a learning prototype for backtesting and strategy evaluation.
implementation:
  - Add visible non-trading disclaimer to header and strategy areas.
  - Reword value-chain and Copilot copy toward data explanation, report reading, and historical backtests.
  - Remove wording that implies live trading, orders, trading advice, signals, or profit guarantees.
acceptance:
  - Header states learning prototype and not trading advice.
  - Strategy cards state historical backtests do not imply future performance.
  - Forbidden trading/live-order/profit phrases are absent from new frontend source.
verify:
  - '! /usr/bin/rg -n "交易建议|自动交易|下单|实盘|收益保证|交易信号|买卖点" ellectric/web/src'
  - cd ellectric/web && npm run build
constraints:
  - Use learning prototype/backtest/strategy evaluation/hypothesis wording only.
  - Do not add real trading, order placement, or live scheduling capability.
  - Do not modify backend API semantics.
