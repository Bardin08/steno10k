# UI design system — "Editorial Machine"

The design law every UI-building session obeys. Distilled from F3
(`docs/specs/2026-07-11-steno10k-f3-ui-design-system-design.md`). Adopts the
Impeccable (Paul Bakaus), Taste (Leon Lin), and Emil Kowalski animation rules.

**Concept:** the written word, produced by a machine. Editorial serif meets a
mono "machine record."

## Tokens

The source of truth is `frontend/src/design/tokens.css` (added in the F3
milestone). Never hardcode hex — reference tokens.

- Canvas: `--color-paper` / `--color-surface` / `--color-sink` (restrained
  near-neutral paper, **not** saturated warm-cream). Charcoal `--color-ink`
  family. Dark theme is a first-class peer; never pure black or pure white.
- Accent: a single muted evergreen (`--color-accent*`), saturation < 80%.
  Primary action = ink-black pill (one max-contrast moment per view).
- Radius: `--radius-sm 6px` · `--radius-md 12px` (cards) · `--radius-pill`.
- Depth: hairline borders + surface stacking; shadows soft and rare.

## Type triad

- **Instrument Serif** — display/headlines only; never < 20px; `text-wrap:
  balance` on h1–h3. Italic emphasis in `--color-accent-ink`.
- **Geist Sans** — all UI/body; body ≥ 14px, line length ≤ 65–75ch. **Inter is
  banned.**
- **Geist Mono** — machine-truth only: timestamps, durations, sizes, model ids,
  file names, stage numbers, kbd. Eyebrows/labels are mono uppercase.

## Motion (Emil's numbers)

- Default easing `cubic-bezier(0.22, 1, 0.36, 1)` (strong ease-out). Never
  `ease-in`.
- Durations: micro (hover/press/tooltip) 125–160ms; small elements ~180ms;
  modals/drawers ~280ms. **Everything < 300ms.** Exits ~0.8× the enter.
- **Animate `transform` + `opacity` only** — never width/height/top/left/margin.
- Press `scale(0.97)`; enter fade + `translateY` from `scale(0.96)` (never from
  `scale(0)`). **No bounce** by default; springs only for gestures/drawers.
- Popovers origin-aware; modals keep center. One orchestrated staggered
  page-load, not scattered micro-animations.
- `prefers-reduced-motion: reduce` disables transforms/transitions everywhere —
  mandatory.

## Layout

- Asymmetry over centered symmetry; vary section rhythm (never uniform gaps).
  Collapse to single column below 768px.
- Grid for 2D, flex for 1D; contain to ~1180px.

## Component states

Every data component ships **loading (skeleton matching layout), empty, and
inline error** states. Polish is completeness, not decoration.

## Ban list (reject in review)

AI purple/blue palettes · gradient text · glassmorphism decoration · identical
3-equal-card rows · nested cards · side-stripe accent borders · tiny uppercase
eyebrows on every section · `01/02/03` decoration · ghost-card (1px border +
>8px soft shadow together) · over-rounded corners · **emojis** · Inter for UI ·
centered hero at high variance · placeholder content ("John Doe", `99.99%`,
"Acme", "Elevate/Seamless") · Unsplash stock · custom cursors.

## Pass/fail test

If it's identifiable as AI-made without domain knowledge, it failed.
