# steno10k F0 — Repo Operating Model

_Foundation spec 0 of the steno10k build. Defines the "operating system" for the
whole project: repo structure, git workflow, CI/CD, code standards, agent
instructions, and task tracking. **This must exist before any feature code** —
every later foundation (domain & core contracts, API schema, design system) and
every fan-out unit is committed through this model._

Parent vision: `2026-07-11-new-audio-pipeline-vision-design.md`.
Status: design spec, for review. Date: 2026-07-11.

---

## 1. Goal & guiding principles

Get CI/CD, git discipline, and task tracking in place **from commit one** —
cheaper at the start than retrofitted, and what makes the **parallel multi-agent
build safe**. Without a written branch/commit/PR contract and green-CI gates, many
concurrent sessions produce merge chaos and an inconsistent, vibe-coded mix.

**Primary value: simplicity → speed of development.** Everything below optimizes
for clear, concise, low-friction work. Concretely:

- **The best code is the code never written.** Prefer reuse, well-maintained
  libraries, and model-driven generation over hand-rolled code.
- **DRY / SOLID / KISS.** No duplication; small, focused, supportable units.
- **Keep it concise.** Docs, PR descriptions, and instructions are short and
  high-signal — never bloated or hard to read.

**Definition of done:** a fresh public GitHub repo `steno10k` where an agent can be
told "take issue #N, deliver its PR," and the repo mechanically enforces
structure, style, tests, and history — with the task visibly tracked start to
finish.

## 2. Repo & scaffolding

- **Repo:** `steno10k`, public, MIT `LICENSE`.
- **Top-level layout** (monorepo — backend + frontend + infra in one repo, matching
  the single-container deployment):

  ```
  steno10k/
    backend/            # Python: FastAPI app + pipeline + stages
      src/steno10k/
      tests/
      pyproject.toml
    frontend/           # React SPA (TypeScript)
      src/
      package.json
    landing/            # GitHub Pages landing page
    docs/
      standards/        # coding standards (agent knowledge — see §5, §9)
      adr/              # architecture decision records
    .github/            # workflows, issue/PR templates, CODEOWNERS
    Dockerfile          # single container (backend serves built frontend)
    docker-compose.yml  # local dev convenience (app + mounted volume)
    CONTRIBUTING.md     # human-facing: how to contribute
    AGENTS.md           # agent working instructions (see §6)
    README.md
    CHANGELOG.md        # release-only, auto-maintained (see §4)
  ```

- Baseline files in this foundation: `LICENSE`, `README` skeleton, `CONTRIBUTING`,
  `AGENTS.md`, `docs/standards/*`, `.gitignore`, `.editorconfig`,
  `config.example.yaml` (placeholders only — no secrets ever).
- **`CHANGELOG.md` is for releases, not per-agent changes.** It is never edited by
  hand in feature PRs; the release workflow (§4) prepends each release's notes to
  the top of the file.

## 3. Git workflow (the agent contract)

- **Model: trunk-based with short-lived feature branches.** `main` is always green
  and deployable. No long-lived `develop` branch.
- **Branch naming:** `<type>/<issue>-<slug>` — e.g. `feat/42-stage-transcribe`,
  `chore/7-ci`, `fix/88-chunk-overlap`. No `#` in the branch name. Types mirror
  Conventional Commits.
- **Commits: Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, `test:`,
  `refactor:`, `ci:`). Enables automated changelog / versioning.
- **Integration: PR-per-unit.** No direct pushes to `main` (branch protection). A
  PR must (a) link its issue (`Closes #N`), (b) pass all required CI checks,
  (c) be **squash-merged** → clean, linear history, one commit per unit.
- **PR description template (day one).** Short and clear: what/why, linked issue,
  test evidence, checklist. Concise by rule — no wall-of-text, no filler that is
  hard to read. Simplicity is the value.

### 3.1 Branch protection rules (`main`)

Configured on the repo from day one (via the GitHub ruleset / branch protection):

- **Require a pull request before merging** — no direct pushes to `main`.
- **Require status checks to pass** — all `ci.yml` required checks (lint,
  typecheck, tests, container build) green, and the **branch up to date** with
  `main` before merge.
- **Require linear history** and **allow squash-merge only** (merge commits and
  rebase-merge disabled).
- **Require conversation resolution** before merging.
- **Require ≥1 approving review**, with **dismiss stale approvals on new commits**
  (a solo maintainer can self-approve / an agent's PR is approved by the
  integrator; CODEOWNERS auto-requests review on the shared contracts).
- **Block force-pushes and branch deletion** on `main`.
- **Applies to administrators**, with a narrow, documented bypass for the
  integrator to fast-track contract-change PRs (§3.2) when needed.

### 3.2 Shared-contract changes — coordination, not prohibition

Additive-only ("never touch shared files") is **rejected**: you cannot build a
real system without evolving shared contracts, and forcing additivity breeds
duplication (violates DRY). Instead, a lightweight **coordination protocol**:

- The shared contracts (the domain & core-contract modules, the API schema, the
  design tokens) start from a frozen baseline but **are allowed to evolve**.
- When a fan-out unit needs a shared-contract change, the agent **stops**, and the
  change goes out as a **small, isolated, fast-tracked "contract change" PR** —
  separate from the feature work, reviewed and merged with priority.
- Dependent in-flight branches then **rebase onto the updated `main`**. Downstream
  work that depends on the pending contract change **waits** until it is merged.
- Keep the shared surface **small and stable** to minimize how often this happens;
  batch contract changes where possible. A designated integrator (human/orchestrator)
  approves contract PRs quickly so workers aren't blocked long.

