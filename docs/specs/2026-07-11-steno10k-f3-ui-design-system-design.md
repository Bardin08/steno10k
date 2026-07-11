# steno10k F3 — UI Design System

_Foundation spec 3: the frozen design system **and the curated AI authoring rules**
every UI-building session obeys — so parallel agents produce one coherent
interface, not a vibe-coded mix. Ships as design tokens + an agent-facing rules doc
(`docs/standards/ui-design-system.md`, referenced by `AGENTS.md`, F0 §9) + a small
primitive component set._

Parent vision: `2026-07-11-new-audio-pipeline-vision-design.md`.
Depends on: F0 (repo operating model), F2 (API contract, for the data the UI binds).
Status: design spec, for review. A visual preview exists at
`docs/design/steno10k-style-preview.html`. Date: 2026-07-11.

---

## 1. Goal

Make "write UI code" directable and consistent: precise tokens + hard numeric rules
so any agent building any screen lands the same look, motion, and polish. The rules
are **design law** enforced through the agent knowledge doc + lint, not taste left to
chance.

## 2. Adopted design law (sources)

Three published skills are adopted as the enforced ruleset; the on-disk rules doc
distills them into steno10k-specific directives:

- **Impeccable** (Paul Bakaus) — anti-slop rules, contrast floors, motion hygiene,
  the ban list.
- **Taste** (Leon Lin) — neutral-base-plus-one-accent, banned palettes/fonts,
  asymmetry, mandatory component states, no-emoji.
- **Emil Kowalski** (animations.dev) — the motion numbers (durations, easing,
  transform/opacity, interruptibility).
- Aesthetic reference: refero "Voicenotes" + "Workflow" editorial styles.

**Pass/fail test (from Impeccable):** if it's identifiable as AI-made without domain
knowledge, it failed.

## 3. Aesthetic direction — "Editorial Machine"

The written word, produced by a machine. A transcription tool should look editorial
(serif) while showing its machine record (mono).

- **Type triad:** **Instrument Serif** display · **Geist Sans** UI · **Geist Mono**
  for machine-truth (timestamps, durations, model names, file names, stage ids,
  keyboard hints). The mono layer is the signature — it is meaningful, not decoration.
- **Canvas:** restrained near-neutral paper (deliberately **not** the saturated
  warm-cream Impeccable bans) + charcoal ink. Light is the default/signature; a dark
  theme is a first-class peer.
- **Accent:** a single muted evergreen. Primary action = ink-black pill (the one
  max-contrast moment per view).
- **Depth:** hairline borders + surface stacking over shadows.

## 4. Design tokens (frozen contract)

Expressed as CSS variables (Tailwind v4 `@theme`). Values from the approved preview.

**Light**
```
--paper:#f6f5f2  --surface:#ffffff  --surface-sink:#efeeea
--ink:#1a1917  --ink-soft:#55524c  --ink-faint:#8b877f
--hairline:#e2e0da  --hairline-strong:#cfccc4
--accent:#3f6b52  --accent-wash:#eef4ef  --accent-ink:#2c4d3a
```
**Dark** (never pure black — Taste)
```
--paper:#171614  --surface:#1f1e1b  --surface-sink:#262420
--ink:#ecebe6  --ink-soft:#a8a49b  --ink-faint:#726e65
--hairline:#2e2c28  --hairline-strong:#3a3833
--accent:#6fa585  --accent-wash:#1e2a22  --accent-ink:#a9cdb8
```
**Scale / shape / motion**
```
space: 4px base — 4/8/12/16/20/24/32/40/56/72
radius: --r-sm 6px · --r-md 12px · --r-pill 999px   (cards max 12–16px)
shadow-soft: 0 1px 2px rgba(0,0,0,.04), 0 6px 16px rgba(0,0,0,.05)
--ease: cubic-bezier(0.22, 1, 0.36, 1)   (strong ease-out)
--dur-micro:140ms  --dur:200ms  --dur-lg:280ms
maxw: 1180px
```

## 5. Typography rules

- **Serif (Instrument Serif, 400)** for display/headlines only; never below 20px;
  `text-wrap: balance` on h1–h3. Italic for emphasis, in `--accent-ink`.
- **Grotesk (Geist)** for all UI/body; body 16px/1.55, tracking `-0.006em`; body
  never below 14px; line length ≤ 65–75ch. **Inter is banned** (Taste).
- **Mono (Geist Mono)** exclusively for machine-truth: timestamps, durations, sizes,
  model ids, file names, stage numbers, kbd. Eyebrows/labels are mono uppercase,
  `letter-spacing 0.1–0.14em`.
- Display `letter-spacing` floor `-0.04em`; hero `clamp()` max ≤ 6rem.

## 6. Color rules

- Neutral base + **exactly one** accent (evergreen), saturation < 80%. **Banned:**
  AI purple/blue, gradient text, glassmorphism-as-decoration, pure `#000`/`#fff` for
  text/canvas.
- Contrast: body ≥ 4.5:1, large text ≥ 3:1, placeholders 4.5:1 (not muted gray).
- Accent reserved for: primary-ish states, links, focus rings, active tabs, status.
  Never large fills of accent.

