# #67 Verification: Integrated Explainable Strategy Replay

**Date:** 2026-07-24
**Branch:** feat/verify-integrated-replay
**Commits included:** #62 (a37cf07) → #63 (d7f50ce) → #64 (f2c3141) → #65 (90112d9) → #66 (d973be7)

## Commands Run

```bash
# Pre-bake
./.venv/bin/python -m ellectric.service.dashboard --output ellectric/web/public/rolling-demo.json

# Tests
./.venv/bin/python -m pytest --import-mode=importlib -q --no-header -p no:warnings
# Result: 231 passed, 1 failed (pre-existing: test_run_backtest_marks_loaded_agent_trained)

# Frontend build
cd ellectric/web && npm run build
# Result: ✓ built in 524ms

# Server
python -m uvicorn ellectric.api.server:app --host 127.0.0.1 --port 8766
```

## Browser Verification (Playwright + Chromium 1228)

### Viewport overflow & console errors

| Viewport | Overflow | Console Errors | Table Visible | Strategy Col Fixed |
|----------|---------:|---------------:|:--------------:|:------------------:|
| 375×667  | 0px      | 0              | ✓              | ✓                  |
| 768×1024 | 0px      | 0              | ✓              | ✓                  |
| 1280×800 | 0px      | 0              | ✓              | ✓                  |

### Accessibility

- Heat cells: `<button role="gridcell">` with `aria-label` containing strategy, date, exact value, and baseline initialization marker
- Non-color encoding: all cells display `+`, `−`, or `0` text
- SVG charts: `role="img"` with `aria-label`
- Table: 9 column headers in correct order (策略, 30天模拟价差值, 盈利日, 持仓时段正贡献率, 最大回撤, 盈利因子, 趋势倍数, Oracle捕获率, 事实标签)
- Keyboard: Tab navigates to `<button role="gridcell">` elements; table scroll region has `tabindex=0`

### Playback behavior

- Normal: auto-plays (button shows "暂停 / Pause")
- Reduced motion (`prefers-reduced-motion: reduce`): starts paused (button shows "播放 / Play")
- Source contract test verifies `visibilitychange` listener and `prefers-reduced-motion` media query

### Degraded state

- Invalid strategy snapshot → `.strategy-table` not rendered (count: 0)
- Degradation message visible
- No `.strategy-long-term` values leaked
- Pre-bake tests verify non-zero exit code on invalid input

### Copilot replay context

- `scene`: "shandong-2025-10-30d"
- `granularity`: "daily" (matches selected mode)
- `strategies`: ["td3", "ppo", "sac", "trend"]
- `content_hash`: 64 characters
- `long_term_evidence`: not present in context
- History preserved without context leakage (verified in #66 browser test)

### Screenshots

Located at `/tmp/opencode/screenshots-67/`:
- desktop-1280.png — desktop daily overview
- desktop-15min-detail.png — 15-minute detail mode
- tablet-768.png — tablet view
- phone-375.png — phone overview
- phone-table-closeup.png — phone strategy table with sticky first column
- cumulative-chart.png — cumulative spread path
- copilot-context.png — Copilot with replay context
- degraded.png — market-only degraded state

## Artifact hash

```
rolling-demo.json: 1.2MB, strategy.status=ok, 2880 points, content_hash=64 chars
```

## Known issues

- 1 pre-existing test failure (`test_run_backtest_marks_loaded_agent_trained`) — RL pipeline mock issue, unrelated to showcase replay work, present on clean master HEAD
