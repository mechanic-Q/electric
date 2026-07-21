# Web UI (Showcase Dashboard)

The React single-page application built with Vite and TypeScript at `ellectric/web/`. Serves as the public-facing read-only display of the Electric learning platform's output — rolling demo data, model predictions, strategy backtest results, and a plain-language Copilot chat. Built to static files served by the FastAPI backend.

## Language

**WebUI / Showcase Dashboard**:
The React SPA, served as static files from `ellectric/web/` built output, consumed by visitors at the public URL. The term covers the entire browser application including the header, Rolling Playback Stage, info panels, evidence reports, and the Copilot Panel.
_Avoid_: VIVO UI, frontend, app

**Rolling Playback Stage**:
The playhead-driven panel that synchronizes all other panels (load chart, price heatmap, renewable chart, strategy replay, evidence). Advances through the dataset at configurable speed (1x/4x/16x) and auto-loops. The primary visual metaphor of the showcase.
_Avoid_: Timeline, player, carousel

**Copilot Panel**:
The DeepSeek SSE-powered chat sidebar/bottom sheet that answers visitor questions about the dashboard in plain language, using report data and model explanations as context. On desktop it is a sticky right sidebar; on mobile it is a collapsible bottom drawer with toggle bar.
_Avoid_: Chat widget, assistant, bot

**Inline-style layout (anti-pattern)**:
Layout grids and flex containers written as inline React `style` objects rather than CSS classes. Because inline styles have higher specificity than stylesheet rules, they defeat CSS media queries and make responsive behavior impossible. The fix (extracted in the responsive refactor): move layout declarations (grid-template-columns, layout flex-direction) to CSS classes; keep only theme colors, borders, and per-element sizing inline.
_Avoid_: Inline grid, css-in-js for layout
