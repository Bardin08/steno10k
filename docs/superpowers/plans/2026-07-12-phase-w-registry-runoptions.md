# Phase W — Registry Wire-up + Run-Options Passthrough Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the run queue execute the real 8-stage pipeline — populate `build_registry()`, inject an LLM client into `StageContext`, and thread the `force` flag from the API through to stages.

**Architecture:** `build_registry()` returns the eight concrete `Stage` instances in canonical order (validated by `StageRegistry`). `runq._process` resolves an `LLMClient` from `cfg.llm` and threads `Run.force` into `StageContext.force` / `RunOptions.force`. `routers/runs.py` passes `body.force` into `enqueue`. Per-run `stage_overrides`/`only`/`from_stage` are deferred and recorded in an ADR.

**Tech Stack:** Python 3.12, FastAPI, pydantic, pytest. Package root `backend/src/steno10k`; tests under `backend/tests`. Run commands from `backend/`.

---

## Preconditions (do before Task 1)

- [ ] **Take the frozen-`api/` contract lock.** Create `~/.claude/locks/steno10k/api.lock.md` describing: contract = `backend/src/steno10k/api/` (`stages.py`, `runq.py`, `routers/runs.py`); change = populate registry, inject LLM client, thread `force`; branch = `feat/phase-w-registry-runoptions`. Confirm no other active lock covers `api/` first.
- [ ] **Take the ADR numbering lock.** Create `~/.claude/locks/steno10k/adr.lock.md`. `docs/adr/` is currently empty, so the next number is `0001`. Record that W claims `0001`.

Both locks are removed after the PR merges (final task).

---

## Task 1: Populate `build_registry()`

**Files:**
- Modify: `backend/src/steno10k/api/stages.py:32-40`
- Test: `backend/tests/api/test_stages.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/api/test_stages.py`:

```python
from __future__ import annotations

from steno10k.api.stages import build_registry
from steno10k.contracts.names import StageName


def test_build_registry_has_all_eight_stages_in_canonical_order() -> None:
    reg = build_registry()
    assert reg.names == [
        StageName.NORMALIZE,
        StageName.CHUNK,
        StageName.TRANSCRIBE,
        StageName.CLEAN,
        StageName.MERGE,
        StageName.SUMMARIZE,
        StageName.BUNDLE,
        StageName.NOTIFY,
    ]


def test_build_registry_deps_match_declared_graph() -> None:
    # StageRegistry() would raise on construction if any depends_on edge pointed
    # forward; this asserts the concrete stages' declared deps survive validation.
    reg = build_registry()
    deps = reg.deps()
    assert deps[StageName.CHUNK] == [StageName.NORMALIZE]
    assert deps[StageName.SUMMARIZE] == [StageName.MERGE, StageName.CLEAN]
    assert deps[StageName.NORMALIZE] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_stages.py -v`
Expected: FAIL — `test_build_registry_has_all_eight_stages_in_canonical_order` asserts `reg.names == []` is not the 8-element list (current stub returns `StageRegistry([])`).

- [ ] **Step 3: Implement `build_registry()`**

Replace the body of `build_registry()` in `backend/src/steno10k/api/stages.py` (keep the existing `STAGE_DEPS` dict and module docstring above it). Update imports at the top of the file to add the stage classes:

```python
from steno10k.stages.bundle import BundleStage
from steno10k.stages.chunk import ChunkStage
from steno10k.stages.clean import CleanStage
from steno10k.stages.merge import MergeStage
from steno10k.stages.normalize import NormalizeStage
from steno10k.stages.notify import NotifyStage
from steno10k.stages.summarize import SummarizeStage
from steno10k.stages.transcribe import TranscribeStage
```

New body:

