# Docs Site (MDX on GitHub Pages) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a beautiful, MDX-authored, full-text-searchable docs site on the existing GitHub Pages site, under `/steno10k/docs/`, styled like the landing page.

**Architecture:** A standalone Astro + `@astrojs/mdx` project in `docs-site/` builds to static HTML. Pagefind adds a build-time search index. GitHub Actions merges the landing page (root) and the docs build (`/docs/`) into one Pages artifact. The docs reuse the landing's CSS custom properties so they match by construction.

**Tech Stack:** Astro 5, `@astrojs/mdx`, Pagefind, GitHub Pages (Actions deploy), Node 20, npm.

**Verification note:** A static content site has no unit-test harness — the build IS the test. Each task is verified by `astro build` (or `npm run build`) succeeding and by grepping the generated HTML in `docs-site/dist/` for expected output. Broken internal links and MDX errors fail the build.

**Reference:** Design spec at `docs/superpowers/specs/2026-07-12-docs-site-mdx-design.md`.

---

### Task 0: Pre-work — issue and branch

Per `AGENTS.md`: one issue → one branch → one PR, branch named `<type>/<issue>-<slug>`. A worktree already exists at `../steno10k-docs` on branch `feat/docs-site-mdx` (created before the issue number was known). This task files the tracking issue and renames the branch to embed the issue number.

**Files:** none (git + GitHub only).

- [ ] **Step 1: Create the tracking issue**

Run:
```bash
gh issue create \
  --title "Docs site (MDX on GitHub Pages)" \
  --label "type:feat" \
  --body "Publish a searchable, MDX-authored docs site on the existing GitHub Pages site under /steno10k/docs/, styled like the landing page.

Design spec: docs/superpowers/specs/2026-07-12-docs-site-mdx-design.md
Plan: docs/superpowers/plans/2026-07-12-docs-site-mdx.md"
```
Expected: prints the new issue URL. Note the issue number `<N>`.

- [ ] **Step 2: Rename the branch to embed the issue number**

Run (substitute `<N>`):
```bash
git branch -m feat/docs-site-mdx feat/<N>-docs-site-mdx
```
Expected: current branch is now `feat/<N>-docs-site-mdx`. Confirm: `git branch --show-current`.

- [ ] **Step 3: Verify the design spec and plan are committed on this branch**

Run: `git log --oneline -3`
Expected: includes the spec commit (`docs: design spec for MDX docs site...`) and, after Task 0's plan commit below, the plan.

- [ ] **Step 4: Commit the plan document**

```bash
git add docs/superpowers/plans/2026-07-12-docs-site-mdx.md
git commit -m "docs: implementation plan for MDX docs site"
```

---

### Task 1: Scaffold the Astro project

**Files:**
- Create: `docs-site/package.json`
- Create: `docs-site/astro.config.mjs`
- Create: `docs-site/tsconfig.json`
- Create: `docs-site/.gitignore`
- Create: `docs-site/src/pages/index.mdx` (temporary smoke page, replaced in Task 3)

- [ ] **Step 1: Create `docs-site/package.json`**

```json
{
  "name": "steno10k-docs",
  "type": "module",
  "private": true,
  "scripts": {
    "dev": "astro dev",
    "build": "astro build && pagefind --site dist",
    "preview": "astro preview"
  },
  "dependencies": {
    "@astrojs/mdx": "^4.0.0",
    "astro": "^5.0.0"
  },
  "devDependencies": {
    "pagefind": "^1.1.0"
  }
}
```

- [ ] **Step 2: Create `docs-site/astro.config.mjs`**

The repo is `Bardin08/steno10k`, a GitHub *project* site: base path is `/steno10k/`. Docs live under `/steno10k/docs/`.

```js
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

export default defineConfig({
  site: "https://bardin08.github.io",
  base: "/steno10k/docs",
  trailingSlash: "always",
  integrations: [mdx()],
});
```

- [ ] **Step 3: Create `docs-site/tsconfig.json`**

```json
{
  "extends": "astro/tsconfigs/strict"
}
```

- [ ] **Step 4: Create `docs-site/.gitignore`**

```gitignore
dist/
node_modules/
.astro/
```

- [ ] **Step 5: Create a temporary smoke page `docs-site/src/pages/index.mdx`**