## 7. Motion rules (Emil's numbers)

- **Default easing `--ease` (strong ease-out).** Never `ease-in`. CSS built-ins are
  too weak — use the token curve.
- **Durations:** micro (hover/press/tooltip) 125–160ms → `--dur-micro`; small
  elements (dropdown/popover/select) ~180ms → `--dur`; modals/drawers enter
  ~280ms → `--dur-lg`. **Everything < 300ms.** Exits ~0.8× the enter.
- **Animate `transform` + `opacity` only** — never width/height/top/left/margin.
- **Press:** `scale(0.97)` on `:active`. **Enter:** fade + `translateY` from
  `scale(0.96)` (never from `scale(0)`).
- **No bounce by default.** Springs (via Motion) only for gestures/drawers/drag where
  interruptibility + preserved velocity matter; CSS transitions everywhere else
  (interruptible, retarget smoothly).
- **Popovers origin-aware** (`transform-origin` from trigger); modals keep center.
- **Page load:** one orchestrated staggered reveal (`animation-delay` cascade), not
  scattered micro-animations.
- **`prefers-reduced-motion: reduce`** disables transforms/transitions everywhere —
  mandatory on every animation.
- Don't animate frequently-repeated/keyboard-driven actions.

## 8. Layout & spacing

- **Asymmetry over centered symmetry** — split heroes, offset grids, varied section
  rhythm (never uniform gaps). Collapse cleanly to single column below 768px.
- Grid for 2D, flex for 1D; breakpoint-free grids
  `repeat(auto-fit, minmax(280px,1fr))`. Contain to `--maxw`.
- Depth from hairline borders + surface stacking (`paper → surface → sink`); shadows
  soft and rare.

## 9. Component conventions

Primitives (headless + tokens): **Button** (primary ink-pill / ghost-outline; press
scale), **Input/Select/Textarea** (label above, error below, `gap-8`), **Card**
(12px, hairline, used only when elevation communicates hierarchy — no nested cards),
**Table** (mono numerics, hairline rows, hover tint), **StatusPill** (mono uppercase;
run=accent-wash, done=sink, queued=outline), **QueueRow**, **ProgressBar** (accent on
sink), **Tabs** (2px accent underline), **Toast** (Sonner-style, slightly slower
`ease`), **Modal/Drawer** (spring, focus-trapped), **Tooltip** (125ms; subsequent
instant), **EmptyState**.

**Mandatory:** every data component ships **loading (skeleton matching layout),
empty, and inline error** states — polish is completeness, not decoration.

## 10. The ban list (AI-slop tells — reject in review)

AI purple/blue palettes · gradient text · glassmorphism decoration · identical
3-equal-card rows · nested cards · side-stripe accent borders · tiny uppercase
eyebrows on every section · `01/02/03` markers as decoration · ghost-card (1px border
+ >8px soft shadow together) · over-rounded corners · **emojis** (use SVG:
Phosphor/Radix) · Inter for UI · centered hero when variance is high · placeholder
content ("John Doe", `99.99%`, "Acme", "Elevate/Seamless") · Unsplash stock · custom
cursors.

## 11. Stack

- **React SPA + TypeScript**; **Tailwind v4** with tokens as `@theme` CSS vars (single
  source of truth). Version-locked in `package.json`.
- **Radix primitives** (headless, accessible) for menus/dialogs/tabs/tooltips;
  **Motion** (Framer) only for springs/gestures.
- Icons: **Phosphor** (or Radix icons) — never emoji.
- Fonts self-hosted: Instrument Serif, Geist, Geist Mono.
- Lint/format from F0 §5 enforce import/style rules; a lint rule flags raw hex (must
  use tokens) and emoji.

## 12. Enforcement & where it lives

- **`docs/standards/ui-design-system.md`** — the agent-facing rules doc (this spec,
  distilled to directives), referenced by `AGENTS.md` (F0 §9). Every UI session reads
  it first.
- **Token source** — the Tailwind `@theme` / CSS-vars file is the frozen contract
  (F0 §3.2 coordinated changes).
- **Primitive component library** — the approved building blocks; screens compose
  these, agents don't re-invent them.

## 13. Frozen vs extensible

- **Frozen (coordinated change):** tokens, the type triad rules, motion numbers, the
  primitive component APIs, the ban list.
- **Extensible without coordination:** composing new screens from primitives, adding a
  new icon, a new empty/error copy.

## 14. Acceptance criteria

- Token file (`@theme` CSS vars) for light + dark exists and matches §4.
- `docs/standards/ui-design-system.md` distills §5–§11 into agent directives, linked
  from `AGENTS.md`.
- The primitive components in §9 are built, each with loading/empty/error states and
  the motion rules, unit-tested (render + reduced-motion).
- A lint rule rejects raw hex colors and emoji in UI code (CI-enforced, F0).
- A reference screen (e.g. the queue/monitor) assembled from primitives demonstrates
  the system end to end and matches the approved preview's look and motion.
