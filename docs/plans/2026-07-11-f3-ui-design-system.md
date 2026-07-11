# F3 — UI Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the frozen "Editorial Machine" design system in code — the token contract (`frontend/src/design/tokens.css` via Tailwind v4 `@theme`, light + dark), self-hosted type triad, a CI-enforced lint rule banning raw hex + emoji, the primitive component library (§9 of the spec, each with loading/empty/error states), and a reference screen assembled from the primitives that matches the approved preview.

**Architecture:** React 19 + Vite SPA already scaffolded. Adopt **Tailwind v4** with the `@tailwindcss/vite` plugin; `tokens.css` is the single source of truth — an `@theme` block registers the design tokens (which auto-generate `bg-paper`, `text-ink`, `rounded-md`, `font-mono`, `ease-editorial`, … utilities) and a `[data-theme="dark"]` block overrides the same CSS vars so theme flips at runtime with zero `dark:` variants. Components are className-only (no CSS modules); Radix supplies headless a11y for Tabs/Tooltip/Dialog/Select; Sonner supplies toasts; Phosphor supplies icons. Motion (Framer) is intentionally **not** added — the spec restricts springs to gesture/drag interactions, and none exist in the primitive set; entrance animation is CSS + a `useReducedMotion` gate. Delivered in **three PRs**: PR-A freezes the contract (tokens + fonts + lint + theme), PR-B builds primitives, PR-C builds the reference screen.

**Tech Stack:** TypeScript (strict) · React 19 · Vite 6 · Tailwind v4 · Radix primitives · Sonner · Phosphor · Fontsource (self-hosted fonts) · Vitest + Testing Library · ESLint (flat) + Prettier.