```mdx
# steno10k docs

Scaffold smoke test.
```

- [ ] **Step 6: Install dependencies**

Run: `cd docs-site && npm install`
Expected: installs astro, @astrojs/mdx, pagefind; creates `package-lock.json`.

- [ ] **Step 7: Build to verify the scaffold works**

Run: `cd docs-site && npm run build`
Expected: `astro build` completes, then `pagefind` runs over `dist/`. Output includes `docs-site/dist/index.html`.

- [ ] **Step 8: Verify the base path is applied**

Run: `grep -r "/steno10k/docs" docs-site/dist/index.html`
Expected: at least one match (Astro rewrites asset/links with the base). If the page has no base-prefixed URLs yet, instead verify the file exists: `test -f docs-site/dist/index.html && echo OK`.

- [ ] **Step 9: Commit**

```bash
git add docs-site/package.json docs-site/package-lock.json docs-site/astro.config.mjs docs-site/tsconfig.json docs-site/.gitignore docs-site/src/pages/index.mdx
git commit -m "feat: scaffold docs-site Astro project"
```

---

### Task 2: Shared design tokens

The docs must consume the landing's CSS custom properties (`--paper`, `--ink`, `--accent`, `--hairline`, fonts) so they match by construction. Extract the token block into a shared file that both the docs layout and (later, optionally) the landing can reference. For v1 we copy the token `:root` block plus the font `@import` into `docs-site/src/styles/tokens.css` — a single source the docs own; the landing keeps its own `styles.css` unchanged.

**Files:**
- Create: `docs-site/src/styles/tokens.css`

- [ ] **Step 1: Create `docs-site/src/styles/tokens.css`**

Copy the token values verbatim from `landing/styles.css` `:root` (lines 4–32) and load the same fonts the landing uses.

```css
/* Design tokens mirrored from landing/styles.css :root — keep in sync. */
@import url("https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@300;400;500;600&family=Geist+Mono:wght@400;500&display=swap");

:root {
  --paper: #f6f5f2;
  --surface: #ffffff;
  --surface-sink: #efeeea;
  --ink: #1a1917;
  --ink-soft: #55524c;
  --ink-faint: #8b877f;
  --hairline: #e2e0da;
  --hairline-strong: #cfccc4;

  --accent: #3f6b52;
  --accent-wash: #eef4ef;
  --accent-ink: #2c4d3a;

  --ease: cubic-bezier(0.22, 1, 0.36, 1);
  --dur-micro: 140ms;
  --dur: 200ms;
  --dur-lg: 280ms;

  --r-sm: 6px;
  --r-md: 12px;
  --r-pill: 999px;

  --shadow-soft: 0 1px 2px rgba(26, 25, 23, 0.04), 0 6px 16px rgba(26, 25, 23, 0.05);
  --maxw: 1180px;
}
```

- [ ] **Step 2: Commit**

```bash
git add docs-site/src/styles/tokens.css
git commit -m "feat: docs-site shared design tokens mirrored from landing"
```

---

### Task 3: Docs layout, sidebar nav, and prose styling

**Files:**
- Create: `docs-site/src/nav.ts`
- Create: `docs-site/src/styles/docs.css`
- Create: `docs-site/src/layouts/DocsLayout.astro`
- Modify: `docs-site/src/pages/index.mdx` (replace smoke page with real docs home)

- [ ] **Step 1: Create the ordered sidebar structure `docs-site/src/nav.ts`**

`slug` is base-relative (the layout prepends `import.meta.env.BASE_URL`). Order here IS the sidebar order.

```ts
export interface NavItem {
  title: string;
  slug: string; // "" = docs home
}

export const nav: NavItem[] = [
  { title: "Overview", slug: "" },
  { title: "Getting started", slug: "getting-started" },
  { title: "Configuration", slug: "configuration" },
];
```

- [ ] **Step 2: Create the prose + layout styling `docs-site/src/styles/docs.css`**

Styles the Markdown output and the layout shell using the mirrored tokens.

