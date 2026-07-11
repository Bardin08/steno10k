# M0 — Repo Operating Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `steno10k` repo operating model (F0) end to end — structure, standards, CI/CD, Docker, GitHub Projects, agent rules — and land the landing page as the first proving PR.

**Architecture:** Monorepo: `backend/` (Python + FastAPI, `uv`), `frontend/` (React + TS), `landing/` (static GitHub Pages), `docs/`, `.github/`. One container serves the built SPA. Trunk-based git with branch protection, squash-merge, Conventional Commits. **This milestone ships only the guardrails and minimal scaffolds** — no domain models, no design tokens, no UI components, no real config. Those arrive in the F1/F2/F3 milestones when actual code is added.

**Tech Stack:** Python 3.12 · uv · ruff · mypy · pytest · FastAPI · Node 22 · React 19 · TypeScript · vitest · eslint · prettier · Docker · GitHub Actions · GHCR · GitHub Projects.

Source specs (in `docs/specs/`): F0 repo model, F1 contracts, F2 API, F3 design system. Reference: `docs/design/steno10k-style-preview.html` (approved style). Reusable code to port later lives in the `lecturemate10k` repo (parts bin) — **not** part of M0.

---

## Task 1: Repo skeleton, ignore rules, license

**Files:**
- Create: `.gitignore`, `.editorconfig`, `LICENSE`, plus dir scaffolding

- [ ] **Step 1: Create directory scaffolding**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k
mkdir -p backend/src/steno10k backend/tests frontend/src landing docs/standards docs/adr .github/workflows .github/ISSUE_TEMPLATE
touch docs/adr/.gitkeep
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
dist/
*.egg-info/
# Node
node_modules/
frontend/dist/
# Local data & secrets — NEVER commit
config.yaml
.env
data/
models/
.cache/
# OS/IDE
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 3: Write `.editorconfig`**

```ini
root = true
[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
[*.{py}]
indent_size = 4
[*.{ts,tsx,js,jsx,json,yml,yaml,css,html,md}]
indent_size = 2
```

- [ ] **Step 4: Write `LICENSE` (MIT)** — standard MIT text, copyright `2026 Vladyslav Bardin`.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: repo skeleton, gitignore, editorconfig, MIT license"
```

---

## Task 2: Human docs — README, CONTRIBUTING, CHANGELOG

**Files:**
- Create: `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`

- [ ] **Step 1: Write `README.md` skeleton** — one-line pitch ("The written word, on your own machine — local-first audio → transcript + summary"), what it is, quickstart (`docker compose up`), the 8-stage pipeline list, hardware table (from F1 §8 / preview), links to `docs/`. Concise.

- [ ] **Step 2: Write `CONTRIBUTING.md` (human-facing only)** — local setup, running backend/frontend/tests, the branch → PR → squash flow at a glance, where standards live (`docs/standards/` + `AGENTS.md`), how to open an issue. **No coding standards inline.**

- [ ] **Step 3: Write `CHANGELOG.md`**

```markdown
# Changelog

All notable changes are recorded here. Entries are generated on release from
Conventional Commits — do not edit by hand in feature PRs.

