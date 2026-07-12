# Docs site (MDX on GitHub Pages) — design

**Status:** draft for review
**Date:** 2026-07-12
**Branch / worktree:** `feat/docs-site-mdx` → `../steno10k-docs`

## Problem

The landing page (`landing/`) links "Docs" to the raw `docs/` folder on GitHub.
That is fine for developers but is not a beautiful, no-install, user-facing docs
experience. We want online documentation for end-users that:

- lives on the **same GitHub Pages site** as the landing page,
- looks like the landing page (same "Editorial Machine" style),
- is authored in **MDX** (Markdown + optional embedded components),
- requires no separate hosting and no install for readers.

## Constraints & context

- **One Pages site per repo.** `Bardin08/steno10k` publishes a *project* site at
  `https://bardin08.github.io/steno10k/` — base path `/steno10k/`. There is a
  single `github-pages` environment and a single artifact upload. Landing + docs
  must therefore be **merged into one output folder** (landing at root, docs
  under `/docs/`), not deployed as two independent Pages sites.
- **Current deploy** (`.github/workflows/pages.yml`) uploads the `landing/`
  folder verbatim — no build step. Adding MDX requires introducing a build step.
- **Landing styling** lives in `landing/styles.css` as an "Editorial Machine"
  system: CSS custom properties (`--paper`, `--surface`, `--ink`, `--accent`,
  `--hairline`, radii, motion) plus fonts Instrument Serif (serif display),
  Geist (UI), Geist Mono (machine truth). Docs will **consume these tokens**
  rather than re-declare them.
- **Frozen contracts** (per `AGENTS.md`): `frontend/src/design/tokens.css` and
  the API surface. This work does **not** touch them — it consumes only
  `landing/styles.css`, which is not a frozen contract.
- The existing React app (`frontend/`) is unrelated to the landing page and is
  out of scope; the docs site is standalone.

## Decisions (settled during brainstorming)

| Decision | Choice |
| --- | --- |
| Generator | **Astro + `@astrojs/mdx`**, static output |
| Styling source | **Reuse `landing/styles.css`** tokens (one source of truth) |
| Content | **New user-facing docs, authored fresh** (existing `docs/` stays dev-facing) |
| Navigation | **Sidebar + content** (classic docs layout) |
| Search | **Full-text search via Pagefind** (static, build-time index) |
| v1 scope | **Minimal**: scaffold + merged deploy + shared styling + search + 1–2 real pages |
| Theme | **Light only** (matches landing; no dark mode in v1) |

## Architecture

A new **`docs-site/`** Astro project, sibling to `landing/` and `frontend/`,
building to static HTML that is merged into the same Pages artifact as the
landing page.

```
docs-site/
├─ package.json            # astro, @astrojs/mdx  (npm, matching frontend/)
├─ astro.config.mjs        # site: https://bardin08.github.io
│                          # base: /steno10k/docs
├─ src/
│  ├─ layouts/DocsLayout.astro   # nav + sidebar + content shell
│  ├─ styles/docs.css            # prose layer, consumes landing CSS vars
│  ├─ nav.ts                     # ordered sidebar structure (explicit)
│  └─ content/
│     ├─ config.ts               # content collection schema (title, order)
│     └─ docs/
│        ├─ index.mdx            # docs home → redirect to getting-started
│        ├─ getting-started.mdx
│        └─ configuration.mdx
```

**Standalone Astro project vs. bolting MDX onto `frontend/`:** standalone.
The landing is plain static HTML/CSS with nothing to do with the React app; a
separate Astro project keeps the docs build simple, fast, and independent of the
app's Vite/React toolchain.

## Styling — inheriting the landing look

- `DocsLayout.astro` reuses the landing's **CSS custom properties** (`--paper`,
  `--ink`, `--accent`, `--hairline`, the three font families) rather than
  re-declaring them. The shared `:root` tokens + nav/footer chrome are made
  available to the layout (either by importing `landing/styles.css` directly, or
  by factoring the token block into a shared `tokens.css` both consume — chosen
  during implementation, whichever keeps a single source of truth).
- A new `docs.css` styles rendered Markdown output — `h1`–`h4`, `p`, `ul`/`ol`,
  inline `code` and code blocks, tables, blockquotes, and heading anchor links —
  using those variables. A `## heading` renders in Instrument Serif on `--paper`,
  matching the landing by construction.
- **Light only** in v1, matching the landing (which declares no dark theme).

## Deploy — one Pages artifact

Rewrite `.github/workflows/pages.yml` to build-then-merge (single deploy):

1. `actions/checkout`
2. `actions/setup-node` (Node 20) → `npm ci` in `docs-site/`
3. `npm run build` in `docs-site/` → `astro build && pagefind --site dist`
   (static HTML + Pagefind search index)
4. Assemble `site/`: `cp -r landing/* site/`, then docs build output → `site/docs/`
5. `actions/upload-pages-artifact` with `path: site` → `actions/deploy-pages`
6. Trigger `paths` widened to `["landing/**", "docs-site/**"]`

Landing "Docs" links repointed from GitHub `/tree/main/docs` → `/steno10k/docs/`
(`landing/index.html` nav link, hero "Read the docs" CTA, footer "Configuration").

## Content (v1) & navigation

- Sidebar driven by an explicit, ordered `nav.ts` (predictable ordering, not
  auto-globbed).
- Two real pages for v1, enough to prove the pipeline end-to-end:
  - **`getting-started.mdx`** — install & run in one container; first-run
    walkthrough.
  - **`configuration.mdx`** — the eight stages, Whisper model sizing, enabling
    and disabling stages.
- **`index.mdx`** (docs home) redirects to Getting Started.
- Deferred to later issues: additional pages, versioning, dark mode.

## Search — full-text via Pagefind

Server-free, service-free static search using **Pagefind**:

- After `astro build`, run Pagefind over the built `docs/` output. It crawls the
  static HTML, produces a compact fragment index plus a prebuilt search UI, and
  writes them into the output (`/steno10k/docs/pagefind/`). No server, no
  third-party service — works on GitHub Pages.
- `DocsLayout` mounts the Pagefind UI in the sidebar/header (search box +
  keyboard shortcut). Styling is themed to consume the landing CSS vars so the
  search box matches the rest of the site.
- The index is scoped to the docs output only (not the landing page), so results
  are docs pages.
- Wiring: add `pagefind` as a docs-site dev dependency and a build script
  (`astro build && pagefind --site dist`), so the merged `site/docs/` already
  contains the index. The GitHub Actions job runs the same script — no extra
  step beyond the existing docs build.

## Testing & verification

- `astro build` fails on broken internal links and MDX errors — this is the core
  CI gate. Add a `docs` job (or fold into `ci.yml`) that runs the docs build.
- Local verification: `npm run build`, serve the merged `site/`, and click
  through `/steno10k/docs/` before relying on the Actions deploy.
- No content unit-test framework — the build is the test.

## Out of scope (v1)

Doc versioning, dark mode, migrating existing `docs/*.md` content, and any
change to `frontend/` or frozen contracts.