```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: "Geist", ui-sans-serif, system-ui, sans-serif;
  background: var(--paper);
  color: var(--ink);
  font-size: 16px;
  line-height: 1.6;
  letter-spacing: -0.006em;
  -webkit-font-smoothing: antialiased;
}

.shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 48px;
  max-width: var(--maxw);
  margin: 0 auto;
  padding: 0 32px;
}

.topbar {
  border-bottom: 1px solid var(--hairline);
  background: var(--surface);
}
.topbar-in {
  max-width: var(--maxw);
  margin: 0 auto;
  padding: 18px 32px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.brand { font-weight: 600; letter-spacing: -0.02em; }
.brand .k { color: var(--accent); }
.brand a { color: inherit; text-decoration: none; }

.sidebar {
  position: sticky;
  top: 24px;
  align-self: start;
  padding: 32px 0;
}
.sidebar nav { display: flex; flex-direction: column; gap: 2px; }
.sidebar a {
  color: var(--ink-soft);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: var(--r-sm);
  transition: background var(--dur-micro) var(--ease), color var(--dur-micro) var(--ease);
}
.sidebar a:hover { background: var(--surface-sink); color: var(--ink); }
.sidebar a[aria-current="page"] { color: var(--accent-ink); background: var(--accent-wash); }

.content {
  padding: 40px 0 96px;
  max-width: 72ch;
}
.content h1 { font-family: "Instrument Serif", Georgia, serif; font-weight: 400; font-size: 2.6rem; line-height: 1.1; margin-bottom: 0.6em; }
.content h2 { font-family: "Instrument Serif", Georgia, serif; font-weight: 400; font-size: 1.8rem; margin: 1.8em 0 0.5em; }
.content h3 { font-size: 1.15rem; font-weight: 600; margin: 1.4em 0 0.4em; }
.content p { margin: 0.9em 0; }
.content ul, .content ol { margin: 0.9em 0; padding-left: 1.4em; }
.content li { margin: 0.3em 0; }
.content a { color: var(--accent-ink); text-underline-offset: 2px; }
.content code { font-family: "Geist Mono", ui-monospace, monospace; font-size: 0.9em; background: var(--surface-sink); padding: 0.1em 0.35em; border-radius: var(--r-sm); }
.content pre { background: var(--ink); color: var(--paper); padding: 16px 18px; border-radius: var(--r-md); overflow-x: auto; margin: 1.2em 0; }
.content pre code { background: none; padding: 0; color: inherit; }
.content table { width: 100%; border-collapse: collapse; margin: 1.2em 0; font-size: 0.95em; }
.content th, .content td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--hairline); }
.content th { font-weight: 600; }
.content blockquote { border-left: 3px solid var(--accent); padding-left: 16px; color: var(--ink-soft); margin: 1.2em 0; }

#search { margin-left: auto; min-width: 220px; }

@media (max-width: 820px) {
  .shell { grid-template-columns: 1fr; gap: 0; }
  .sidebar { position: static; padding: 16px 0; }
}
```

- [ ] **Step 3: Create `docs-site/src/layouts/DocsLayout.astro`**

The content region is marked `data-pagefind-body` so Pagefind (Task 5) indexes only docs content. Sidebar highlights the current page.

```astro
---
import { nav } from "../nav";
import "../styles/tokens.css";
import "../styles/docs.css";

const { title } = Astro.props;
const base = import.meta.env.BASE_URL.replace(/\/$/, "");
const here = Astro.url.pathname.replace(/\/$/, "");

function hrefFor(slug: string) {
  return slug ? `${base}/${slug}/` : `${base}/`;
}
function isCurrent(slug: string) {
  return hrefFor(slug).replace(/\/$/, "") === here;
}
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title ? `${title} — steno10k docs` : "steno10k docs"}</title>
  </head>
  <body>
    <header class="topbar">
      <div class="topbar-in">
        <div class="brand">
          <a href={`${base}/`}><span class="n">steno</span><span class="k">10k</span> docs</a>
        </div>
        <div id="search"></div>
      </div>
    </header>

    <div class="shell">
      <aside class="sidebar">
        <nav>
          {nav.map((item) => (
            <a href={hrefFor(item.slug)} aria-current={isCurrent(item.slug) ? "page" : undefined}>
              {item.title}
            </a>
          ))}
        </nav>
      </aside>

      <main class="content" data-pagefind-body>
        <slot />
      </main>
    </div>
  </body>
</html>
```

- [ ] **Step 4: Replace `docs-site/src/pages/index.mdx` with the real docs home**