Net effect: shared changes are safe and DRY, not forbidden — the cost is a short,
explicit coordination step instead of silent divergence.

## 4. CI/CD (GitHub Actions, from commit one)

- **`ci.yml` — on every PR and push to `main`:**
  - Backend: `ruff` (lint+format check), `mypy`, `pytest`.
  - Frontend: `eslint`, `prettier --check`, `tsc --noEmit`, `vitest`.
  - Build: frontend production build + the single Docker image.
  - Required checks for merge (branch protection).
- **On merge to `main`:** build and **push the image to GHCR**, tagged **`latest`**
  and with the **short commit hash** (e.g. `sha-1a2b3c4`) so any build is pullable
  and runnable directly.
- **`release.yml` — on tag `v{major}.{minor}.{patch}`** (e.g. `v0.1.0`): build and
  push the image tagged with the **release tag**, create a GitHub Release with
  notes from Conventional Commits, and prepend those notes to `CHANGELOG.md`.
- **`pages.yml` — on push to `main` touching `landing/`:** deploy the GitHub Pages
  landing page.
- Cache pip/uv and npm for fast runs; single supported version to start.

## 5. Code standards & tooling

Guiding rule throughout: **least code wins; reuse over rewrite; DRY/SOLID/KISS.**
Standards live in `docs/standards/*` (agent knowledge, §9); **CI is the mechanical
enforcement** — the config in the repo is the single source of truth, not prose.

- **Python:** `ruff` (lint + format, replaces black/isort/flake8), `mypy`
  (strict-ish), `pytest`. `from __future__ import annotations`; modern type syntax
  (`X | None`, `list[X]`). Packaged via `pyproject.toml` (prefer `uv`). Favor
  standard-library and vetted deps over bespoke code.
- **TypeScript/React:** `eslint` + `prettier`, strict `tsconfig`, `vitest`. Same
  minimal-code ethos. Component and style conventions **strictly follow the design
  system**, defined in the design-system foundation — including the specific set of
  skills we adopt there (decided when we work that spec).

## 6. Agent working instructions (`AGENTS.md`)

Machine-facing, high-signal rules so any session behaves identically. Written to
be **short and tool-oriented**, following the principles in:

- humanlayer — "Writing a good CLAUDE.md" (https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- humanlayer — 12-factor-agents (https://github.com/humanlayer/12-factor-agents)

Contents:

- Pick up work: one issue → one branch → one PR; scope tightly.
- Branch naming + Conventional Commit format (with examples).
- Run `pre-commit` / the CI check subset **locally before pushing**.
- Open PRs with `gh`, link the issue (`Closes #N`), fill the (concise) PR template.
- **Do not edit the shared contracts** (the domain & core-contract modules, the API
  schema, the design tokens) inside a fan-out PR. If a change is needed, stop and
  follow the coordination protocol (§3.2).
- Use **git worktrees** when multiple sessions run locally (isolated working dirs).
- Where the standards (`docs/standards/*`) live and how to run tests.

## 7. Task tracking (GitHub Projects)

- **GitHub Issues + a GitHub Project board** is the single record of work.
- **Columns:** Backlog → Ready → In Progress → In Review → Done, with automations
  (Issue → In Progress when a linked PR opens; → Done on merge).
- **Hierarchy:** one **epic issue per milestone**, **sub-issue per fan-out unit**
  (each stage, endpoint, screen). Branches/PRs reference issue numbers → full audit
  trail.
- **Labels:** `area:backend`, `area:frontend`, `area:infra`, `type:feat`,
  `good-parallel`, `blocked-on-contract`.
- **Sync:** the `gh-plan` skill turns a milestone's plan file into the epic +
  sub-issues on the board.
- **Templates:** concise issue template (context, acceptance criteria, touched
  files) and PR template (§3) in `.github/`.

## 8. Secrets management

- **No secret ever enters the repo.** `config.example.yaml` ships placeholders;
  real values come from environment variables at runtime and **GitHub Actions
  secrets** in CI. `.gitignore` excludes real config / `.env`.

## 9. Docs split: contributing vs standards

- **`CONTRIBUTING.md`** — human-facing only: how to set up, the workflow at a
  glance, how to open a PR, where to ask questions. **Not** the place for coding
  standards.
- **`docs/standards/*`** — the actual coding standards (Python, TypeScript, git,
  testing), authored as agent knowledge and referenced by `AGENTS.md`. Kept
  concise; CI enforces them mechanically.

## 10. Non-goals / deferred (deliberate)

- Renovate/Dependabot automated dependency updates.
- Full `semantic-release` auto-versioning (start with manual `vX.Y.Z` tags +
  Conventional Commits).
- Multi-version / multi-OS CI matrix.
- Code-coverage gates (add once there's meaningful code).

## 11. Acceptance criteria

- Public `steno10k` repo with the §2 layout and baseline files.
- `main` protected: required CI checks, no direct push, squash-merge only.
- `ci.yml` runs lint + typecheck + tests + container build on PRs and blocks merge
  on failure; merges to `main` push a `latest` + short-SHA image to GHCR.
- `release.yml` produces a `v{major}.{minor}.{patch}`-tagged image + GitHub Release
  + `CHANGELOG` prepend.
- `CONTRIBUTING.md` (human) + `AGENTS.md` + `docs/standards/*` document the
  workflow and standards, split per §9.
- A GitHub Project board exists with the §7 columns, automations, labels, and
  concise issue/PR templates.
- **First real PR = the landing page** (`landing/` → GitHub Pages): it proves the
  whole loop end to end (branch → PR → CI → squash-merge → Pages deploy) **and**
  delivers the landing page, which is itself part of the repo/Pages configuration.