**Source spec:** `docs/specs/2026-07-11-steno10k-f3-ui-design-system-design.md`.
**Standard doc:** `docs/standards/ui-design-system.md` (already distills spec §5–§11 and is linked from `AGENTS.md` — acceptance criterion #2 is already satisfied; this plan implements the rest).
**Approved preview:** `docs/design/steno10k-style-preview.html` (the look/motion PR-C must match).

**Git:** `tokens.css` is a **frozen contract** (CODEOWNERS + `AGENTS.md`). PR-A *creates* it (no prior version to coordinate), so **no contract-lock is needed** — but check `~/.claude/locks/steno10k/` before starting anyway. Later edits to `tokens.css` **do** require the lock protocol. Each PR: one branch → one PR → squash-merge. All work is under `frontend/`.

**CI gate (every PR must pass — `.github/workflows/ci.yml` `frontend` job):**
`cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build`

---

# PR-A — Token contract, fonts, theme, lint rule

_Freezes the design system's shared surface so screen work can fan out on top of it._

## Task A0: Epic + three sub-issues (all up front) + first branch

Create the F3 epic and **all three** sub-issues now — the whole milestone is
planned, so there's nothing to wait for. Each PR branch references its
pre-created issue number; PR-B and PR-C don't re-create issues.

- [ ] **Step 1: Confirm no active contract lock**

```bash
ls ~/.claude/locks/steno10k/ 2>/dev/null || echo "no locks — clear to proceed"
```

- [ ] **Step 2: Create the three sub-issues, then the epic that tracks them**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k

A=$(gh issue create --title "F3a: design tokens, fonts, theme, lint rule" \
  --label "area:frontend,type:feat" \
  --body "Freeze the Editorial Machine token contract (frontend/src/design/tokens.css via Tailwind v4 @theme, light + dark), self-host the type triad, add the CI hex/emoji lint rule, and a theme provider. Per docs/specs/2026-07-11-steno10k-f3-ui-design-system-design.md. Unblocks F3b." \
  | grep -oE '[0-9]+$')

B=$(gh issue create --title "F3b: primitive component library" \
  --label "area:frontend,type:feat" \
  --body "Build the spec §9 primitives (Button, form fields, Card, Table, StatusPill, ProgressBar, QueueRow, Tabs, Tooltip, Modal, Drawer, Toast, EmptyState, Skeleton, ErrorState), each with loading/empty/error states + reduced-motion, unit-tested. Depends on F3a." \
  | grep -oE '[0-9]+$')

C=$(gh issue create --title "F3c: reference screen (queue/monitor)" \
  --label "area:frontend,type:feat" \
  --body "Assemble the queue/monitor reference screen from the F3b primitives, matching docs/design/steno10k-style-preview.html — proves the design system end to end. Depends on F3b." \
  | grep -oE '[0-9]+$')

gh issue create --title "F3: UI design system (epic)" \
  --label "area:frontend,type:feat" \
  --body "$(printf 'Ships the Editorial Machine design system per docs/plans/2026-07-11-f3-ui-design-system.md.\n\nSub-issues (one PR each, sequential):\n- [ ] #%s F3a — token contract, fonts, theme, lint rule\n- [ ] #%s F3b — primitive component library\n- [ ] #%s F3c — reference screen\n' "$A" "$B" "$C")"

echo "F3a=#$A  F3b=#$B  F3c=#$C  — note these; each PR branch uses its number."
```

> Record the three numbers. Throughout this plan: **N** = F3a (`$A`), **M** =
> F3b (`$B`), **P** = F3c (`$C`).

- [ ] **Step 3: Branch off main for PR-A** (use F3a's number `N`)

```bash
git switch main && git pull -q
git switch -c feat/N-f3-tokens
```

---

## Task A1: Add Tailwind v4 via the Vite plugin

**Files:**
- Modify: `frontend/package.json` (deps)
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/design/global.css`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Install Tailwind v4 + the Vite plugin**

```bash
cd frontend
npm install -D tailwindcss@^4 @tailwindcss/vite@^4
```

- [ ] **Step 2: Wire the plugin into Vite** — replace `frontend/vite.config.ts` with:

```ts
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

- [ ] **Step 3: Create the CSS entry** `frontend/src/design/global.css` (imports Tailwind + the token contract; `tokens.css` arrives in Task A2):

```css
@import "tailwindcss";
@import "./tokens.css";
```

- [ ] **Step 4: Import the CSS entry once, at the app root** — add to the top of `frontend/src/main.tsx` (above the React imports):

```ts
import "./design/global.css";
```

- [ ] **Step 5: Verify the dev build boots**

Run: `cd frontend && npx vite build`
Expected: build succeeds (Tailwind processes the CSS; `tokens.css` not-found is fixed in A2 — if you run before A2, create an empty `src/design/tokens.css` first).

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/design/global.css frontend/src/main.tsx
git commit -m "chore: add Tailwind v4 via @tailwindcss/vite plugin"
```

---

## Task A2: Frozen token contract (`tokens.css`) — light + dark

**Files:**
- Create: `frontend/src/design/tokens.css`
- Create: `frontend/src/design/tokens.test.ts`

Token names mirror `docs/standards/ui-design-system.md` (`--color-*`, `--radius-*`, `--font-*`, `--ease-editorial`). Values are copied verbatim from the approved preview (`docs/design/steno10k-style-preview.html`).

- [ ] **Step 1: Write the failing test** (guards the frozen values so accidental edits fail CI) — `frontend/src/design/tokens.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";

const css = readFileSync(
  fileURLToPath(new URL("./tokens.css", import.meta.url)),
  "utf8",
);

test("light canvas + accent tokens match the approved preview", () => {
  expect(css).toContain("--color-paper: #f6f5f2;");
  expect(css).toContain("--color-ink: #1a1917;");
  expect(css).toContain("--color-accent: #3f6b52;");
  expect(css).toContain("--color-accent-wash: #eef4ef;");
});

test("dark theme overrides the same vars (never pure black)", () => {
  expect(css).toContain('[data-theme="dark"]');
  expect(css).toContain("--color-paper: #171614;");
  expect(css).toContain("--color-accent: #6fa585;");
  expect(css).not.toContain("#000000");
});

test("motion + shape tokens exist", () => {
  expect(css).toContain("--ease-editorial: cubic-bezier(0.22, 1, 0.36, 1);");
  expect(css).toContain("--dur-micro: 140ms;");
  expect(css).toContain("--radius-md: 12px;");
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- tokens` → FAIL (`tokens.css` missing/empty).

- [ ] **Step 3: Implement `frontend/src/design/tokens.css`**

```css
/* ============================================================
   steno10k — "Editorial Machine" design tokens (FROZEN CONTRACT)
   Source of truth. Values from docs/design/steno10k-style-preview.html.
   Edits require the contract-lock protocol (AGENTS.md).
   @theme registers tokens -> auto-generates bg-*/text-*/border-*/
   rounded-*/font-*/ease-* utilities. [data-theme="dark"] overrides the
   same CSS vars so the theme flips at runtime with no dark: variants.
   ============================================================ */
@theme {
  /* canvas — restrained near-neutral paper (NOT saturated cream) */
  --color-paper: #f6f5f2;
  --color-surface: #ffffff;
  --color-sink: #efeeea;
  --color-ink: #1a1917;
  --color-ink-soft: #55524c;
  --color-ink-faint: #8b877f;
  --color-hairline: #e2e0da;
  --color-hairline-strong: #cfccc4;

  /* single functional accent — muted evergreen (no AI blue/purple) */
  --color-accent: #3f6b52;
  --color-accent-wash: #eef4ef;
  --color-accent-ink: #2c4d3a;

  /* type triad */
  --font-serif: "Instrument Serif", Georgia, serif;
  --font-sans: "Geist Variable", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "Geist Mono Variable", ui-monospace, monospace;

  /* shape */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-pill: 999px;

  /* motion — Emil's numbers */
  --ease-editorial: cubic-bezier(0.22, 1, 0.36, 1);
}

/* Non-utility design vars (durations, shadow, layout width). */
:root {
  --dur-micro: 140ms;
  --dur: 200ms;
  --dur-lg: 280ms;
  --shadow-soft: 0 1px 2px rgba(26, 25, 23, 0.04), 0 6px 16px rgba(26, 25, 23, 0.05);
  --maxw: 1180px;
}

/* Dark theme — a first-class peer. Never pure black/white (Taste). */
[data-theme="dark"] {
  --color-paper: #171614;
  --color-surface: #1f1e1b;
  --color-sink: #262420;
  --color-ink: #ecebe6;
  --color-ink-soft: #a8a49b;
  --color-ink-faint: #726e65;
  --color-hairline: #2e2c28;
  --color-hairline-strong: #3a3833;
  --color-accent: #6fa585;
  --color-accent-wash: #1e2a22;
  --color-accent-ink: #a9cdb8;

  --shadow-soft: 0 1px 2px rgba(0, 0, 0, 0.3), 0 6px 16px rgba(0, 0, 0, 0.35);
}

/* Base typography + the mandatory reduced-motion kill-switch. */
@layer base {
  html {
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }
  body {
    background: var(--color-paper);
    color: var(--color-ink);
    font-family: var(--font-sans);
    font-size: 16px;
    line-height: 1.55;
    letter-spacing: -0.006em;
  }
  h1,
  h2,
  h3 {
    font-family: var(--font-serif);
    font-weight: 400;
    text-wrap: balance;
    letter-spacing: -0.018em;
  }

  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
}
```

- [ ] **Step 4: Run tests, verify pass** — `cd frontend && npm test -- tokens` → PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/design/tokens.css frontend/src/design/tokens.test.ts
git commit -m "feat: frozen Editorial Machine token contract (light + dark)"
```

---

## Task A3: Self-host the type triad (Fontsource)

**Files:**
- Modify: `frontend/package.json` (deps)
- Modify: `frontend/src/design/global.css`

Instrument Serif is a static 400 (+ italic) face; Geist and Geist Mono ship as variable fonts. Fontsource self-hosts them (no Google CDN — the spec bans third-party font hosting for a local-first tool).

- [ ] **Step 1: Install the faces**

```bash
cd frontend
npm install @fontsource/instrument-serif @fontsource-variable/geist @fontsource-variable/geist-mono
```

- [ ] **Step 2: Import them in the CSS entry** — replace `frontend/src/design/global.css` with:

```css
@import "tailwindcss";

/* self-hosted type triad (bundled by Vite — no third-party CDN) */
@import "@fontsource/instrument-serif/400.css";
@import "@fontsource/instrument-serif/400-italic.css";
@import "@fontsource-variable/geist";
@import "@fontsource-variable/geist-mono";

@import "./tokens.css";
```

> The `--font-sans`/`--font-mono` families in `tokens.css` (`"Geist Variable"`, `"Geist Mono Variable"`) are the family names Fontsource's variable packages register. Instrument Serif registers as `"Instrument Serif"`.

- [ ] **Step 3: Verify the build bundles the fonts**

Run: `cd frontend && npm run build`
Expected: PASS; `dist/assets` contains `.woff2` font files.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/design/global.css
git commit -m "feat: self-host the Instrument Serif / Geist / Geist Mono triad"
```

---

## Task A4: Theme provider + `useReducedMotion` hook

**Files:**
- Create: `frontend/src/theme/ThemeProvider.tsx`
- Create: `frontend/src/theme/useReducedMotion.ts`
- Create: `frontend/src/theme/theme.test.tsx`

- [ ] **Step 1: Write the failing tests** — `frontend/src/theme/theme.test.tsx`:

```tsx
import { act, render, renderHook, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";
import { useReducedMotion } from "./useReducedMotion";
import { setReducedMotion } from "../test/matchMedia";

function Toggle() {
  const { theme, toggle } = useTheme();
  return (
    <button onClick={toggle} data-theme-state={theme}>
      toggle
    </button>
  );
}

test("provider defaults to light and flips data-theme on <html>", () => {
  render(
    <ThemeProvider>
      <Toggle />
    </ThemeProvider>,
  );
  const btn = screen.getByRole("button");
  expect(btn.getAttribute("data-theme-state")).toBe("light");
  expect(document.documentElement.dataset.theme).toBe("light");
  act(() => btn.click());
  expect(document.documentElement.dataset.theme).toBe("dark");
});

test("useReducedMotion reads the media query", () => {
  setReducedMotion(true);
  const { result } = renderHook(() => useReducedMotion());
  expect(result.current).toBe(true);
  setReducedMotion(false);
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- theme` → FAIL.

- [ ] **Step 3: Implement `frontend/src/theme/ThemeProvider.tsx`**

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type Theme = "light" | "dark";
type ThemeContextValue = { theme: Theme; toggle: () => void };

const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "steno10k-theme";

function readInitial(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "dark" ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readInitial);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggle = useCallback(
    () => setTheme((t) => (t === "light" ? "dark" : "light")),
    [],
  );

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}
```

> Fix the import typo before running: React exports `useCallback` (lowercase c). The line must read `useCallback,` — written here to be pasted exactly: `import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";`

- [ ] **Step 4: Implement `frontend/src/theme/useReducedMotion.ts`**

```ts
import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/** True when the user asked the OS to reduce motion. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => window.matchMedia(QUERY).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(QUERY);
    const onChange = () => setReduced(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return reduced;
}
```

- [ ] **Step 5: Run tests + lint + types, verify pass**