```mdx
---
layout: ../layouts/DocsLayout.astro
title: Overview
---

# steno10k documentation

steno10k turns any recording into a clean transcript and summary, entirely on
your own machine. These docs cover installing, running, and configuring it.

- **[Getting started](./getting-started/)** — run it in one container and process your first recording.
- **[Configuration](./configuration/)** — the eight pipeline stages and how to tune them.
```

- [ ] **Step 5: Build and verify the layout renders**

Run: `cd docs-site && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Verify sidebar and prose are present in output**

Run: `grep -o "Getting started" docs-site/dist/index.html && grep -o "steno10k documentation" docs-site/dist/index.html`
Expected: both strings match.

- [ ] **Step 7: Commit**

```bash
git add docs-site/src/nav.ts docs-site/src/styles/docs.css docs-site/src/layouts/DocsLayout.astro docs-site/src/pages/index.mdx
git commit -m "feat: docs layout, sidebar nav, and prose styling"
```

---

### Task 4: Write the two v1 content pages

**Files:**
- Create: `docs-site/src/pages/getting-started.mdx`
- Create: `docs-site/src/pages/configuration.mdx`

- [ ] **Step 1: Create `docs-site/src/pages/getting-started.mdx`**

```mdx
---
layout: ../layouts/DocsLayout.astro
title: Getting started
---

# Getting started

steno10k runs as a single container with one mounted volume. Point it at a
folder of recordings and it produces a clean transcript and a summary.

## Run it in one container

```bash
docker run --rm \
  -v ~/steno:/data \
  ghcr.io/bardin08/steno10k:latest
```

- `-v ~/steno:/data` mounts your working folder. Recordings go in, results come
  out in the same tree.
- Transcription runs locally with Whisper; only the clean/summarize stages call
  an OpenAI-compatible model, and only if you configure one.

## Your first run

1. Drop audio files into a project folder under your mounted volume, e.g.
   `~/steno/constitutional-law/lecture-07/`.
2. Start the container. steno10k normalizes filenames, chunks long audio,
   and transcribes each chunk in parallel.
3. When it finishes, the folder contains `clean_transcript.md` and
   `summary.md` alongside the source audio.

Next: tune what runs in **[Configuration](./configuration/)**.
```

- [ ] **Step 2: Create `docs-site/src/pages/configuration.mdx`**

```mdx
---
layout: ../layouts/DocsLayout.astro
title: Configuration
---

# Configuration

The pipeline is eight stages. Each caches to disk, so re-runs are cheap and
partial runs are free. Any stage can be switched off from config or the UI;
dependent stages cascade automatically.

## The eight stages

| # | Stage | Kind | What it does |
| --- | --- | --- | --- |
| 01 | normalize | local | Rename source files to safe, unicode-clean names. |
| 02 | chunk | local | Split long audio into overlapping ffmpeg segments. |
| 03 | transcribe | local | faster-whisper per chunk, in parallel, on CPU. |
| 04 | clean | llm | Fix punctuation and recognition errors via LLM. |
| 05 | merge | local | Concatenate raw + clean transcripts to markdown. |
| 06 | summarize | llm | Produce `summary.md` from the merged transcript. |
| 07 | bundle | local | Render transcript + summary to `.docx`. |
| 08 | notify | local | Push results to Telegram — off by default. |

## Choosing a Whisper model

Only transcription is heavy — the LLM stages are remote calls. Pick the Whisper
size that fits your machine:

| Model | Disk | RAM / worker | Quality | Fits |
| --- | --- | --- | --- | --- |
| tiny | 75 MB | ~1 GB | rough | any laptop |
| small | 490 MB | ~2 GB | good | 16 GB |
| medium | 1.5 GB | ~3 GB | very good | 16 GB |
| large-v3 | 3 GB | ~5 GB | best | workstation |

## Disabling stages