## [Unreleased]
```

- [ ] **Step 4: Commit**

```bash
git add README.md CONTRIBUTING.md CHANGELOG.md && git commit -m "docs: README, CONTRIBUTING, CHANGELOG skeletons"
```

---

## Task 3: Agent instructions — `AGENTS.md` + `CLAUDE.md` symlink + lock protocol

**Files:**
- Create: `AGENTS.md`, `CLAUDE.md` (symlink → `AGENTS.md`)

- [ ] **Step 1: Author `AGENTS.md` with care** — this is high-value; write it high-signal, concise, and tool-oriented. **Explicitly follow the humanlayer guidance** on writing a good CLAUDE.md — https://www.humanlayer.dev/blog/writing-a-good-claude-md and the principles in https://github.com/humanlayer/12-factor-agents. It is the single instruction file both Claude Code (`CLAUDE.md`) and other agents (`AGENTS.md`) read, so keep one source. Contents:
  - **Workflow:** one issue → one branch → one PR. Branch `<type>/<issue>-<slug>` (e.g. `feat/42-stage-transcribe`), no `#`.
  - **Commits:** Conventional Commits (`feat|fix|chore|docs|test|refactor|ci:`).
  - **Before pushing:** run `pre-commit run --all-files` + the relevant test subset locally.
  - **PRs:** open with `gh pr create`, link the issue (`Closes #N`), fill the template, concise description.
  - **Frozen contracts — do NOT edit in a fan-out PR:** `backend/src/steno10k/contracts/`, `backend/src/steno10k/api/` (OpenAPI DTOs), `frontend/src/design/tokens.css`, `docs/standards/`. (These are created in the F1/F2/F3 milestones; referenced here so the guardrail exists first.)
  - **Standards:** read `docs/standards/*` first — they are law.
  - **Parallel sessions:** use `git worktree` for isolation.

- [ ] **Step 2: Document the contract-change LOCK protocol (in `AGENTS.md`)** — a local, user-level coordination mechanism so concurrent sessions don't collide on shared contracts:
  - Before opening a "contract change" PR that touches a frozen contract, create a lock file at **`~/.claude/locks/steno10k/<contract>.lock.md`** (user-level, outside the repo).
  - The lock file **describes the change** (which contract, what's changing, the PR link/branch) so any other agent can decide whether it's impacted.
  - Every agent **checks `~/.claude/locks/steno10k/` before touching a frozen contract**; if an active lock covers its area, it **waits** until the lock is cleared (removed when the contract PR merges).
  - Locks are advisory coordination for local multi-session work, complementary to GitHub branch protection + CODEOWNERS.

- [ ] **Step 3: Create the `CLAUDE.md` symlink**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k && ln -s AGENTS.md CLAUDE.md
```
(Per-area `CLAUDE.md` files under `backend/`, `frontend/` may be added in later milestones if they prove useful — not now.)

- [ ] **Step 4: Verify the symlink resolves**

Run: `cat CLAUDE.md | head -3`
Expected: shows the top of `AGENTS.md`.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md CLAUDE.md && git commit -m "docs: agent instructions (AGENTS.md + CLAUDE.md) with contract-lock protocol"
```

---

## Task 4: Coding standards docs

**Files:**
- Create: `docs/standards/git.md`, `docs/standards/python.md`, `docs/standards/typescript.md`, `docs/standards/ui-design-system.md`

- [ ] **Step 1: `docs/standards/git.md`** — trunk-based model, branch naming, Conventional Commits table, squash-merge, the §3.2 coordination protocol + the lock-file mechanism (Task 3), required CI checks.

- [ ] **Step 2: `docs/standards/python.md`** — `from __future__ import annotations`; modern types (`X | None`, `list[X]`); ruff (lint+format) + mypy strict-ish + pytest; prefer stdlib/vetted deps; least code / DRY / SOLID / KISS; narrow exceptions except at documented isolation boundaries.

- [ ] **Step 3: `docs/standards/typescript.md`** — strict `tsconfig`; eslint + prettier; function components; least code; no `any`; import from the primitive component library, don't re-invent; icons from Phosphor, never emoji.

- [ ] **Step 4: `docs/standards/ui-design-system.md`** (distilled from F3) — token names (will reference `frontend/src/design/tokens.css`, added in the F3 milestone), type-triad rules (Instrument Serif display / Geist UI / Geist Mono machine-truth), motion numbers (`ease-out`, `<300ms`, transform+opacity, `scale(0.97)` press, no bounce, reduced-motion), color rules (neutral + one evergreen accent, contrast floors), layout (asymmetry, hairline depth), mandatory component states (loading/empty/error), and the **ban list**. End with the pass/fail test.

- [ ] **Step 5: Commit**

```bash
git add docs/standards && git commit -m "docs: coding + design standards (git, python, typescript, ui)"
```

---

## Task 5: Backend scaffold (uv, ruff, mypy, pytest, one passing test)

**Files:**
- Create: `backend/pyproject.toml`, `backend/src/steno10k/__init__.py`, `backend/src/steno10k/version.py`, `backend/tests/test_version.py`

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "steno10k"
version = "0.1.0"
description = "Local-first audio -> transcript + summary pipeline"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "pydantic>=2.9"]

