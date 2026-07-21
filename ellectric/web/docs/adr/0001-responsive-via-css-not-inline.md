# 0001 — Responsive layout via CSS classes, not inline styles

Status: accepted

Layout grids (grid-template-columns, layout flex-direction) must live in CSS classes so media queries can govern responsive behavior. Inline React style objects are reserved for theme colors, borders, and per-element sizing only. This ADR was triggered by a bug where four inline style objects on the app shell grid, stage grid, panel grid, and header made every existing `@media` rule dead code — the page was unusable on mobile despite having media queries. The fix extracted these four declarations to CSS classes and added 768px/980px overrides.

## Considered Options

- **Keep inline + `!important` overrides in media queries** — smallest code change, but `!important` is toxic: it breaks specificity for every future override and requires the same `!important` on every competing property.
- **Full CSS-in-JS framework (styled-components, emotion)** — would solve the problem but adds a runtime dependency and build step for what a plain CSS file handles natively.
- **Current decision: CSS classes, inline reserved for theme/sizing** — zero new dependencies, uses the platform's native cascade, and the extraction cost was a one-time ~60-line CSS addition with minimal JSX changes.

## Consequences

- New panels must decide at creation time: class vs inline for each style. Theme colors/borders → inline; layout grids → CSS class.
- Responsive behavior is governed entirely by CSS media queries, which are visible in a single stylesheet rather than scattered in JSX.
- Future mobile breakpoint changes require only CSS changes, no React re-build for logic — just a rebuild to produce new static assets.
- A future contributor could re-introduce inline grids out of ignorance; the glossary term ("Inline-style layout (anti-pattern)") and this ADR serve as durable references.