Turn off any stage you don't need — for example, disable `notify` (off by
default) or skip the LLM `clean`/`summarize` stages to stay fully local.
Disabling a stage automatically skips stages that depend on its output.
```

- [ ] **Step 3: Build and verify both pages render**

Run: `cd docs-site && npm run build`
Expected: build succeeds with no broken-link errors.

- [ ] **Step 4: Verify page output**

Run: `grep -o "Run it in one container" docs-site/dist/getting-started/index.html && grep -o "The eight stages" docs-site/dist/configuration/index.html`
Expected: both strings match.

- [ ] **Step 5: Commit**

```bash
git add docs-site/src/pages/getting-started.mdx docs-site/src/pages/configuration.mdx
git commit -m "feat: getting-started and configuration docs pages"
```

---

### Task 5: Wire up Pagefind search UI

The `build` script already runs `pagefind --site dist` (Task 1). This task mounts the prebuilt Pagefind UI into the layout so the search box in the topbar works. Pagefind assets are generated into `dist/pagefind/` at build time, so search works in `npm run preview` and in production — not in `astro dev`.

**Files:**
- Modify: `docs-site/src/layouts/DocsLayout.astro`

- [ ] **Step 1: Add the Pagefind UI assets and init to `DocsLayout.astro`**

Insert before `</body>`. `bundlePath` points at the base-prefixed Pagefind output.

```astro
    <link href={`${base}/pagefind/pagefind-ui.css`} rel="stylesheet" />
    <script is:inline define:vars={{ base }}>
      window.addEventListener("DOMContentLoaded", () => {
        const boot = () => {
          if (!window.PagefindUI) return;
          new window.PagefindUI({
            element: "#search",
            bundlePath: `${base}/pagefind/`,
            showSubResults: true,
            showImages: false,
          });
        };
        const s = document.createElement("script");
        s.src = `${base}/pagefind/pagefind-ui.js`;
        s.onload = boot;
        document.head.appendChild(s);
      });
    </script>
  </body>
```

- [ ] **Step 2: Build to generate the Pagefind index and UI assets**

Run: `cd docs-site && npm run build`
Expected: after `astro build`, Pagefind prints an indexing summary (pages indexed > 0) and writes `dist/pagefind/`.

- [ ] **Step 3: Verify the Pagefind bundle exists and the UI is wired**

Run: `test -f docs-site/dist/pagefind/pagefind-ui.js && grep -o "pagefind/pagefind-ui.js" docs-site/dist/index.html`
Expected: file exists and the built HTML references the UI script.

- [ ] **Step 4: Manually verify search returns results**

Run: `cd docs-site && npm run preview`
Then open the printed URL (e.g. `http://localhost:4321/steno10k/docs/`), type "whisper" into the search box, and confirm the Configuration page appears in results. Stop the preview server (Ctrl-C).

- [ ] **Step 5: Commit**

```bash
git add docs-site/src/layouts/DocsLayout.astro
git commit -m "feat: mount Pagefind search UI in docs layout"
```

---

### Task 6: Merge landing + docs into one Pages artifact

Rewrite the Pages workflow to build the docs, assemble a `site/` folder (landing at root, docs under `site/docs/`), and upload that.

**Files:**
- Modify: `.github/workflows/pages.yml`

- [ ] **Step 1: Replace `.github/workflows/pages.yml` with the build-and-merge version**