Run: `cd frontend && npm test -- theme && npm run lint && npm run typecheck`
Expected: PASS (the test setup + `matchMedia` mock land in Task A5; if you run this task standalone first, create `src/test/setup.ts` and `src/test/matchMedia.ts` from A5 Steps 3–4 now).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/theme/
git commit -m "feat: theme provider (data-theme on <html>) + useReducedMotion"
```

---

## Task A5: CI lint rule — ban raw hex + emoji in UI code

**Files:**
- Create: `frontend/eslint-rules/index.js`
- Create: `frontend/eslint-rules/index.test.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/matchMedia.ts`
- Modify: `frontend/eslint.config.js`
- Modify: `frontend/package.json` (dev dep: `@testing-library/jest-dom`)

The rule set catches hardcoded hex colors (must use tokens) and emoji (must use Phosphor SVG) in `.ts`/`.tsx`. `tokens.css` is CSS — ESLint never lints it, so the frozen hex source is unaffected.

- [ ] **Step 1: Write the failing rule test** — `frontend/eslint-rules/index.test.ts`:

```ts
import { RuleLoad } from "eslint";
import { expect, test } from "vitest";
import plugin from "./index.js";

const { RuleTester } = await import("eslint");
const tester = new RuleTester({
  languageOptions: { ecmaVersion: 2022, sourceType: "module" },
});

test("no-raw-hex flags a hardcoded color, allows token references", () => {
  tester.run("no-raw-hex", plugin.rules["no-raw-hex"], {
    valid: [
      { code: 'const c = "var(--color-ink)";' },
      { code: 'const path = "#/queue";' }, // route hash, not a color
    ],
    invalid: [
      {
        code: 'const c = "#ffffff";',
        errors: [{ messageId: "rawHex" }],
      },
      {
        code: 'const x = <div className="bg-[#3f6b52]" />;',
        errors: [{ messageId: "rawHex" }],
        languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } },
      },
    ],
  });
});

test("no-emoji flags an emoji in a string or JSX text", () => {
  tester.run("no-emoji", plugin.rules["no-emoji"], {
    valid: [{ code: 'const s = "done";' }],
    invalid: [{ code: 'const s = "done ✅";', errors: [{ messageId: "emoji" }] }],
  });
});

// keep the import referenced so lint of the test file stays clean
void RuleLoad;
```

> Drop the `RuleLoad` import + the trailing `void RuleLoad;` line if your ESLint version doesn't export it — they're only there to demonstrate imports; the real handle is `RuleTester`. Simplest form: `import { RuleTester } from "eslint";` at the top and delete both `RuleLoad` lines.

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- eslint-rules` → FAIL.

- [ ] **Step 3: Implement `frontend/eslint-rules/index.js`**

```js
/**
 * steno10k local ESLint rules — design-law enforcement.
 * Flat-config plugin: { rules: { "no-raw-hex", "no-emoji" } }.
 */

// 3/4/6/8-digit hex color, e.g. #fff #3f6b52 #3f6b52ff — but NOT "#/route" or "#top".
const HEX = /#[0-9a-fA-F]{3,4}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b/;
const EMOJI = /\p{Extended_Pictographic}/u;

function checkText(context, node, raw, key) {
  const re = key === "rawHex" ? HEX : EMOJI;
  if (typeof raw === "string" && re.test(raw)) {
    context.report({ node, messageId: key });
  }
}

const noRawHex = {
  meta: {
    type: "problem",
    docs: { description: "Ban hardcoded hex colors; use design tokens." },
    messages: {
      rawHex: "Raw hex color is banned — reference a design token (var(--color-*) / a token utility).",
    },
    schema: [],
  },
  create(context) {
    return {
      Literal(node) {
        checkText(context, node, node.value, "rawHex");
      },
      TemplateElement(node) {
        checkText(context, node, node.value.raw, "rawHex");
      },
      JSXText(node) {
        checkText(context, node, node.value, "rawHex");
      },
    };
  },
};

const noEmoji = {
  meta: {
    type: "problem",
    docs: { description: "Ban emoji in UI code; use Phosphor SVG icons." },
    messages: { emoji: "Emoji is banned — use a Phosphor SVG icon instead." },
    schema: [],
  },
  create(context) {
    return {
      Literal(node) {
        checkText(context, node, node.value, "emoji");
      },
      TemplateElement(node) {
        checkText(context, node, node.value.raw, "emoji");
      },
      JSXText(node) {
        checkText(context, node, node.value, "emoji");
      },
    };
  },
};

export default { rules: { "no-raw-hex": noRawHex, "no-emoji": noEmoji } };
```

- [ ] **Step 4: Create the test scaffolding used by every component test** — `frontend/src/test/matchMedia.ts`:

```ts
import { vi } from "vitest";

/** Install a controllable window.matchMedia (jsdom has none). */
export function setReducedMotion(reduced: boolean): void {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: reduced && query.includes("prefers-reduced-motion"),
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
```

`frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { setReducedMotion } from "./matchMedia";

setReducedMotion(false); // default: motion enabled
afterEach(() => {
  cleanup();
  setReducedMotion(false);
});
```

Install the matcher dep:

```bash
cd frontend && npm install -D @testing-library/jest-dom
```

- [ ] **Step 5: Wire the rules into the flat config** — replace `frontend/eslint.config.js` with:

```js
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import steno10k from "./eslint-rules/index.js";

export default tseslint.config(
  { ignores: ["dist", "eslint-rules/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { steno10k },
    rules: {
      "steno10k/no-raw-hex": "error",
      "steno10k/no-emoji": "error",
    },
  },
);
```

- [ ] **Step 6: Run the full frontend gate, verify pass**

Run: `cd frontend && npm test && npm run lint && npm run typecheck && npm run build`
Expected: PASS. (If lint flags a `#` in existing code, replace it with a token; that is the rule working.)

- [ ] **Step 7: Commit**

```bash
git add frontend/eslint-rules/ frontend/src/test/ frontend/eslint.config.js frontend/package.json frontend/package-lock.json
git commit -m "feat: CI lint rule banning raw hex + emoji in UI code"
```

---

## Task A6: Ship PR-A

- [ ] **Step 1: Full gate** — `cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build` → all green. (Run `npm run format:write` first if `format:check` fails.)

- [ ] **Step 2: Push + open PR**

```bash
git push -u origin feat/N-f3-tokens
gh pr create --base main --title "F3a: design tokens, fonts, theme, lint rule" \
  --body "Closes #N. Freezes the Editorial Machine token contract (frontend/src/design/tokens.css, Tailwind v4 @theme, light + dark), self-hosts the type triad, adds the CI hex/emoji lint rule, and a theme provider + useReducedMotion. Unblocks the primitive library."
```

- [ ] **Step 3: Hand off for review** — post the PR link and **stop**. The user
  reviews in GitHub and squash-merges. Do not merge from the CLI. Once the user
  confirms F3a is merged, `git switch main && git pull` before starting PR-B.

---

# PR-B — Primitive component library

_The approved building blocks (spec §9). Screens compose these; agents never re-invent them. Every data component ships loading (skeleton), empty, and inline error states._

## Task B0: Branch + dependencies + `cn` helper + barrel

**Files:**
- Create: `frontend/src/lib/cn.ts`
- Create: `frontend/src/components/index.ts` (barrel — appended per task)

- [ ] **Step 1: Branch off main for PR-B** (F3a merged first; **M** = the F3b issue created in Task A0)

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k
git switch main && git pull -q
git switch -c feat/M-f3-primitives
```

- [ ] **Step 2: Install component deps**

```bash
cd frontend
npm install clsx sonner @phosphor-icons/react \
  @radix-ui/react-dialog @radix-ui/react-tabs \
  @radix-ui/react-tooltip @radix-ui/react-select
