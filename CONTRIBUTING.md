# Contributing to steno10k

Thanks for your interest. This guide covers how to get set up and how work
flows. **Coding and design standards live in `docs/standards/`** (and are
summarized for agents in `AGENTS.md`) — this file is about the mechanics.

## Local setup

**Backend** (Python 3.12+, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
uv run pytest        # tests
uv run ruff check .  # lint + format check
uv run mypy          # types
```

**Frontend** (Node 22+):

```bash
cd frontend
npm install
npm test             # unit tests
npm run lint
npm run typecheck
npm run build
```

**Full app** (single container):

```bash
docker compose up
```

**Hooks** — install pre-commit once so checks run before you push:

```bash
pre-commit install
```

## Workflow at a glance

1. One issue → one branch → one PR. Branch name: `<type>/<issue>-<slug>`
   (e.g. `feat/42-stage-transcribe`).
2. [Conventional Commits](https://www.conventionalcommits.org/) for messages
   (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `ci:`).
3. Run the checks locally, then open a PR with `gh pr create`, link the issue
   (`Closes #N`), and fill the template. Keep the description concise.
4. CI must be green; PRs are **squash-merged** into `main`.

## Questions

Open a [GitHub issue](../../issues). For anything touching a shared contract,
see the coordination protocol in `docs/standards/git.md`.
