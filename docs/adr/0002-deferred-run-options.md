# 0002 — Defer per-run run-options (only / from_stage / stage_overrides)

Status: Accepted · Date: 2026-07-12 · Milestone: M1·W

## Context

`RunOptions` carries `force`, `only`, `from_stage`, and `skip_llm`. Phase W wires
the run queue to the concrete stage registry and threads the per-run `force` flag
from the API (`EnqueueRunRequest`) through `RunQueue.enqueue` to `StageContext`.

The API request also accepts a `stage_overrides` map. The web UI does not expose
per-run stage selection — a run's active stages should be predictable from
project/set config, not chosen ad-hoc each time. `only`/`from_stage` are
single-run scoping tools better suited to the CLI (M1·C) than the current web
flow.

## Decision

Phase W threads **only `force`**. It does **not** apply per-run `stage_overrides`,
`only`, or `from_stage`. Each run's active stages are fully determined by
config-level `stages.enabled` (resolved by `run_set` with its dependency
cascade) plus `force`.

`EnqueueRunRequest.stage_overrides` remains on the request DTO for
forward-compatibility but is intentionally **unapplied** — it is accepted and
ignored, documented at the call site in `api/routers/runs.py`.

## Consequences

- Run behaviour is predictable: active stages depend only on
  `config.stages.enabled` + `force`, never on hidden per-run state.
- A future "advanced options" unit can wire `stage_overrides` (e.g. via a per-run
  `Config` copy in `runq._process`, leaving the frozen `run_set` untouched) and
  expose `only`/`from_stage`, most likely first through the CLI. No contract
  change is required to add them later — the fields already exist on `RunOptions`.
