# Phase W — Registry wire-up + run-options passthrough

## Goal

Make the run queue execute the real pipeline. Today `build_registry()` returns
an empty `StageRegistry([])` and `runq._process` hardcodes `RunOptions()`,
`force=False`, and `llm=None`, so an enqueued run does nothing useful. Phase W
wires the eight concrete stages into the registry, injects an LLM client so the
`clean`/`summarize` stages run, and threads `force` from the API through to the
stage context.

## Scope

Three concrete changes:

1. **Populate `build_registry()`** with the eight real stages.
2. **Inject the LLM client** into `StageContext` so LLM stages run.
3. **Thread `force`** from the API / enqueue → `Run` → `StageContext.force`.

Deferred (documented in an ADR, not implemented in W): per-run
`stage_overrides`, `only`, and `from_stage`. Each run uses config-level
`stages.enabled` as-is.

## Design

### 1. Registry wire-up

`api/stages.py::build_registry()` returns `StageRegistry([...])` populated with
the eight stages in canonical `StageName` declaration order:

```
normalize, chunk, transcribe, clean, merge, summarize, bundle, notify
```

Each stage's `depends_on` already matches `STAGE_DEPS` in the same module, and
`StageRegistry._validate()` enforces that every dependency is declared before
the stage that needs it. Construction therefore fails loudly if the order or a
dependency edge ever drifts.

### 2. LLM client injection

`runq._process` currently passes `llm=None`. Add a small private helper
(inline in `runq`, no new module — YAGNI) that resolves the client from config:

- `cfg.llm.enabled` is `True` → build `OpenAICompatibleClient(cfg.llm)`.
- Building raises `RuntimeError` (missing `api_key_env`) → log a warning and
  inject `None`. The LLM stages already guard on `ctx.llm is None` and return
  `StageStatus.SKIPPED` with `"no LLM client"`, so a missing key skips those
  stages instead of failing the whole run.
- `cfg.llm.enabled` is `False` → `None`.

This keeps the stages' existing `ctx.llm is None` guards as the single source of
truth for "LLM unavailable" and avoids duplicating that policy in the queue.

### 3. `force` passthrough

- `Run` dataclass gains `force: bool = False`, threaded through `_snapshot`.
- `RunQueue.enqueue(project, set_, *, force: bool = False)` stores it on `Run`.
- `_process` constructs `StageContext(force=run.force, ...)` and
  `RunOptions(force=run.force)`.
  - Stages read `ctx.force` (e.g. `clean`, `summarize`, `chunk`, `transcribe`,
    `bundle` all gate re-computation on `ctx.force`). `RunOptions.force` is set
    for consistency but is not what stages consume.
- `routers/runs.py::create_run` passes `body.force` into `enqueue`.
- The existing `stage_overrides` field stays on `EnqueueRunRequest` (frozen API
  surface) but remains **unapplied**: a code comment and the ADR record that
  per-run overrides are deferred; each run uses `cfg.stages.enabled`.

## Coordination (locks)

Per `CLAUDE.md`, two shared resources need advisory locks before work starts:

- **`~/.claude/locks/steno10k/api.lock.md`** — W edits the frozen `api/`
  surface (`stages.py`, `runq.py`, `routers/runs.py`). Take the contract-change
  lock before starting; release when the PR merges.
- **`~/.claude/locks/steno10k/adr.lock.md`** — the new ADR consumes the next
  shared ADR number. Take the numbering lock, compute the next number, release
  on merge.

## ADR

New `docs/adr/NNNN-deferred-run-options.md` records that `only`, `from_stage`,
and per-run `stage_overrides` are intentionally deferred to a later "advanced
options" unit. Until then, each run uses config-level `stages.enabled` plus the
per-run `force` flag.

## Testing

- **`test_stages.py`** — `build_registry()` returns the eight stages in
  canonical order and validates (dependencies declared backward).
- **`test_runq.py`**:
  - `enqueue(force=True)` → the `StageContext` observed by stages has
    `force=True`, and `Run.force` is snapshotted.
  - LLM helper returns a client when `cfg.llm.enabled`, and `None` when disabled
    or when the API key env var is missing (monkeypatched environment).
- **Integration** — enqueue a run over a tiny fixture set and assert the stages
  execute in canonical order via emitted events; LLM stages skip cleanly when no
  key is configured.

## Out of scope

- M1·C (the CLI consuming the richer `enqueue`).
- M1·P (single-container packaging).
- Any new API request fields (`only`/`from_stage` are ADR-documented only).