```

- [ ] **Step 3: `frontend/src/lib/cn.ts`** (tiny className joiner — no `tailwind-merge`; we don't need class-conflict resolution for a hand-authored primitive set):

```ts
import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
```

- [ ] **Step 4: Seed the barrel** `frontend/src/components/index.ts`:

```ts
// Primitive component library — the approved building blocks (spec §9).
// Screens import from here; do not re-invent these.
export {}; // exports are appended as each primitive lands
```

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/lib/cn.ts frontend/src/components/index.ts
git commit -m "chore: add primitive deps (radix, sonner, phosphor, clsx) + cn helper"
```

---

## Task B1: Button

**Files:**
- Create: `frontend/src/components/Button.tsx`, `frontend/src/components/Button.test.tsx`
- Modify: `frontend/src/components/index.ts`

Variants: `primary` (ink pill — the one max-contrast moment) and `ghost` (outline). Press `scale(0.97)`; token easing + micro duration; a11y focus ring in accent.

- [ ] **Step 1: Write the failing test** — `Button.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { Button } from "./Button";

test("renders label and fires onClick", async () => {
  const onClick = vi.fn();
  render(<Button onClick={onClick}>Run it</Button>);
  const btn = screen.getByRole("button", { name: "Run it" });
  btn.click();
  expect(onClick).toHaveBeenCalledOnce();
});

test("primary is the default variant; ghost opts out", () => {
  const { rerender } = render(<Button>Go</Button>);
  expect(screen.getByRole("button")).toHaveAttribute("data-variant", "primary");
  rerender(<Button variant="ghost">Go</Button>);
  expect(screen.getByRole("button")).toHaveAttribute("data-variant", "ghost");
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- Button` → FAIL.

- [ ] **Step 3: Implement `Button.tsx`**

```tsx
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../lib/cn";

type Variant = "primary" | "ghost";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const base =
  "inline-flex items-center gap-2 rounded-pill px-5 py-2.5 text-sm font-medium " +
  "border transition-[transform,background-color,border-color] " +
  "duration-[var(--dur-micro)] ease-editorial active:scale-[0.97] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent " +
  "disabled:opacity-50 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-paper border-transparent hover:bg-black",
  ghost: "bg-transparent text-ink border-hairline-strong hover:border-ink",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ variant = "primary", className, ...props }, ref) {
    return (
      <button
        ref={ref}
        data-variant={variant}
        className={cn(base, variants[variant], className)}
        {...props}
      />
    );
  },
);
```

- [ ] **Step 4: Export from the barrel** — append to `frontend/src/components/index.ts`:

```ts
export { Button, type ButtonProps } from "./Button";
```

- [ ] **Step 5: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- Button && npm run lint && npm run typecheck
git add frontend/src/components/Button.tsx frontend/src/components/Button.test.tsx frontend/src/components/index.ts
git commit -m "feat: Button primitive (ink pill / ghost, press scale, focus ring)"
```

---

## Task B2: Form fields — Input, Textarea, Select

**Files:**
- Create: `frontend/src/components/Field.tsx` (shared label/error wrapper)
- Create: `frontend/src/components/Input.tsx`, `frontend/src/components/Textarea.tsx`, `frontend/src/components/Select.tsx`
- Create: `frontend/src/components/fields.test.tsx`
- Modify: `frontend/src/components/index.ts`

Convention (spec §9): label above, error below, `gap-8`(→ `gap-2` at the 4px base = 8px). Inline error is the field's error state.

- [ ] **Step 1: Write the failing test** — `fields.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Input } from "./Input";
import { Textarea } from "./Textarea";
import { Select } from "./Select";

test("Input shows label and inline error, links them via aria", () => {
  render(<Input label="Model" error="required" defaultValue="" />);
  const input = screen.getByLabelText("Model");
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByText("required")).toBeInTheDocument();
});

test("Textarea renders its label", () => {
  render(<Textarea label="Prompt" />);
  expect(screen.getByLabelText("Prompt")).toBeInTheDocument();
});