```yaml
name: Pages

on:
  push:
    branches: [main]
    paths: ["landing/**", "docs-site/**", ".github/workflows/pages.yml"]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: docs-site/package-lock.json

      - name: Build docs
        working-directory: docs-site
        run: |
          npm ci
          npm run build

      - name: Assemble site
        run: |
          mkdir -p site
          cp -r landing/* site/
          mkdir -p site/docs
          cp -r docs-site/dist/* site/docs/

      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Verify the merge locally (simulate the workflow)**

Run:
```bash
cd docs-site && npm run build && cd ..
rm -rf site && mkdir -p site && cp -r landing/* site/ && mkdir -p site/docs && cp -r docs-site/dist/* site/docs/
test -f site/index.html && test -f site/docs/index.html && test -f site/docs/pagefind/pagefind-ui.js && echo "MERGE OK"
```
Expected: prints `MERGE OK` (landing root page, docs home, and Pagefind bundle all present).

- [ ] **Step 3: Clean up the local simulation artifact**

Run: `rm -rf site`
Expected: `site/` removed (it is not committed; only produced by CI).

- [ ] **Step 4: Add `site/` to the repo root `.gitignore`**

Confirm the root `.gitignore` ignores the simulation output. Add this line if absent:

```gitignore
/site/
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/pages.yml .gitignore
git commit -m "ci: build and merge docs-site into the Pages artifact"
```

---

### Task 7: Repoint landing "Docs" links

The landing currently links Docs to GitHub `/tree/main/docs`. Point them at the published docs.

**Files:**
- Modify: `landing/index.html` (lines 26, 64–66, 338)

- [ ] **Step 1: Repoint the nav Docs link**

In `landing/index.html`, change the nav link:

```html
<a class="link" href="/steno10k/docs/">Docs</a>
```
(was `href="https://github.com/Bardin08/steno10k/tree/main/docs"`)

- [ ] **Step 2: Repoint the hero "Read the docs" CTA**

```html
<a class="btn btn-ghost" href="/steno10k/docs/">Read the docs</a>
```
(was `href="https://github.com/Bardin08/steno10k/tree/main/docs"`)

- [ ] **Step 3: Repoint the footer "Configuration" link**

```html
<a href="/steno10k/docs/configuration/">Configuration</a>
```
(was `href="https://github.com/Bardin08/steno10k/tree/main/docs"`)

- [ ] **Step 4: Verify no stale docs links remain**

Run: `grep -n "tree/main/docs" landing/index.html`
Expected: no matches.

- [ ] **Step 5: Verify the new links are present**

Run: `grep -c "/steno10k/docs/" landing/index.html`
Expected: `3`.

- [ ] **Step 6: Commit**

```bash
git add landing/index.html
git commit -m "feat: point landing Docs links at the published docs site"
```

---

### Task 8: CI gate for the docs build

Ensure a broken docs build fails CI on pull requests (the Pages workflow only runs on `main`).

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Read the existing CI workflow**

Run: `cat .github/workflows/ci.yml`
Expected: understand the existing job structure, trigger, and naming conventions to match style.

- [ ] **Step 2: Add a `docs` job to `.github/workflows/ci.yml`**

Add this job under `jobs:` (match the file's existing indentation and trigger — the workflow already runs on pull_request/push).

```yaml
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: docs-site/package-lock.json
      - name: Build docs (verifies MDX + links + search index)
        working-directory: docs-site
        run: |
          npm ci
          npm run build
```

- [ ] **Step 3: Validate the workflow YAML is well-formed**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"`
Expected: prints `YAML OK`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: build docs-site on PRs to gate MDX and link errors"
```

---

### Task 9: Final verification

- [ ] **Step 1: Clean full build from scratch**

Run: `cd docs-site && rm -rf dist node_modules && npm ci && npm run build`
Expected: install + `astro build` + `pagefind` all succeed.

- [ ] **Step 2: Verify the complete merged artifact**

Run:
```bash
cd .. && rm -rf site && mkdir -p site && cp -r landing/* site/ && mkdir -p site/docs && cp -r docs-site/dist/* site/docs/
for f in index.html docs/index.html docs/getting-started/index.html docs/configuration/index.html docs/pagefind/pagefind-ui.js; do
  test -f "site/$f" && echo "OK  $f" || echo "MISSING  $f"
done
rm -rf site
```
Expected: five `OK` lines, no `MISSING`.

- [ ] **Step 3: Confirm no AI attribution in any commit**

Run: `git log origin/main..HEAD --format="%an <%ae>%n%b" | grep -iE "claude|co-authored|generated with|🤖" || echo "CLEAN"`
Expected: prints `CLEAN`.

- [ ] **Step 4: Run repo pre-commit hooks over the branch**

Run: `pre-commit run --all-files`
Expected: hooks pass (or auto-fix formatting; re-stage and amend if they modify files).

---

## Self-review notes

- **Spec coverage:** issue + branch pre-work (T0), Astro+MDX scaffold (T1), shared landing tokens (T2), sidebar+content layout + prose (T3), two v1 pages (T4), Pagefind search (T5), one-artifact merged deploy (T6), repointed landing links (T7), build-as-test CI gate (T8), final verification (T9). All spec sections mapped.
- **Base path:** `/steno10k/docs` used consistently in `astro.config.mjs`, layout link construction, Pagefind `bundlePath`, and landing links.
- **Frozen contracts:** untouched — only `landing/` and new `docs-site/` are modified; `frontend/src/design/tokens.css` and the API surface are not.
- **Deferred (per spec):** versioning, dark mode, migrating existing `docs/*.md`.