[dependency-groups]
dev = ["ruff>=0.7", "mypy>=1.13", "pytest>=8.3", "httpx>=0.27"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/steno10k"]

[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src", "tests"]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

- [ ] **Step 2: Write the failing test `backend/tests/test_version.py`**

```python
from __future__ import annotations

from steno10k.version import __version__


def test_version_is_semver() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
```

- [ ] **Step 3: Run it, verify it fails**

Run: `cd backend && uv run pytest tests/test_version.py -v`
Expected: FAIL (`ModuleNotFoundError: steno10k.version`).

- [ ] **Step 4: Implement**

`backend/src/steno10k/__init__.py`: empty.
`backend/src/steno10k/version.py`:

```python
from __future__ import annotations

__version__ = "0.1.0"
```

- [ ] **Step 5: Run test + lint + typecheck, verify pass**

```bash
cd backend && uv run pytest -v && uv run ruff check . && uv run mypy
```
Expected: tests PASS, ruff clean, mypy clean.

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "chore: backend scaffold (uv, ruff, mypy, pytest)"
```

---

## Task 6: Frontend scaffold (build/test tooling + trivial App)

Minimal only — **no design tokens or components** (those are the F3 milestone). Just enough for CI to lint/type/test/build.

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/eslint.config.js`, `frontend/.prettierrc`, `frontend/src/App.test.tsx`

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "steno10k-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": { "react": "^19.0.0", "react-dom": "^19.0.0" },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0", "vite": "^6.0.0", "typescript": "^5.6.0",
    "eslint": "^9.0.0", "prettier": "^3.3.0",
    "vitest": "^2.1.0", "@testing-library/react": "^16.0.0", "jsdom": "^25.0.0"
  }
}
```

- [ ] **Step 2: Write `tsconfig.json`, `vite.config.ts`, `index.html`, `main.tsx`, `App.tsx`, `eslint.config.js`, `.prettierrc`**

`tsconfig.json`: strict, `jsx: react-jsx`, `noUnusedLocals`, `noUnusedParameters`.
`vite.config.ts`: `react()` plugin; vitest `environment: "jsdom"`.
`index.html`: mounts `#root`, loads `main.tsx`.
`App.tsx`: renders the `steno10k` wordmark (plain, unstyled for now).

- [ ] **Step 3: Write the failing test `frontend/src/App.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";

test("renders the steno10k wordmark", () => {
  render(<App />);
  expect(screen.getByText(/steno/i)).toBeDefined();
});
```

- [ ] **Step 4: Install, run test + lint + typecheck + build, verify pass**

```bash
cd frontend && npm install && npm test && npm run lint && npm run typecheck && npm run build
```
Expected: test PASS, lint clean, typecheck clean, `dist/` built.

- [ ] **Step 5: Commit**

```bash
git add frontend && git commit -m "chore: frontend scaffold (vite, ts, eslint, vitest)"
```

---

## Task 7: Single-container Dockerfile + compose + health stub

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `backend/src/steno10k/api.py`, `backend/tests/test_health.py`

- [ ] **Step 1: Write the minimal liveness stub `backend/src/steno10k/api.py`**