```python
def build_registry() -> StageRegistry:
    """Assemble the concrete `StageRegistry` the run queue executes.

    Stages are listed in canonical `StageName` order; `StageRegistry` validates
    that every `depends_on` edge points at an earlier stage.
    """
    return StageRegistry(
        [
            NormalizeStage(),
            ChunkStage(),
            TranscribeStage(),
            CleanStage(),
            MergeStage(),
            SummarizeStage(),
            BundleStage(),
            NotifyStage(),
        ]
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/api/test_stages.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Guard the import boundary**

The stages import heavy deps (ffmpeg/whisper wrappers). Confirm `create_app` still imports cleanly:

Run: `cd backend && uv run python -c "from steno10k.api import create_app; create_app.__name__"`
Expected: prints `create_app` with no ImportError.

- [ ] **Step 6: Commit**

```bash
git add backend/src/steno10k/api/stages.py backend/tests/api/test_stages.py
git commit -m "feat: populate build_registry with the eight concrete stages"
```

---

## Task 2: Add `force` to the `Run` record

**Files:**
- Modify: `backend/src/steno10k/api/runq.py:31-47` (`Run` dataclass), `:147-157` (`_snapshot`)
- Test: `backend/tests/api/test_runq.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/api/test_runq.py`:

```python
def test_enqueue_defaults_force_false(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    run = q.enqueue(project="law", set_="week-1")
    assert run.force is False
    assert q.get(run.id).force is False


def test_enqueue_records_force_true(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    run = q.enqueue(project="law", set_="week-1", force=True)
    assert run.force is True
    assert q.get(run.id).force is True  # survives _snapshot round-trip
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_runq.py -k force -v`
Expected: FAIL — `TypeError: enqueue() got an unexpected keyword argument 'force'` (and `Run` has no `force` attr).

- [ ] **Step 3: Add the field**

In `backend/src/steno10k/api/runq.py`, add `force` to the `Run` dataclass (after `position`):

```python
    position: int = 0
    force: bool = False
    stats: dict[str, Any] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
```

Thread it through `_snapshot` (add the `force=run.force` line):

```python
    @staticmethod
    def _snapshot(run: Run) -> Run:
        return Run(
            id=run.id,
            project=run.project,
            set_=run.set_,
            status=run.status,
            position=run.position,
            force=run.force,
            stats=dict(run.stats),
            events=list(run.events),
        )
```

Update `enqueue` to accept and store `force`:

```python
    def enqueue(self, project: str, set_: str, *, force: bool = False) -> Run:
        # position is a best-effort snapshot of queue depth at enqueue time;
        # it is never updated afterwards, so it can go stale as other runs
        # complete or are cancelled ahead of this one.
        run = Run(
            id=new_id(),
            project=project,
            set_=set_,
            position=self._queue.qsize(),
            force=force,
        )
        bus = EventBus()
        bus.subscribe(functools.partial(self._record_event, run.id))
        with self._lock:
            self._runs[run.id] = run
            self._buses[run.id] = bus
        self._queue.put(run.id)
        return run
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/api/test_runq.py -k force -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/api/runq.py backend/tests/api/test_runq.py
git commit -m "feat: record per-run force flag on Run"
```

---

## Task 3: Thread `force` into `StageContext` / `RunOptions`

**Files:**
- Modify: `backend/src/steno10k/api/runq.py:169-206` (`_process`)
- Test: `backend/tests/api/test_runq.py`

- [ ] **Step 1: Write the failing test**

Add a stage that captures the `ctx.force` it observes, plus a test. Append to `backend/tests/api/test_runq.py`:

```python
@dataclass
class _ForceRecordingStage:
    """Records the `ctx.force` value seen at run time so a test can assert
    the queue threaded the per-run force flag into the StageContext."""

    seen: list[bool] = field(default_factory=list)
    name: StageName = StageName.NORMALIZE
    depends_on: list[StageName] = field(default_factory=list)

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        self.seen.append(ctx.force)
        return StageResult(status=StageStatus.OK)


def test_force_threads_into_stage_context(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    stage = _ForceRecordingStage()
    q = RunQueue(storage=storage, registry=StageRegistry([stage]))
    q.start()
    try:
        run = q.enqueue(project="law", set_="week-1", force=True)
        _wait(lambda: q.get(run.id).status == RunStatus.COMPLETED)
        assert stage.seen == [True]
    finally:
        q.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_runq.py::test_force_threads_into_stage_context -v`
Expected: FAIL — `assert [False] == [True]` (`_process` hardcodes `force=False`).

- [ ] **Step 3: Thread force in `_process`**

In `_process`, change the `StageContext` construction and `run_set` call. Replace `force=False` with `force=run.force`, and pass `RunOptions(force=run.force)`:

```python
            ctx = StageContext(
                set_dir=set_dir,
                cfg=cfg,
                force=run.force,
                manifest=manifest,
                errors=errors,
                events=bus,
                llm=None,
            )
            run_set(self._registry, ctx, RunOptions(force=run.force))
```

(The `llm=None` line is replaced in Task 4.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/api/test_runq.py::test_force_threads_into_stage_context -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/api/runq.py backend/tests/api/test_runq.py
git commit -m "feat: thread per-run force into StageContext and RunOptions"
```

---

## Task 4: Inject the LLM client in `_process`

**Files:**
- Modify: `backend/src/steno10k/api/runq.py` (imports, new `_make_llm` helper, `_process` `llm=` arg)
- Test: `backend/tests/api/test_runq.py`

- [ ] **Step 1: Write the failing test**

Add imports and tests. At the top of `backend/tests/api/test_runq.py` add:

```python
from steno10k.api.runq import _make_llm
from steno10k.contracts.config import LLMConfig
from steno10k.lib.llm import OpenAICompatibleClient
```

Append tests:

```python
def test_make_llm_returns_none_when_disabled() -> None:
    cfg = Config()
    cfg.llm.enabled = False
    assert _make_llm(cfg) is None


def test_make_llm_returns_none_when_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = Config()
    cfg.llm = LLMConfig(enabled=True, api_key_env="OPENAI_API_KEY", model="gpt-x")
    # missing key: OpenAICompatibleClient.__init__ raises RuntimeError, which
    # _make_llm swallows into None so the run degrades gracefully.
    assert _make_llm(cfg) is None


def test_make_llm_builds_client_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    cfg = Config()
    cfg.llm = LLMConfig(enabled=True, api_key_env="OPENAI_API_KEY", model="gpt-x")
    client = _make_llm(cfg)
    assert isinstance(client, OpenAICompatibleClient)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_runq.py -k make_llm -v`
Expected: FAIL — `ImportError: cannot import name '_make_llm'`.

- [ ] **Step 3: Implement `_make_llm` and use it**

In `backend/src/steno10k/api/runq.py`, add imports near the top:

```python
from steno10k.contracts.config import Config
from steno10k.contracts.llm import LLMClient
from steno10k.lib.llm import OpenAICompatibleClient
```

Add a module-level helper (place it above the `RunQueue` class, after the `Run` dataclass):

```python
def _make_llm(cfg: Config) -> LLMClient | None:
    """Resolve an LLM client from config, or None when unavailable.

    Returns None when the LLM is disabled or its API key env var is unset —
    the LLM stages guard on `ctx.llm is None` and self-skip, so a missing key
    degrades to a transcript-only run instead of failing it.
    """
    if not cfg.llm.enabled:
        return None
    try:
        return OpenAICompatibleClient(cfg.llm)
    except RuntimeError as exc:  # missing API key
        log.warning("LLM client unavailable, LLM stages will skip: %s", exc)
        return None
```

In `_process`, change the `StageContext` `llm=None` to `llm=_make_llm(cfg)`:

```python
                events=bus,
                llm=_make_llm(cfg),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/api/test_runq.py -k make_llm -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/api/runq.py backend/tests/api/test_runq.py
git commit -m "feat: inject LLM client into run stage context"
```

---

## Task 5: Pass `force` through the runs router

**Files:**
- Modify: `backend/src/steno10k/api/routers/runs.py:26-35` (`create_run`)
- Test: `backend/tests/api/test_runs.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/api/test_runs.py`:

```python
def test_create_run_threads_force(tmp_path: Path) -> None:
    from steno10k.api import create_app  # noqa: F811 (explicit for readability)

    with TestClient(create_app(data_root=tmp_path)) as c:
        c.post("/api/v1/projects", json={"title": "Law"})
        c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
        run_id = c.post(
            "/api/v1/runs",
            json={"project": "law", "set": "week-1", "force": True},
        ).json()["data"]["id"]

        rq = c.app.state.run_queue
        assert rq.get(run_id).force is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_runs.py::test_create_run_threads_force -v`
Expected: FAIL — `rq.get(run_id).force is True` is `False`, since `create_run` calls `enqueue` without `force`.

- [ ] **Step 3: Pass force in `create_run`**

Replace the body comment + `enqueue` call in `backend/src/steno10k/api/routers/runs.py::create_run`:

```python
@router.post("")
def create_run(
    body: EnqueueRunRequest, run_queue: Annotated[RunQueue, Depends(get_run_queue)]
) -> dict[str, Any]:
    # `force` is threaded through; `stage_overrides` is accepted on the request
    # for forward-compatibility but intentionally NOT applied per-run yet — each
    # run uses config-level `stages.enabled`. See docs/adr/0001-deferred-run-options.md.
    run = run_queue.enqueue(project=body.project, set_=body.set, force=body.force)
    return ok(RunDTO.from_domain(run).model_dump())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/api/test_runs.py::test_create_run_threads_force -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/api/routers/runs.py backend/tests/api/test_runs.py
git commit -m "feat: thread force from runs router into enqueue"
```

---

## Task 6: Integration test — full registry executes in order

**Files:**
- Test: `backend/tests/api/test_runq.py`

- [ ] **Step 1: Write the test**

This proves the real `build_registry()` runs end-to-end via the queue and emits stage events in canonical order. LLM stages skip cleanly (no API key). Append to `backend/tests/api/test_runq.py`:

```python
def test_full_registry_runs_stages_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from steno10k.api.stages import build_registry

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # LLM stages self-skip
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")  # empty set: stages no-op but run to completion
    q = RunQueue(storage=storage, registry=build_registry())
    run = q.enqueue(project="law", set_="week-1")
    bus = q.get_bus(run.id)
    started: list[str] = []
    assert bus is not None
    bus.subscribe(
        lambda e: started.append(str(e.payload.get("stage")))
        if e.kind == "stage_started"
        else None
    )
    q.start()
    try:
        _wait(lambda: q.get(run.id).status == RunStatus.COMPLETED, timeout=10.0)
        # stages that actually started must appear in canonical order
        canonical = [str(n) for n in build_registry().names]
        observed = [s for s in started if s in canonical]
        assert observed == sorted(observed, key=canonical.index)
    finally:
        q.stop()
```

- [ ] **Step 2: Run the test**

Run: `cd backend && uv run pytest tests/api/test_runq.py::test_full_registry_runs_stages_in_order -v`
Expected: PASS. (If a heavy stage fails on the empty set rather than skipping, that is a real defect to investigate — the run should complete with stages skipped/no-op, not crash the worker.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/api/test_runq.py
git commit -m "test: full registry executes stages in canonical order via queue"
```

---

## Task 7: ADR for deferred run-options

**Files:**
- Create: `backend/../docs/adr/0001-deferred-run-options.md` (repo path `docs/adr/0001-deferred-run-options.md`)

- [ ] **Step 1: Write the ADR**

Create `docs/adr/0001-deferred-run-options.md`:

```markdown
# 0001 — Deferred run-options (only / from_stage / per-run stage_overrides)

- Status: Accepted
- Date: 2026-07-12

## Context

`RunOptions` carries `force`, `only`, `from_stage`, and `skip_llm`. Phase W
wires the run queue to the concrete stage registry and threads the per-run
`force` flag from the API through to `StageContext`.

The API (`EnqueueRunRequest`) also accepts a `stage_overrides` map. The UI does
not expose per-run stage selection, and `only`/`from_stage` are single-run
scoping tools better suited to the CLI (M1·C) than the current web flow.

## Decision

Phase W threads only `force`. It does NOT apply per-run `stage_overrides`,
`only`, or `from_stage`. Each run uses config-level `stages.enabled` (resolved
by `run_set` with its dependency cascade). `EnqueueRunRequest.stage_overrides`
remains on the request for forward-compatibility but is intentionally unapplied.

## Consequences

- Behaviour is predictable: a run's active stages are fully determined by
  `config.stages.enabled` plus `force`.
- A future "advanced options" unit can wire `stage_overrides` (e.g. via a
  per-run `Config` copy in `_process`) and expose `only`/`from_stage`, most
  likely first through the CLI. No contract change is needed to add them later.
```

- [ ] **Step 2: Verify the reference resolves**

Confirm the path the router comment references now exists:

Run: `test -f docs/adr/0001-deferred-run-options.md && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0001-deferred-run-options.md
git commit -m "docs: ADR 0001 deferred run-options (only/from_stage/stage_overrides)"
```

- [ ] **Step 4: Release the ADR lock**

Remove `~/.claude/locks/steno10k/adr.lock.md` (the ADR number is now committed on the branch).

---

## Task 8: Full verification + PR

- [ ] **Step 1: Run the full backend gate**

Per the CI-gates memory, CI runs bare `uv run mypy` (strict, over src AND tests) and pre-commit skips mypy — so run mypy explicitly:

```bash
cd backend && uv run mypy && uv run pytest -q
```

Expected: mypy clean, all tests pass.

- [ ] **Step 2: Run pre-commit**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k && pre-commit run --all-files
```

Expected: all hooks pass (fix and re-run if any reformat).

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin feat/phase-w-registry-runoptions
gh pr create --fill
```

In the PR body, note: closes the M1·W unit; touched the frozen `api/` surface under the contract-change lock; added ADR 0001. Keep it concise, no AI attribution.

- [ ] **Step 4: Release the api/ contract lock**

After the PR merges, remove `~/.claude/locks/steno10k/api.lock.md`.
```
