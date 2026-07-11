# Git standard

## Model

Trunk-based. `main` is always green and deployable. No long-lived `develop`.

## Branches

`<type>/<issue>-<slug>` — e.g. `feat/42-stage-transcribe`, `chore/7-ci`,
`fix/88-chunk-overlap`. No `#` in the name. `<type>` mirrors the commit type.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):

| Type       | Use for                                  |
| ---------- | ---------------------------------------- |
| `feat`     | a user-facing feature                    |
| `fix`      | a bug fix                                |
| `chore`    | tooling, scaffolding, deps               |
| `docs`     | documentation                            |
| `test`     | tests only                               |
| `refactor` | behaviour-preserving restructuring       |
| `ci`       | CI/CD changes                            |

## Integration

- **PR-per-unit.** No direct pushes to `main` (branch protection).
- A PR must link its issue (`Closes #N`), pass all required CI checks, and be
  **squash-merged** → one commit per unit, linear history.
- PR descriptions are concise and high-signal.

## Shared-contract changes — coordination

Additive-only is **not** required (it breeds duplication). Instead:

1. When a change must touch a frozen contract (see `AGENTS.md`), stop feature
   work and raise a small, isolated **contract-change PR**, reviewed with
   priority.
2. Create a lock at `~/.claude/locks/steno10k/<contract>.lock.md` describing the
   change; other agents check it and **wait** if impacted.
3. Dependent branches rebase onto updated `main`. Remove the lock on merge.

Keep the shared surface small and stable to minimize coordination.