```python
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="steno10k")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

(A liveness stub only — the real API surface is the F2 milestone.)

- [ ] **Step 2: Write the failing test `backend/tests/test_health.py`**

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from steno10k.api import app


def test_health_ok() -> None:
    resp = TestClient(app).get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 3: Run it, verify pass**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 4: Write multi-stage `Dockerfile`** — stage 1 (`node:22`) `npm ci && npm run build`; stage 2 (`python:3.12-slim`) installs `ffmpeg`, `uv sync`s the backend, copies the built SPA into a static dir, exposes `8000`, runs `uvicorn steno10k.api:app --host 0.0.0.0 --port 8000`.

- [ ] **Step 5: Write `docker-compose.yml`** — one `app` service built from the Dockerfile, `8000:8000`, a mounted volume at the data-root, `env_file: .env` for secrets. Write `.dockerignore` (node_modules, .venv, caches, data/, .git).

- [ ] **Step 6: Verify the image builds and serves health**

```bash
docker build -t steno10k:dev . && docker run --rm -d -p 8000:8000 --name s10 steno10k:dev && sleep 3 && curl -s localhost:8000/api/v1/health && docker stop s10
```
Expected: `{"status":"ok"}`.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore backend && git commit -m "chore: single-container Dockerfile, compose, health stub"
```

---

## Task 8: Pre-commit + commit-message lint

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Write `.pre-commit-config.yaml`** with hooks: ruff (lint+format) on `backend/`, prettier on `frontend/`, and a Conventional Commit `commit-msg` check.

- [ ] **Step 2: Verify**

Run: `pre-commit run --all-files`
Expected: hooks run; fix any reported issues.

- [ ] **Step 3: Commit**

```bash
git add .pre-commit-config.yaml && git commit -m "ci: pre-commit hooks (ruff, prettier, conventional commits)"
```

---

