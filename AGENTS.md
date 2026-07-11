# AGENTS.md

Operating rules for any agent (and human) working in this repo. Keep it loaded.
`CLAUDE.md` is a symlink to this file — one source of truth.

## Prime directives

- **Simplicity is the value.** Least code wins; the best code is the code never
  written. Reuse over rewrite. DRY / SOLID / KISS.
- **Read `docs/standards/*` before writing code.** They are law, not suggestions.
- **One issue → one branch → one PR.** Scope tightly.

## Workflow

- **Branch:** `<type>/<issue>-<slug>` — e.g. `feat/42-stage-transcribe`. No `#`.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat | fix | chore | docs | test | refactor | ci:`.
- **Before pushing:** run `pre-commit run --all-files` and the relevant tests.
- **PRs:** `gh pr create`, link the issue (`Closes #N`), fill the template,
  keep the description concise and high-signal. CI must be green; PRs are
  squash-merged.
- **No AI attribution — ever.** Never add assistant/AI attribution to commits, PRs,
  code, or docs: no `Co-Authored-By: Claude…`, no "Generated with Claude Code", no
  🤖 trailers. Author every change as your own.
- **Parallel sessions:** use `git worktree` so each session has an isolated tree.

## Frozen contracts — do NOT edit in a feature/fan-out PR

These are the shared interfaces everything builds against. Changing them ripples
across parallel work, so they are coordinated separately:

- `backend/src/steno10k/contracts/` — domain models, Stage protocol, events
- `backend/src/steno10k/api/` — API DTOs / OpenAPI surface
- `frontend/src/design/tokens.css` — design tokens
- `docs/standards/` — the standards themselves

(These paths are created in the F1/F2/F3 milestones; listed now so the guardrail
exists first.)

### Contract-change lock protocol

When a change genuinely must touch a frozen contract:

1. **Stop** the feature work. Raise a small, isolated **contract-change PR**.
2. Create a lock file at **`~/.claude/locks/steno10k/<contract>.lock.md`**
   (user-level, outside the repo) describing: which contract, what changes, and
   the PR/branch link — so other agents can tell if they're impacted.
3. **Every agent checks `~/.claude/locks/steno10k/` before touching a frozen
   contract.** If an active lock covers your area, **wait** until it clears.
4. Remove the lock when the contract PR merges.

This advisory local lock complements GitHub branch protection + CODEOWNERS.

**Other shared resources that need the same lock.** Not every shared resource is a
"frozen contract", but anything with **shared sequential state** collides under
parallel work and must be coordinated the same way:

- **`docs/adr/` numbering** — the next ADR number is shared. Before adding an ADR,
  take a `~/.claude/locks/steno10k/adr.lock.md` lock, compute the next number, then
  release on merge. Two agents both grabbing `0001` otherwise clobber each other.

## Design & code standards (pointers)

- `docs/standards/git.md` — branching, commits, coordination protocol
- `docs/standards/python.md` — Python conventions
- `docs/standards/typescript.md` — TypeScript/React conventions
- `docs/standards/ui-design-system.md` — the design law (tokens, motion, bans)

## Notes for writing agent instructions

This file follows the guidance in
[Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
and [12-factor-agents](https://github.com/humanlayer/12-factor-agents): short,
high-signal, tool-oriented. When editing it, keep it that way — prune noise.