test("Select renders options and its label", () => {
  render(
    <Select label="Language" defaultValue="en">
      <option value="en">English</option>
      <option value="uk">Ukrainian</option>
    </Select>,
  );
  expect(screen.getByLabelText("Language")).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Ukrainian" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- fields` → FAIL.

- [ ] **Step 3: Implement `Field.tsx`** (shared chrome; uses `useId` to link label/control/error)

```tsx
import { type ReactNode } from "react";

export interface FieldChrome {
  label?: string;
  error?: string;
}

export function FieldShell({
  id,
  label,
  error,
  children,
}: FieldChrome & { id: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
        </label>
      )}
      {children}
      {error && (
        <p id={`${id}-error`} className="font-mono text-xs text-accent-ink">
          {error}
        </p>
      )}
    </div>
  );
}

export const controlBase =
  "rounded-sm border border-hairline-strong bg-surface px-3 py-2 text-sm " +
  "text-ink placeholder:text-ink-faint transition-colors " +
  "duration-[var(--dur-micro)] ease-editorial " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent " +
  "aria-[invalid=true]:border-accent-ink";
```

- [ ] **Step 4: Implement `Input.tsx`**

```tsx
import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { cn } from "../lib/cn";
import { FieldShell, controlBase, type FieldChrome } from "./Field";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & FieldChrome;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, className, id, ...props },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell id={fieldId} label={label} error={error}>
      <input
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${fieldId}-error` : undefined}
        className={cn(controlBase, className)}
        {...props}
      />
    </FieldShell>
  );
});
```

- [ ] **Step 5: Implement `Textarea.tsx`**

```tsx
import { forwardRef, useId, type TextareaHTMLAttributes } from "react";
import { cn } from "../lib/cn";
import { FieldShell, controlBase, type FieldChrome } from "./Field";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> &
  FieldChrome;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ label, error, className, id, ...props }, ref) {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldShell id={fieldId} label={label} error={error}>
        <textarea
          ref={ref}
          id={fieldId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${fieldId}-error` : undefined}
          className={cn(controlBase, "min-h-24 resize-y", className)}
          {...props}
        />
      </FieldShell>
    );
  },
);
```

- [ ] **Step 6: Implement `Select.tsx`** (native `<select>` — Radix Select is reserved for rich menus; a native control is the least code for a labeled dropdown and fully accessible)

```tsx
import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import { cn } from "../lib/cn";
import { FieldShell, controlBase, type FieldChrome } from "./Field";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & FieldChrome;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, className, id, children, ...props },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell id={fieldId} label={label} error={error}>
      <select
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        className={cn(controlBase, "appearance-none pr-8", className)}
        {...props}
      >
        {children}
      </select>
    </FieldShell>
  );
});
```

- [ ] **Step 7: Export from the barrel** — append:

```ts
export { Input, type InputProps } from "./Input";
export { Textarea, type TextareaProps } from "./Textarea";
export { Select, type SelectProps } from "./Select";
```

- [ ] **Step 8: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- fields && npm run lint && npm run typecheck
git add frontend/src/components/Field.tsx frontend/src/components/Input.tsx frontend/src/components/Textarea.tsx frontend/src/components/Select.tsx frontend/src/components/fields.test.tsx frontend/src/components/index.ts
git commit -m "feat: form field primitives (Input/Textarea/Select, label + inline error)"
```

---

## Task B3: Card, Skeleton, ErrorState, EmptyState (the states kit)

**Files:**
- Create: `frontend/src/components/Card.tsx`, `frontend/src/components/Skeleton.tsx`, `frontend/src/components/ErrorState.tsx`, `frontend/src/components/EmptyState.tsx`
- Create: `frontend/src/components/states.test.tsx`
- Modify: `frontend/src/components/index.ts`

These are the mandatory loading/empty/error trio (spec §9). `Card` is the elevation primitive (hairline + 12px radius; no nested cards).

- [ ] **Step 1: Write the failing test** — `states.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { Card } from "./Card";
import { Skeleton } from "./Skeleton";
import { ErrorState } from "./ErrorState";
import { EmptyState } from "./EmptyState";

test("Card renders children in a region", () => {
  render(<Card aria-label="panel">body</Card>);
  expect(screen.getByLabelText("panel")).toHaveTextContent("body");
});

test("Skeleton exposes an accessible busy status", () => {
  render(<Skeleton />);
  expect(screen.getByRole("status")).toBeInTheDocument();
});

test("ErrorState shows message and a retry action", () => {
  const onRetry = vi.fn();
  render(<ErrorState message="Load failed" onRetry={onRetry} />);
  screen.getByRole("button", { name: /retry/i }).click();
  expect(onRetry).toHaveBeenCalledOnce();
});

test("EmptyState shows title and description", () => {
  render(<EmptyState title="No recordings" description="Drop audio to start." />);
  expect(screen.getByText("No recordings")).toBeInTheDocument();
  expect(screen.getByText("Drop audio to start.")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- states` → FAIL.

- [ ] **Step 3: Implement `Card.tsx`**

```tsx
import { type HTMLAttributes } from "react";
import { cn } from "../lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-md border border-hairline bg-surface",
        "shadow-[var(--shadow-soft)]",
        className,
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 4: Implement `Skeleton.tsx`** (matches layout via className; `animate-pulse` auto-stops under reduced motion via the tokens.css kill-switch)

```tsx
import { cn } from "../lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn("animate-pulse rounded-sm bg-sink", className)}
    />
  );
}
```

- [ ] **Step 5: Implement `ErrorState.tsx`**

```tsx
import { WarningCircle } from "@phosphor-icons/react";
import { Button } from "./Button";

export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-md border border-hairline bg-surface p-6">
      <WarningCircle size={22} className="text-accent-ink" weight="duotone" />
      <p className="text-sm text-ink-soft">{message}</p>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Implement `EmptyState.tsx`**

```tsx
import { type ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-hairline-strong bg-surface px-6 py-14 text-center">
      {icon && <div className="text-ink-faint">{icon}</div>}
      <h3 className="text-lg text-ink">{title}</h3>
      {description && (
        <p className="max-w-[40ch] text-sm text-ink-soft">{description}</p>
      )}
      {action}
    </div>
  );
}
```

- [ ] **Step 7: Export from the barrel** — append:

```ts
export { Card } from "./Card";
export { Skeleton } from "./Skeleton";
export { ErrorState, type ErrorStateProps } from "./ErrorState";
export { EmptyState, type EmptyStateProps } from "./EmptyState";
```

- [ ] **Step 8: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- states && npm run lint && npm run typecheck
git add frontend/src/components/Card.tsx frontend/src/components/Skeleton.tsx frontend/src/components/ErrorState.tsx frontend/src/components/EmptyState.tsx frontend/src/components/states.test.tsx frontend/src/components/index.ts
git commit -m "feat: Card + loading/empty/error state primitives"
```

---

## Task B4: Table

**Files:**
- Create: `frontend/src/components/Table.tsx`, `frontend/src/components/Table.test.tsx`
- Modify: `frontend/src/components/index.ts`

Compositional styled wrappers around native table elements (mono numerics, hairline rows, hover tint — matches the preview's hardware table).

- [ ] **Step 1: Write the failing test** — `Table.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Table, THead, TBody, TR, TH, TD } from "./Table";

test("renders a semantic table with mono numeric cells", () => {
  render(
    <Table>
      <THead>
        <TR>
          <TH>Model</TH>
          <TH>Disk</TH>
        </TR>
      </THead>
      <TBody>
        <TR>
          <TD mono>large-v3</TD>
          <TD mono num>
            3 GB
          </TD>
        </TR>
      </TBody>
    </Table>,
  );
  expect(screen.getByRole("table")).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "3 GB" })).toHaveClass("font-mono");
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- Table` → FAIL.

- [ ] **Step 3: Implement `Table.tsx`**

```tsx
import { type HTMLAttributes, type TdHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <table
      className={cn("w-full border-collapse text-sm", className)}
      {...props}
    />
  );
}

export function THead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />;
}

export function TBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />;
}

export function TR({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr className={cn("hover:[&>td]:bg-paper", className)} {...props} />
  );
}

export function TH({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "border-b border-hairline-strong px-4 pb-3 text-left font-mono",
        "text-xs font-medium uppercase tracking-[0.08em] text-ink-faint",
        className,
      )}
      {...props}
    />
  );
}

interface TDProps extends TdHTMLAttributes<HTMLTableCellElement> {
  mono?: boolean;
  num?: boolean;
}

export function TD({ mono, num, className, ...props }: TDProps) {
  return (
    <td
      className={cn(
        "border-b border-hairline px-4 py-3.5",
        mono && "font-mono",
        num && "text-ink-soft",
        className,
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 4: Export from the barrel** — append:

```ts
export { Table, THead, TBody, TR, TH, TD } from "./Table";
```

- [ ] **Step 5: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- Table && npm run lint && npm run typecheck
git add frontend/src/components/Table.tsx frontend/src/components/Table.test.tsx frontend/src/components/index.ts
git commit -m "feat: Table primitive (mono numerics, hairline rows, hover tint)"
```

---

## Task B5: StatusPill, ProgressBar, QueueRow

**Files:**
- Create: `frontend/src/components/StatusPill.tsx`, `frontend/src/components/ProgressBar.tsx`, `frontend/src/components/QueueRow.tsx`
- Create: `frontend/src/components/queue.test.tsx`
- Modify: `frontend/src/components/index.ts`

StatusPill (mono uppercase): `run`→accent-wash, `done`→sink, `queued`→outline. QueueRow composes an icon badge + title + mono sub + StatusPill (the preview's queue row).

- [ ] **Step 1: Write the failing test** — `queue.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { StatusPill } from "./StatusPill";
import { ProgressBar } from "./ProgressBar";
import { QueueRow } from "./QueueRow";

test("StatusPill carries its status as a data attribute", () => {
  render(<StatusPill status="run">transcribing</StatusPill>);
  const pill = screen.getByText("transcribing");
  expect(pill).toHaveAttribute("data-status", "run");
});

test("ProgressBar exposes value via ARIA and clamps to 0..100", () => {
  render(<ProgressBar value={140} />);
  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveAttribute("aria-valuenow", "100");
});

test("QueueRow shows title, mono sub, and status", () => {
  render(
    <QueueRow
      title="Judicial Review — parts 1–3"
      sub="3 recordings · 02:41:12 · large-v3"
      status="run"
      statusLabel="transcribing"
    />,
  );
  expect(screen.getByText(/Judicial Review/)).toBeInTheDocument();
  expect(screen.getByText("transcribing")).toHaveAttribute("data-status", "run");
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- queue` → FAIL.

- [ ] **Step 3: Implement `StatusPill.tsx`**

```tsx
import { type ReactNode } from "react";
import { cn } from "../lib/cn";

export type Status = "run" | "done" | "queued";

const styles: Record<Status, string> = {
  run: "bg-accent-wash text-accent-ink",
  done: "bg-sink text-ink-soft",
  queued: "border border-hairline-strong text-ink-faint",
};

export function StatusPill({
  status,
  children,
}: {
  status: Status;
  children: ReactNode;
}) {
  return (
    <span
      data-status={status}
      className={cn(
        "rounded-pill px-2.5 py-1 font-mono text-[10.5px] font-medium uppercase tracking-[0.06em]",
        styles[status],
      )}
    >
      {children}
    </span>
  );
}
```

- [ ] **Step 4: Implement `ProgressBar.tsx`** (accent on sink; animates `transform` not width — the fill is scaled)

```tsx
export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={clamped}
      className="h-1 w-full overflow-hidden rounded-sm bg-sink"
    >
      <div
        className="h-full origin-left rounded-sm bg-accent transition-transform duration-[var(--dur)] ease-editorial"
        style={{ transform: `scaleX(${clamped / 100})` }}
      />
    </div>
  );
}
```

- [ ] **Step 5: Implement `QueueRow.tsx`**

```tsx
import { type ReactNode } from "react";
import { StatusPill, type Status } from "./StatusPill";

export interface QueueRowProps {
  title: string;
  sub: string;
  status: Status;
  statusLabel: string;
  icon?: ReactNode;
}

export function QueueRow({ title, sub, status, statusLabel, icon }: QueueRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-sm border border-hairline bg-paper px-3 py-2.5">
      {icon && (
        <div className="grid h-8 w-8 place-items-center rounded-sm border border-hairline bg-surface text-ink-soft">
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-ink">{title}</div>
        <div className="truncate font-mono text-[11px] text-ink-faint">{sub}</div>
      </div>
      <div className="flex-1" />
      <StatusPill status={status}>{statusLabel}</StatusPill>
    </div>
  );
}
```

- [ ] **Step 6: Export from the barrel** — append:

```ts
export { StatusPill, type Status } from "./StatusPill";
export { ProgressBar } from "./ProgressBar";
export { QueueRow, type QueueRowProps } from "./QueueRow";
```

- [ ] **Step 7: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- queue && npm run lint && npm run typecheck
git add frontend/src/components/StatusPill.tsx frontend/src/components/ProgressBar.tsx frontend/src/components/QueueRow.tsx frontend/src/components/queue.test.tsx frontend/src/components/index.ts
git commit -m "feat: StatusPill + ProgressBar + QueueRow primitives"
```

---

## Task B6: Tabs (Radix)

**Files:**
- Create: `frontend/src/components/Tabs.tsx`, `frontend/src/components/Tabs.test.tsx`
- Modify: `frontend/src/components/index.ts`

2px accent underline on the active trigger (spec §9). Re-exports Radix parts with tokenized styling.

- [ ] **Step 1: Write the failing test** — `Tabs.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./Tabs";

test("shows the active tab's panel and switches on click", () => {
  render(
    <Tabs defaultValue="raw">
      <TabsList>
        <TabsTrigger value="raw">Raw</TabsTrigger>
        <TabsTrigger value="summary">Summary</TabsTrigger>
      </TabsList>
      <TabsContent value="raw">raw body</TabsContent>
      <TabsContent value="summary">summary body</TabsContent>
    </Tabs>,
  );
  expect(screen.getByText("raw body")).toBeInTheDocument();
  screen.getByRole("tab", { name: "Summary" }).click();
  expect(screen.getByText("summary body")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- Tabs` → FAIL.

- [ ] **Step 3: Implement `Tabs.tsx`**

```tsx
import * as RadixTabs from "@radix-ui/react-tabs";
import { type ComponentProps } from "react";
import { cn } from "../lib/cn";

export const Tabs = RadixTabs.Root;

export function TabsList({ className, ...props }: ComponentProps<typeof RadixTabs.List>) {
  return (
    <RadixTabs.List
      className={cn("flex gap-6 border-b border-hairline", className)}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.Trigger>) {
  return (
    <RadixTabs.Trigger
      className={cn(
        "-mb-px border-b-2 border-transparent py-2 text-sm text-ink-soft",
        "transition-colors duration-[var(--dur-micro)] ease-editorial hover:text-ink",
        "data-[state=active]:border-accent data-[state=active]:text-ink",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.Content>) {
  return <RadixTabs.Content className={cn("pt-5", className)} {...props} />;
}
```

- [ ] **Step 4: Export from the barrel** — append:

```ts
export { Tabs, TabsList, TabsTrigger, TabsContent } from "./Tabs";
```

- [ ] **Step 5: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- Tabs && npm run lint && npm run typecheck
git add frontend/src/components/Tabs.tsx frontend/src/components/Tabs.test.tsx frontend/src/components/index.ts
git commit -m "feat: Tabs primitive (Radix, 2px accent underline)"
```

---

## Task B7: Tooltip (Radix)

**Files:**
- Create: `frontend/src/components/Tooltip.tsx`, `frontend/src/components/Tooltip.test.tsx`
- Modify: `frontend/src/components/index.ts`

125ms open (subsequent instant via Radix `Provider` `skipDelayDuration`). Origin-aware is Radix's default (content animates from the trigger side).

- [ ] **Step 1: Write the failing test** — `Tooltip.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Tooltip } from "./Tooltip";

test("renders the trigger; tooltip content is wired via aria", () => {
  render(
    <Tooltip label="Whisper model size">
      <button>large-v3</button>
    </Tooltip>,
  );
  // trigger is present; Radix mounts content on hover/focus (delayed),
  // so we assert the trigger renders and is describable.
  expect(screen.getByRole("button", { name: "large-v3" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- Tooltip` → FAIL.

- [ ] **Step 3: Implement `Tooltip.tsx`**

```tsx
import * as RadixTooltip from "@radix-ui/react-tooltip";
import { type ReactNode } from "react";

export function Tooltip({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <RadixTooltip.Provider delayDuration={125} skipDelayDuration={0}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            sideOffset={6}
            className="rounded-sm bg-ink px-2 py-1 font-mono text-[11px] text-paper shadow-[var(--shadow-soft)]"
          >
            {label}
            <RadixTooltip.Arrow className="fill-ink" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}
```

- [ ] **Step 4: Export from the barrel** — append:

```ts
export { Tooltip } from "./Tooltip";
```

- [ ] **Step 5: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- Tooltip && npm run lint && npm run typecheck
git add frontend/src/components/Tooltip.tsx frontend/src/components/Tooltip.test.tsx frontend/src/components/index.ts
git commit -m "feat: Tooltip primitive (Radix, 125ms open)"
```

---

## Task B8: Modal + Drawer (Radix Dialog)

**Files:**
- Create: `frontend/src/components/Modal.tsx`, `frontend/src/components/Drawer.tsx`, `frontend/src/components/dialog.test.tsx`
- Modify: `frontend/src/components/index.ts`

Both wrap Radix Dialog (focus-trapped, a11y). Modal keeps center; Drawer slides from the right. Enter/exit animate `transform` + `opacity` via CSS keyframes gated on Radix `data-state`; the tokens.css reduced-motion kill-switch disables them. Enter `--dur-lg`, exit ~0.8×.

- [ ] **Step 1: Add the keyframes** — append to `frontend/src/design/tokens.css` (inside a new `@layer components` block at the end of the file):

```css
@layer components {
  @keyframes overlay-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  @keyframes modal-in {
    from { opacity: 0; transform: translate(-50%, -48%) scale(0.96); }
    to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  }
  @keyframes drawer-in {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
}
```

- [ ] **Step 2: Write the failing test** — `dialog.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Modal } from "./Modal";
import { Drawer } from "./Drawer";

test("Modal renders its content when open", () => {
  render(
    <Modal open title="Delete set?" onOpenChange={() => {}}>
      <p>This cannot be undone.</p>
    </Modal>,
  );
  expect(screen.getByRole("dialog")).toHaveTextContent("Delete set?");
  expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
});

test("Drawer renders its content when open", () => {
  render(
    <Drawer open title="Configuration" onOpenChange={() => {}}>
      <p>stage flags</p>
    </Drawer>,
  );
  expect(screen.getByRole("dialog")).toHaveTextContent("Configuration");
});
```

- [ ] **Step 3: Run, verify it fails** — `cd frontend && npm test -- dialog` → FAIL.

- [ ] **Step 4: Implement `Modal.tsx`**

```tsx
import * as Dialog from "@radix-ui/react-dialog";
import { type ReactNode } from "react";

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
}

export function Modal({ open, onOpenChange, title, children }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-ink/40 [animation:overlay-in_var(--dur)_var(--ease-editorial)]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-[min(92vw,480px)] -translate-x-1/2 -translate-y-1/2 rounded-md border border-hairline bg-surface p-6 shadow-[var(--shadow-soft)] [animation:modal-in_var(--dur-lg)_var(--ease-editorial)]">
          <Dialog.Title className="text-xl text-ink">{title}</Dialog.Title>
          <div className="mt-3 text-sm text-ink-soft">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

- [ ] **Step 5: Implement `Drawer.tsx`**

```tsx
import * as Dialog from "@radix-ui/react-dialog";
import { type ReactNode } from "react";

export interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
}

export function Drawer({ open, onOpenChange, title, children }: DrawerProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-ink/40 [animation:overlay-in_var(--dur)_var(--ease-editorial)]" />
        <Dialog.Content className="fixed inset-y-0 right-0 w-[min(92vw,420px)] border-l border-hairline bg-surface p-6 shadow-[var(--shadow-soft)] [animation:drawer-in_var(--dur-lg)_var(--ease-editorial)]">
          <Dialog.Title className="text-xl text-ink">{title}</Dialog.Title>
          <div className="mt-4 text-sm text-ink-soft">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

- [ ] **Step 6: Export from the barrel** — append:

```ts
export { Modal, type ModalProps } from "./Modal";
export { Drawer, type DrawerProps } from "./Drawer";
```

- [ ] **Step 7: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- dialog && npm run lint && npm run typecheck
git add frontend/src/components/Modal.tsx frontend/src/components/Drawer.tsx frontend/src/components/dialog.test.tsx frontend/src/components/index.ts frontend/src/design/tokens.css
git commit -m "feat: Modal + Drawer primitives (Radix Dialog, transform/opacity motion)"
```

> Note: this commit touches `tokens.css` (adding `@layer components` keyframes only — no token value edits). Since PR-A has not merged when working sequentially, this is fine (same feature line). If PR-A is already merged, the keyframe addition is non-frozen (it adds motion utilities, not tokens) but still route it through this PR's normal review.

---

## Task B9: Toast (Sonner)

**Files:**
- Create: `frontend/src/components/Toast.tsx`, `frontend/src/components/Toast.test.tsx`
- Modify: `frontend/src/components/index.ts`

Sonner-style toaster (spec §9), tokenized. Re-export `toast()` for callers; export `<Toaster>` to mount once at the app root.

- [ ] **Step 1: Write the failing test** — `Toast.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { Toaster, toast } from "./Toast";

test("Toaster mounts and toast() is callable", () => {
  const { container } = render(<Toaster />);
  expect(container).toBeInTheDocument();
  expect(typeof toast).toBe("function");
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- Toast` → FAIL.

- [ ] **Step 3: Implement `Toast.tsx`**

```tsx
import { Toaster as SonnerToaster, toast } from "sonner";

export { toast };

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "rounded-md border border-hairline bg-surface text-sm text-ink shadow-[var(--shadow-soft)]",
          description: "text-ink-soft",
        },
      }}
    />
  );
}
```

- [ ] **Step 4: Export from the barrel** — append:

```ts
export { Toaster, toast } from "./Toast";
```

- [ ] **Step 5: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- Toast && npm run lint && npm run typecheck
git add frontend/src/components/Toast.tsx frontend/src/components/Toast.test.tsx frontend/src/components/index.ts
git commit -m "feat: Toast primitive (Sonner, tokenized)"
```

---

## Task B10: Ship PR-B

- [ ] **Step 1: Full gate** — `cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build` → all green. (`npm run format:write` first if needed.)

- [ ] **Step 2: Push + open PR**

```bash
git push -u origin feat/M-f3-primitives
gh pr create --base main --title "F3b: primitive component library" \
  --body "Closes #M. Builds the spec §9 primitives — Button, form fields, Card, Table, StatusPill, ProgressBar, QueueRow, Tabs, Tooltip, Modal, Drawer, Toast, and the loading/empty/error kit (Skeleton, ErrorState, EmptyState) — each tokenized, reduced-motion-safe, and unit-tested. Depends on F3a."
```

- [ ] **Step 3: Hand off for review** — post the PR link and **stop**. The user
  reviews in GitHub and squash-merges. Do not merge from the CLI. Once the user
  confirms F3b is merged, `git switch main && git pull` before starting PR-C.

---

# PR-C — Reference screen

_Assembles the primitives into the queue/monitor screen from the approved preview — the end-to-end proof the system coheres (acceptance criterion #5)._

## Task C0: Branch

Branch off main after PR-B merges (**P** = the F3c issue created in Task A0):

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k
git switch main && git pull -q
git switch -c feat/P-f3-reference-screen
```

---

## Task C1: Queue/monitor screen

**Files:**
- Create: `frontend/src/screens/QueueMonitor.tsx`, `frontend/src/screens/QueueMonitor.test.tsx`

Demonstrates the mandatory trio: `state="loading"` → skeletons, `state="empty"` → `EmptyState`, `state="error"` → `ErrorState`, `state="ready"` → the queue rows + progress. The page-load stagger is gated by `useReducedMotion`.

- [ ] **Step 1: Write the failing test** — `QueueMonitor.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { QueueMonitor, type QueueItem } from "./QueueMonitor";
import { setReducedMotion } from "../test/matchMedia";

const items: QueueItem[] = [
  {
    id: "1",
    title: "Judicial Review — parts 1–3",
    sub: "3 recordings · 02:41:12 · large-v3",
    status: "run",
    statusLabel: "transcribing",
    progress: 64,
  },
];

test("ready state renders the queue rows", () => {
  render(<QueueMonitor state="ready" items={items} />);
  expect(screen.getByText(/Judicial Review/)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "64");
});

test("loading state renders skeletons", () => {
  render(<QueueMonitor state="loading" items={[]} />);
  expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
});

test("empty state renders the EmptyState", () => {
  render(<QueueMonitor state="empty" items={[]} />);
  expect(screen.getByText(/no recordings/i)).toBeInTheDocument();
});

test("error state renders the ErrorState", () => {
  render(<QueueMonitor state="error" items={[]} />);
  expect(screen.getByText(/couldn't load/i)).toBeInTheDocument();
});

test("reduced motion removes the staggered reveal", () => {
  setReducedMotion(true);
  const { container } = render(<QueueMonitor state="ready" items={items} />);
  expect(container.querySelector("[data-reveal]")).toBeNull();
  setReducedMotion(false);
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- QueueMonitor` → FAIL.

- [ ] **Step 3: Implement `QueueMonitor.tsx`**

```tsx
import { WaveSine } from "@phosphor-icons/react";
import {
  Card,
  EmptyState,
  ErrorState,
  ProgressBar,
  QueueRow,
  Skeleton,
  type Status,
} from "../components";
import { useReducedMotion } from "../theme/useReducedMotion";

export interface QueueItem {
  id: string;
  title: string;
  sub: string;
  status: Status;
  statusLabel: string;
  progress?: number;
}

export type QueueState = "loading" | "empty" | "error" | "ready";

export interface QueueMonitorProps {
  state: QueueState;
  items: QueueItem[];
  onRetry?: () => void;
}

export function QueueMonitor({ state, items, onRetry }: QueueMonitorProps) {
  const reduced = useReducedMotion();
  const reveal = reduced ? {} : { "data-reveal": true };

  return (
    <main className="mx-auto max-w-[var(--maxw)] px-8 py-16">
      <header className="mb-10" {...reveal}>
        <p className="mb-3 inline-flex items-center gap-2 font-mono text-[11.5px] font-medium uppercase tracking-[0.14em] text-ink-faint">
          Pipeline · monitor
        </p>
        <h1 className="text-5xl leading-[0.98] text-ink">
          The machine keeps the <em className="not-italic text-accent-ink italic">record</em>.
        </h1>
      </header>

      <Card className="p-4">
        {state === "loading" && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        )}

        {state === "empty" && (
          <EmptyState
            title="No recordings yet"
            description="Drop audio into a set to start the pipeline."
            icon={<WaveSine size={28} weight="duotone" />}
          />
        )}

        {state === "error" && (
          <ErrorState message="Couldn't load the queue." onRetry={onRetry} />
        )}

        {state === "ready" && (
          <div className="flex flex-col gap-3">
            {items.map((item) => (
              <div key={item.id} className="flex flex-col gap-2">
                <QueueRow
                  title={item.title}
                  sub={item.sub}
                  status={item.status}
                  statusLabel={item.statusLabel}
                  icon={<WaveSine size={15} />}
                />
                {item.progress !== undefined && (
                  <ProgressBar value={item.progress} />
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </main>
  );
}
```

- [ ] **Step 4: Run tests + lint + types, verify pass. Commit**

```bash
cd frontend && npm test -- QueueMonitor && npm run lint && npm run typecheck
git add frontend/src/screens/QueueMonitor.tsx frontend/src/screens/QueueMonitor.test.tsx
git commit -m "feat: queue/monitor reference screen (loading/empty/error/ready)"
```

---

## Task C2: Wire the screen into the app root

**Files:**
- Modify: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`

Mount `ThemeProvider` + `Toaster` at the root and render `QueueMonitor` with sample-but-domain-real data (no placeholder "John Doe" / "Acme" — banned by §10).

- [ ] **Step 1: Update the app test** — replace `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";

test("renders the queue monitor with a live item", () => {
  render(<App />);
  expect(screen.getByText(/Judicial Review/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run, verify it fails** — `cd frontend && npm test -- App` → FAIL.

- [ ] **Step 3: Implement `App.tsx`**

```tsx
import { Toaster } from "./components";
import { QueueMonitor, type QueueItem } from "./screens/QueueMonitor";
import { ThemeProvider } from "./theme/ThemeProvider";

const SAMPLE: QueueItem[] = [
  {
    id: "1",
    title: "Judicial Review — parts 1–3",
    sub: "3 recordings · 02:41:12 · large-v3",
    status: "run",
    statusLabel: "transcribing",
    progress: 64,
  },
  {
    id: "2",
    title: "Standing & ripeness — seminar",
    sub: "1 recording · 00:52:08 · summary.md ready",
    status: "done",
    statusLabel: "done",
  },
  {
    id: "3",
    title: "Commerce clause — guest lecture",
    sub: "2 recordings · 01:18:44 · queued #3",
    status: "queued",
    statusLabel: "queued",
  },
];

export default function App() {
  return (
    <ThemeProvider>
      <QueueMonitor state="ready" items={SAMPLE} />
      <Toaster />
    </ThemeProvider>
  );
}
```

- [ ] **Step 4: Run tests + lint + types + build, verify pass. Commit**

```bash
cd frontend && npm test -- App && npm run lint && npm run typecheck && npm run build
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: mount theme + toaster + reference screen at the app root"
```

---

## Task C3: Ship PR-C + visual check

- [ ] **Step 1: Manual visual check against the preview** — run the dev server and compare to `docs/design/steno10k-style-preview.html`:

```bash
cd frontend && npm run dev
```

Confirm: paper canvas (not white), evergreen accent, mono sub-lines, hairline borders, the staggered reveal on load, dark theme flips cleanly (toggle via devtools: `document.documentElement.dataset.theme = "dark"`). Fix any drift, then stop the server.

- [ ] **Step 2: Full gate** — `cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build` → all green.

- [ ] **Step 3: Push + open PR**

```bash
git push -u origin feat/P-f3-reference-screen
gh pr create --base main --title "F3c: queue/monitor reference screen" \
  --body "Closes #P. Assembles the F3b primitives into the queue/monitor reference screen (loading/empty/error/ready), matching the approved preview — the end-to-end proof of the design system. Depends on F3b."
```

- [ ] **Step 4: Hand off for review** — post the PR link and **stop**. The user
  reviews in GitHub and squash-merges. Do not merge from the CLI.

- [ ] **Step 5: After the user merges, verify `main` is green** (CI + GHCR
  publish) and that the epic's three sub-issue checkboxes are all closed.

---

## Self-review notes (coverage vs F3 spec acceptance criteria)

- **AC#1 — token file (`@theme` light + dark) matches §4:** Task A2 (`tokens.css`), guarded by `tokens.test.ts`. Names follow `docs/standards/ui-design-system.md` (`--color-*`, `--radius-*`, `--font-*`, `--ease-editorial`); values verbatim from the preview.
- **AC#2 — `docs/standards/ui-design-system.md` distills §5–§11, linked from `AGENTS.md`:** **already satisfied** (the doc exists and `AGENTS.md`/`CLAUDE.md` references it). No task needed; noted in the header.
- **AC#3 — primitives (§9) with loading/empty/error + motion, unit-tested (render + reduced-motion):** PR-B Tasks B1–B9 cover Button, Input/Select/Textarea, Card, Table, StatusPill, QueueRow, ProgressBar, Tabs, Toast, Modal/Drawer, Tooltip, EmptyState — plus the Skeleton/ErrorState/EmptyState trio (B3). Reduced-motion is tested via `useReducedMotion` (A4) and the reference-screen reveal test (C1); the global reduced-motion kill-switch lives in `tokens.css` (A2).
- **AC#4 — lint rule rejects raw hex + emoji, CI-enforced:** Task A5 (`eslint-rules/`), unit-tested with `RuleTester`, wired into `eslint.config.js` (the `frontend` CI job runs `npm run lint`).
- **AC#5 — reference screen assembled from primitives, matches the preview:** PR-C (Tasks C1–C3), with the manual visual check in C3.

**Deliberate deviations from spec §11 (documented, not omissions):**
- **Motion (Framer) not added.** The spec restricts springs to gesture/drag interactions; the primitive set has none. Modal/Drawer entrance uses CSS keyframes on Radix `data-state` (transform + opacity only), and the reduced-motion kill-switch disables them. Add Motion in a later PR when a real drag/gesture surface appears (e.g. a draggable queue reorder). This honors the prime directive "least code wins" without violating any motion rule.
- **`Select` uses a native `<select>`** rather than Radix Select — a labeled dropdown needs no custom popup; native is fully accessible and less code. Radix Select stays available (installed) for a future rich/searchable menu.

## Roadmap ahead

Per the F1 plan's roadmap, F3 is milestone 3. After this merges, the **fan-out** begins: the 8 stages onto the runner, the backend endpoint groups, and the frontend screens — each screen composing these primitives, coordinated by the F0 lock protocol. `tokens.css` and the primitive APIs are now frozen contracts; changes to them follow the contract-lock protocol in `AGENTS.md`.