## Task 9: CI workflow (`ci.yml`)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write `ci.yml`** — triggers on `pull_request` and `push` to `main`. Jobs:
  - `backend`: setup uv + Python 3.12, `uv sync`, `uv run ruff check`, `uv run mypy`, `uv run pytest`.
  - `frontend`: setup Node 22, `npm ci`, `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, `npm run build`.
  - `docker`: `docker build .`.
  Cache uv and npm. These are the required checks.

- [ ] **Step 2: Add the GHCR push job (push to `main` only)** — build and push `ghcr.io/<owner>/steno10k:latest` and `:sha-<short>` via `docker/build-push-action` + `GITHUB_TOKEN` with `packages: write`.

- [ ] **Step 3: Validate YAML**

Run: `cd backend && uv run python -c "import yaml; yaml.safe_load(open('../.github/workflows/ci.yml')); print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml && git commit -m "ci: PR + main pipeline (lint, type, test, build, GHCR push)"
```

---

## Task 10: Release + Pages workflows

**Files:**
- Create: `.github/workflows/release.yml`, `.github/workflows/pages.yml`

- [ ] **Step 1: Write `release.yml`** — on tag `v*.*.*`: build + push the image tagged with the release tag, create a GitHub Release with notes from Conventional Commits, prepend release notes to `CHANGELOG.md`.

- [ ] **Step 2: Write `pages.yml`** — on push to `main` touching `landing/**`: deploy `landing/` to GitHub Pages (`actions/deploy-pages`).

- [ ] **Step 3: Validate YAML** (same `yaml.safe_load` check for both files). Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml .github/workflows/pages.yml && git commit -m "ci: release (tag -> image + GitHub Release) and Pages deploy"
```

---

## Task 11: Issue/PR templates, CODEOWNERS

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/task.md`, `.github/ISSUE_TEMPLATE/config.yml`, `.github/CODEOWNERS`

- [ ] **Step 1: PR template** (concise, F0 §3): linked issue (`Closes #`), what/why (2–3 lines), test evidence, checklist (tests pass, standards followed, no frozen-contract edits).

- [ ] **Step 2: Issue "task" template**: context, acceptance criteria, files likely touched, area label hint.

- [ ] **Step 3: `CODEOWNERS`** — auto-request review on frozen contracts (`/backend/src/steno10k/contracts/`, `/backend/src/steno10k/api/`, `/frontend/src/design/tokens.css`, `/docs/standards/`).

- [ ] **Step 4: Commit**

```bash
git add .github && git commit -m "chore: PR/issue templates + CODEOWNERS on frozen contracts"
```

---

## Task 12: Landing page (first proving deliverable, follows the F3 design system)

**Files:**
- Create: `landing/index.html`, `landing/styles.css`, `landing/script.js`

- [ ] **Step 1: Port the approved preview** from `docs/design/steno10k-style-preview.html` into `landing/`, split into `index.html` + `styles.css` (extract `<style>`) + `script.js` (reveal/theme JS if any). It **must follow the F3 design system exactly** — the same tokens, type triad, motion rules, and ban list — since it is the first public application of the design language and sets the standard the SPA follows.

- [ ] **Step 2: Substitute REAL links** for the placeholder `#`s so every link is clickable:
  - GitHub → `https://github.com/<owner>/steno10k` (the repo created in Task 13)
  - Issues → `…/steno10k/issues`
  - Changelog → `…/steno10k/blob/main/CHANGELOG.md`
  - License → `…/steno10k/blob/main/LICENSE`
  - Docs/Pipeline/Self-host → anchor links or `docs/` paths that resolve.
  (Determine `<owner>` from `gh api user --jq .login`.)

- [ ] **Step 3: Verify it renders**

Run: `open landing/index.html`. Confirm the Editorial Machine look + motion, working links, and that `prefers-reduced-motion` disables animation.

- [ ] **Step 4: Commit**

```bash
git add landing && git commit -m "feat: landing page in the Editorial Machine style, real links"
```

---

## Task 13: GitHub repo, remote, branch protection, Projects board

**Files:** none (GitHub configuration via `gh`)

- [ ] **Step 1: Create the remote repo and push**

```bash
gh repo create steno10k --public --source=. --remote=origin --description "Local-first audio -> transcript + summary. Self-hostable, MIT."
git push -u origin main
```

- [ ] **Step 2: Configure branch protection on `main`** (F0 §3.1) via `gh api` — require PR, required status checks (`backend`, `frontend`, `docker`), require branches up to date, linear history, squash-only (disable merge + rebase in repo settings), require conversation resolution, ≥1 review with stale-dismissal, block force-push + deletion.

- [ ] **Step 3: Create the GitHub Project board** — columns Backlog → Ready → In Progress → In Review → Done with standard automations; create labels `area:backend`, `area:frontend`, `area:infra`, `type:feat`, `good-parallel`, `blocked-on-contract`.

- [ ] **Step 4: Prove the loop end to end** — open a trivial PR from a branch, confirm CI runs and is required, squash-merge it, and confirm Pages deploys. Record the result.

- [ ] **Step 5: Verification note** — confirm F0 acceptance criteria (spec §11) are all met: repo + layout, protected `main`, CI blocking, GHCR image, release + Pages workflows, standards + AGENTS split, Project board, and the landing PR proving the loop.

---

## Self-review notes (coverage vs F0 spec §11)

- Repo + layout → Tasks 1, 5, 6, 7. Protected `main` + squash + required checks → Task 13 §2. CI (lint/type/test/build) + GHCR latest+sha → Task 9. Release `vX.Y.Z` + CHANGELOG prepend + Pages → Task 10. CONTRIBUTING (human) + AGENTS/CLAUDE + `docs/standards/*` split → Tasks 2, 3, 4. GitHub Project board + labels + templates → Tasks 11, 13. Secrets policy → `.gitignore` (Task 1) + `.env`/GH secrets (Task 7); **no `config.example.yaml` in M0** — deferred to the F1 milestone when real config exists. Landing page as the proving PR, following the design system, with real links → Tasks 12, 13 §4.
- **Deferred out of M0 (added in F1/F2/F3 milestones with real code):** `config.example.yaml`, backend domain models + contracts, `frontend/src/design/tokens.css`, UI primitive components. M0 references their frozen paths in AGENTS/CODEOWNERS so the guardrails exist before the code.
- **New in this revision:** `CLAUDE.md` symlink → `AGENTS.md` (Task 3); the user-level contract-change **lock protocol** in `~/.claude/locks/steno10k/` (Task 3); AGENTS.md authored per humanlayer's good-CLAUDE.md guidance.
