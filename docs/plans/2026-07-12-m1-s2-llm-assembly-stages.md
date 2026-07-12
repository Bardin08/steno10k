# M1·S2 — LLM + Assembly Stages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pipeline's back half — five `Stage` implementations (`clean`, `merge`, `summarize`, `bundle`, `notify`) under `steno10k/stages/` — and rewire the F2 prompts router onto `lib.prompts`.

**Architecture:** Each stage is a black-box class implementing the F1 `Stage` protocol (`name`, `depends_on`, `enabled(cfg, opts)`, `run(ctx) -> StageResult`). Stages read a `StageContext`, iterate `ctx.manifest.recordings` as the source of truth, read/write files under `ctx.set_dir` per the §3 on-disk contract, and call into the merged M1·L library (`lib.prompts`, `lib.docx`) and the `ctx.llm` protocol. Dependency direction is one-way: `stages → lib`, `stages → contracts`; stages never import `api`. Registry wiring and `RunOptions` threading are out of scope (M1·W).

**Tech Stack:** Python 3.12, pytest, mypy (strict), ruff. Runtime deps (`openai`, `python-docx`, `httpx`) already landed with M1·L (#14).

**Spec:** `docs/specs/2026-07-11-steno10k-m1-s2-llm-assembly-stages-design.md`.

**Reference (parts bin):** `/Users/vladyslavbardin/Docs/Personal/lecturemate10k/src/audio_pipeline/pipeline.py` (`_clean_stage`, `_merge_stage`, `_conspect_stage`, `_bundle_stage`, `_notify_stage`, `_run_llm_pool`).

**Preconditions (verified):** Branch `feat/m1-s2-llm-assembly-stages` exists, rebased on `origin/main` (L merged, #14). `steno10k/lib/{prompts,docx,llm}.py` present with the surfaces this plan calls. `api/stages.py::STAGE_DEPS` present. No `steno10k/stages/` package yet.

---

## File Structure

Created under `backend/`:

- `src/steno10k/stages/__init__.py` — package marker.
- `src/steno10k/stages/_pool.py` — `run_pool`: bounded thread pool yielding `(item, result, error)`.
- `src/steno10k/stages/_prompts.py` — `resolve_override_dir(cfg, set_dir)`: prompt override dir (matches the F2 router convention).
- `src/steno10k/stages/clean.py` — `CleanStage` (LLM, per-chunk).
- `src/steno10k/stages/merge.py` — `MergeStage` (assembly: raw + clean).
- `src/steno10k/stages/summarize.py` — `SummarizeStage` (LLM, from merged clean).
- `src/steno10k/stages/bundle.py` — `BundleStage` (docx via `lib.docx`).
- `src/steno10k/stages/notify.py` — `NotifyStage` (emit-only).
- `tests/stages/__init__.py` — package marker.
- `tests/stages/support.py` — shared test helpers (`FakeLLM`, `make_ctx`, `make_manifest`, `seed_raw`).
- `tests/stages/test_*.py` — one per stage + `test_import_boundary.py` + `test_pool.py` + `test_prompts_helper.py`.

Modified:

- `src/steno10k/api/routers/prompts.py` — source defaults from `lib.prompts` (surface unchanged).
- `tests/api/test_config_prompts.py` — retarget assertions to the `lib.prompts` defaults.

---

## Task 0: Ticket, package skeletons, shared test support

Per the F0 operating model (AGENTS.md): **one issue → one branch → one PR**. The branch already exists (`feat/m1-s2-llm-assembly-stages`, rebased on `origin/main`); this task creates the tracking issue and the package scaffolding.

**Files:**
- Create: `backend/src/steno10k/stages/__init__.py`
- Create: `backend/tests/stages/__init__.py`
- Create: `backend/tests/stages/support.py`
- Create: `backend/tests/stages/conftest.py`

- [ ] **Step 1: Create the GitHub issue (ticket)**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k-s2
gh issue create \
  --title "M1·S2: LLM + assembly stages (clean, merge, summarize, bundle, notify)" \
  --label "area:backend,type:feat" \
  --body "$(cat <<'EOF'
Implements the M1·S2 fan-out unit — the LLM + assembly stages under steno10k/stages/.

Spec: docs/specs/2026-07-11-steno10k-m1-s2-llm-assembly-stages-design.md
Plan: docs/plans/2026-07-12-m1-s2-llm-assembly-stages.md
Umbrella: docs/specs/2026-07-11-steno10k-m1-decomposition-design.md

Acceptance (spec §9):
- [ ] stages/ has clean, merge, summarize, bundle, notify implementing the F1 Stage protocol; depends_on matches api/stages.py::STAGE_DEPS; no api import.
- [ ] Seeded transcripts_raw/ -> clean+merge+summarize+bundle+notify produce the §3 outputs.
- [ ] LLM stages call only ctx.llm.complete; gated by skip_llm/llm.enabled; SKIPPED when ctx.llm is None.
- [ ] Idempotent (skip existing, honor ctx.force); per-item failures logged to ctx.errors; bundle FAILED on render failure.
- [ ] Raw-only pipeline (clean disabled) yields merged/raw_transcript.md + transcript-only bundle.
- [ ] api/routers/prompts.py sources defaults from lib.prompts; API surface unchanged; router tests pass.
- [ ] Full stage + router suite green (no ffmpeg/whisper/network).
EOF
)"
```

- [ ] **Step 2: Create the package markers**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k-s2
mkdir -p backend/src/steno10k/stages backend/tests/stages
printf '' > backend/src/steno10k/stages/__init__.py
printf '' > backend/tests/stages/__init__.py
```

- [ ] **Step 3: Write the shared test support module**

Create `backend/tests/stages/support.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.domain import Recording
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import Event, EventBus
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.stage import StageContext


class FakeLLM:
    """Stands in for the `contracts.llm.LLMClient` protocol in stage tests.

    `responder(system, user) -> str` computes each reply (default: echo the user
    text). Records every call for assertions. Pass a responder that raises to
    exercise per-item error isolation.
    """

    def __init__(self, responder: Callable[[str, str], str] | None = None) -> None:
        self._responder = responder or (lambda system, user: f"[out] {user}")
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._responder(system, user)


class RecordingBus(EventBus):
    """An `EventBus` that also keeps every emitted event for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[Event] = []
        self.subscribe(self.events.append)


def make_manifest(normalized_names: list[str]) -> Manifest:
    return Manifest(
        project_slug="proj",
        set_slug="set-a",
        title="Set A",
        recordings=[Recording(source_name=n, normalized_name=n) for n in normalized_names],
    )


def seed_raw(set_dir: Path, stem: str, chunks: list[str]) -> None:
    """Write transcripts_raw/<stem>/chunk_NNN.txt fixtures (S1's output shape)."""
    d = set_dir / "transcripts_raw" / stem
    d.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(chunks):
        (d / f"chunk_{i:03d}.txt").write_text(text, encoding="utf-8")


def seed_clean(set_dir: Path, stem: str, chunks: list[str]) -> None:
    """Write transcripts_clean/<stem>/chunk_NNN.md fixtures (clean's output shape)."""
    d = set_dir / "transcripts_clean" / stem
    d.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(chunks):
        (d / f"chunk_{i:03d}.md").write_text(text, encoding="utf-8")


def make_ctx(
    set_dir: Path,
    *,
    cfg: Config | None = None,
    manifest: Manifest | None = None,
    force: bool = False,
    llm: object | None = None,
    events: EventBus | None = None,
) -> StageContext:
    return StageContext(
        set_dir=set_dir,
        cfg=cfg or Config(),
        force=force,
        manifest=manifest or make_manifest(["rec-1.m4a"]),
        errors=ErrorLog(set_dir / "errors.log"),
        events=events or EventBus(),
        llm=llm,  # type: ignore[arg-type]  # FakeLLM implements the complete() protocol
    )
```

- [ ] **Step 4: Write the shared `set_dir` fixture**

A pytest *fixture* must live in a `conftest.py` to be auto-injected into tests by
name (the plain functions in `support.py` are imported explicitly instead). Every
stage test takes a `set_dir` fixture — a fresh `<data_root>/<project>/<set>` tree so
`resolve_override_dir`'s `set_dir.parent.parent` derivation is realistic.

Create `backend/tests/stages/conftest.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def set_dir(tmp_path: Path) -> Path:
    """A fresh set directory shaped like <data_root>/<project>/<set>."""
    d = tmp_path / "data" / "proj" / "set-a"
    d.mkdir(parents=True)
    return d
```

- [ ] **Step 5: Verify the support + conftest modules import**

Run: `cd backend && uv run python -c "import tests.stages.support" && uv run pytest tests/stages/ -q`
Expected: the import succeeds; pytest collects `tests/stages/` with **0 tests** (no test files yet) and exits cleanly — confirming `conftest.py` and `support.py` load without error.

- [ ] **Step 6: Commit**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k-s2
git add backend/src/steno10k/stages/__init__.py backend/tests/stages/__init__.py backend/tests/stages/support.py backend/tests/stages/conftest.py
git commit -m "chore(stages): package skeleton + shared test support (#<ISSUE>)"
```

---

## Task 1: Import-boundary guard

Enforces spec §1: `stages` imports only `lib`/`contracts`/stdlib/third-party — never `api`. Mirrors L's `test_import_boundary.py`.

**Files:**
- Test: `backend/tests/stages/test_import_boundary.py`

- [ ] **Step 1: Write the test**

Create `backend/tests/stages/test_import_boundary.py`:

```python
from __future__ import annotations

import ast
from pathlib import Path

_STAGES_DIR = Path(__file__).resolve().parents[2] / "src" / "steno10k" / "stages"
_FORBIDDEN = ("steno10k.api",)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_stages_never_import_api():
    offenders: list[str] = []
    for py in _STAGES_DIR.glob("*.py"):
        for mod in _imports(py):
            if any(mod == f or mod.startswith(f + ".") for f in _FORBIDDEN):
                offenders.append(f"{py.name} -> {mod}")
    assert offenders == [], f"stages must not import api: {offenders}"
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_import_boundary.py -v`
Expected: PASS (only `__init__.py` exists; no forbidden imports). This guard protects every later task.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/stages/test_import_boundary.py
git commit -m "test(stages): guard stages->api import boundary"
```

---

## Task 2: `stages/_pool.py` — bounded work pool

Port the reference `_run_llm_pool` (`pipeline.py`): yield `(item, result, error)` so one failing item never kills the pool. `concurrency <= 1` runs inline, in order.

**Files:**
- Create: `backend/src/steno10k/stages/_pool.py`
- Test: `backend/tests/stages/test_pool.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_pool.py`:

```python
from __future__ import annotations

import pytest

from steno10k.stages._pool import run_pool


def test_empty_items_yields_nothing():
    assert list(run_pool([], lambda x: x, concurrency=4)) == []


def test_inline_preserves_order_and_results():
    out = list(run_pool([1, 2, 3], lambda x: x * 10, concurrency=1))
    assert out == [(1, 10, None), (2, 20, None), (3, 30, None)]


def test_inline_captures_error_without_raising():
    def fn(x):
        if x == 2:
            raise ValueError("boom")
        return x

    out = list(run_pool([1, 2, 3], fn, concurrency=1))
    assert out[0] == (1, 1, None)
    item, result, err = out[1]
    assert item == 2 and result is None and isinstance(err, ValueError)
    assert out[2] == (3, 3, None)


def test_pooled_runs_all_items_and_isolates_failure():
    def fn(x):
        if x == 2:
            raise ValueError("boom")
        return x * 10

    out = {item: (result, err) for item, result, err in run_pool([1, 2, 3], fn, concurrency=3)}
    assert out[1] == (10, None)
    assert out[3] == (30, None)
    result, err = out[2]
    assert result is None and isinstance(err, ValueError)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_pool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages._pool'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/_pool.py`:

```python
from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def run_pool(
    items: list[T],
    fn: Callable[[T], R],
    concurrency: int,
) -> Iterator[tuple[T, R | None, Exception | None]]:
    """Run `fn(item)` over `items`, yielding `(item, result, error)` per item.

    `fn` is caller-supplied (LLM call + file I/O), so any failure is reported as
    the third tuple element rather than raised — one bad item cannot kill the pool.
    `concurrency <= 1` runs inline, preserving input order; otherwise a bounded
    `ThreadPoolExecutor` runs up to `concurrency` at once (completion order).
    """
    if not items:
        return
    if concurrency <= 1:
        for it in items:
            try:
                yield it, fn(it), None
            except Exception as e:  # isolation: one bad item must not kill the pool
                yield it, None, e
        return
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(fn, it): it for it in items}
        for fut in as_completed(futures):
            it = futures[fut]
            try:
                yield it, fut.result(), None
            except Exception as e:  # isolation: one bad item must not kill the pool
                yield it, None, e
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_pool.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/_pool.py backend/tests/stages/test_pool.py
git commit -m "feat(stages): bounded work pool with per-item error isolation"
```

---

## Task 3: `stages/_prompts.py` — prompt override dir resolution

A 4-line helper the LLM stages share. Resolves the prompt override directory exactly like the F2 prompts router: explicit `cfg.prompts.override_dir`, else `<data_root>/prompt_overrides`, where `data_root = set_dir.parent.parent` (`set_dir` is `<data_root>/<project>/<set>`).

**Files:**
- Create: `backend/src/steno10k/stages/_prompts.py`
- Test: `backend/tests/stages/test_prompts_helper.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_prompts_helper.py`:

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.stages._prompts import resolve_override_dir


def test_falls_back_to_data_root_prompt_overrides():
    set_dir = Path("/data/proj/set-a")
    cfg = Config()  # prompts.override_dir defaults to None
    assert resolve_override_dir(cfg, set_dir) == Path("/data/prompt_overrides")


def test_explicit_override_dir_wins():
    set_dir = Path("/data/proj/set-a")
    cfg = Config()
    cfg.prompts.override_dir = "/custom/prompts"
    assert resolve_override_dir(cfg, set_dir) == Path("/custom/prompts")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_prompts_helper.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages._prompts'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/_prompts.py`:

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config


def resolve_override_dir(cfg: Config, set_dir: Path) -> Path:
    """Prompt override directory for the LLM stages.

    Mirrors the F2 prompts router: an explicit `cfg.prompts.override_dir` wins;
    otherwise `<data_root>/prompt_overrides`, where `data_root` is the grandparent
    of `set_dir` (`<data_root>/<project>/<set>`). Overrides a user sets in the UI
    (written under the same directory) are therefore honored by the stages.
    """
    if cfg.prompts.override_dir:
        return Path(cfg.prompts.override_dir)
    return set_dir.parent.parent / "prompt_overrides"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_prompts_helper.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/_prompts.py backend/tests/stages/test_prompts_helper.py
git commit -m "feat(stages): prompt override-dir resolution (matches F2 router)"
```

---

## Task 4: `stages/clean.py` — LLM transcript cleaning

Per spec §4.1. For each recording's raw chunks, `ctx.llm.complete(prompts.clean, raw_text)` → `transcripts_clean/<stem>/chunk_NNN.md`. Pooled by `cfg.llm.concurrency`; empty raw → empty clean file (no LLM call); idempotent; per-chunk failures logged and isolated; `ctx.llm is None` → SKIPPED.

**Files:**
- Create: `backend/src/steno10k/stages/clean.py`
- Test: `backend/tests/stages/test_clean.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_clean.py`:

```python
from __future__ import annotations

from steno10k.contracts.stage import RunOptions
from steno10k.contracts.status import StageStatus
from steno10k.stages.clean import CleanStage
from tests.stages.support import FakeLLM, make_ctx, make_manifest, seed_raw


def test_name_and_deps():
    stage = CleanStage()
    assert stage.name == "clean"
    assert stage.depends_on == ["transcribe"]


def test_enabled_gates_on_llm_and_skip_llm():
    from steno10k.contracts.config import Config

    stage = CleanStage()
    cfg = Config()
    assert stage.enabled(cfg, RunOptions()) is True
    assert stage.enabled(cfg, RunOptions(skip_llm=True)) is False
    cfg.llm.enabled = False
    assert stage.enabled(cfg, RunOptions()) is False


def test_cleans_each_chunk_via_llm(set_dir):
    seed_raw(set_dir, "rec-1", ["hello raw", "second chunk"])
    llm = FakeLLM(lambda system, user: f"CLEANED::{user}")
    ctx = make_ctx(set_dir, manifest=make_manifest(["rec-1.m4a"]), llm=llm)

    result = CleanStage().run(ctx)

    assert result.status == StageStatus.OK
    assert result.stats["cleaned"] == 2
    d = set_dir / "transcripts_clean" / "rec-1"
    assert (d / "chunk_000.md").read_text(encoding="utf-8") == "CLEANED::hello raw"
    assert (d / "chunk_001.md").read_text(encoding="utf-8") == "CLEANED::second chunk"
    # System prompt is the lib.prompts clean default, user is the raw text.
    assert all(sys_ and "transcript" in sys_.lower() for sys_, _user in llm.calls)


def test_empty_raw_writes_empty_clean_without_llm_call(set_dir):
    seed_raw(set_dir, "rec-1", ["   "])
    llm = FakeLLM()
    ctx = make_ctx(set_dir, llm=llm)

    CleanStage().run(ctx)

    assert (set_dir / "transcripts_clean" / "rec-1" / "chunk_000.md").read_text(encoding="utf-8") == ""
    assert llm.calls == []  # blank chunk never hits the model


def test_idempotent_skip_unless_force(set_dir):
    seed_raw(set_dir, "rec-1", ["raw"])
    dst = set_dir / "transcripts_clean" / "rec-1" / "chunk_000.md"
    dst.parent.mkdir(parents=True)
    dst.write_text("EXISTING", encoding="utf-8")

    ctx = make_ctx(set_dir, llm=FakeLLM(lambda s, u: "NEW"))
    result = CleanStage().run(ctx)
    assert dst.read_text(encoding="utf-8") == "EXISTING"  # untouched
    assert result.stats["skipped"] == 1

    ctx_force = make_ctx(set_dir, force=True, llm=FakeLLM(lambda s, u: "NEW"))
    CleanStage().run(ctx_force)
    assert dst.read_text(encoding="utf-8") == "NEW"  # rebuilt


def test_failed_chunk_logged_and_isolated(set_dir):
    seed_raw(set_dir, "rec-1", ["good", "bad"])

    def responder(system, user):
        if user == "bad":
            raise RuntimeError("model exploded")
        return f"ok:{user}"

    ctx = make_ctx(set_dir, llm=FakeLLM(responder))
    ctx.cfg.llm.concurrency = 1  # deterministic ordering for the assertion
    result = CleanStage().run(ctx)

    assert result.status == StageStatus.OK
    assert result.stats["cleaned"] == 1
    assert result.stats["failed"] == 1
    assert ctx.errors.count == 1
    assert (set_dir / "transcripts_clean" / "rec-1" / "chunk_000.md").exists()
    assert not (set_dir / "transcripts_clean" / "rec-1" / "chunk_001.md").exists()


def test_no_llm_client_skips(set_dir):
    seed_raw(set_dir, "rec-1", ["raw"])
    ctx = make_ctx(set_dir, llm=None)
    result = CleanStage().run(ctx)
    assert result.status == StageStatus.SKIPPED
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_clean.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.clean'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/clean.py`:

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.prompts import load_prompts
from steno10k.stages._pool import run_pool
from steno10k.stages._prompts import resolve_override_dir


class CleanStage:
    """LLM-cleans each raw chunk transcript into a Markdown clean transcript."""

    name = StageName.CLEAN
    depends_on = [StageName.TRANSCRIBE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return cfg.llm.enabled and not opts.skip_llm

    def run(self, ctx: StageContext) -> StageResult:
        if ctx.llm is None:
            return StageResult(StageStatus.SKIPPED, message="no LLM client")

        system = load_prompts(resolve_override_dir(ctx.cfg, ctx.set_dir)).clean

        targets: list[tuple[Path, Path]] = []  # (raw_txt, clean_md)
        skipped = 0
        for rec in ctx.manifest.recordings:
            stem = Path(rec.normalized_name).stem
            raw_dir = ctx.set_dir / "transcripts_raw" / stem
            if not raw_dir.is_dir():
                continue
            for raw in sorted(raw_dir.glob("chunk_*.txt")):
                clean_md = ctx.set_dir / "transcripts_clean" / stem / f"{raw.stem}.md"
                if clean_md.exists() and not ctx.force:
                    skipped += 1
                    continue
                targets.append((raw, clean_md))

        llm = ctx.llm

        def _do(item: tuple[Path, Path]) -> str:
            raw, _dst = item
            text = raw.read_text(encoding="utf-8").strip()
            if not text:
                return ""
            return llm.complete(system, text)

        cleaned = 0
        failed = 0
        for (raw, dst), result, err in run_pool(targets, _do, ctx.cfg.llm.concurrency):
            if err is not None:
                ctx.errors.log("clean", str(raw), err)
                failed += 1
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(result or "", encoding="utf-8")
            cleaned += 1

        return StageResult(
            StageStatus.OK,
            stats={"cleaned": cleaned, "skipped": skipped, "failed": failed},
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_clean.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/clean.py backend/tests/stages/test_clean.py
git commit -m "feat(stages): clean stage (LLM per-chunk transcript cleaning)"
```

---

## Task 5: `stages/merge.py` — assemble merged transcripts

Per spec §4.2. Concatenate per-recording chunk transcripts into `merged/raw_transcript.md` and `merged/clean_transcript.md`, each gated by its `output.save_merged_*` flag. Always rewrites (cheap, deterministic). Read failures logged. Depends on `transcribe` (not `clean`) so a raw-only run is valid.

**Files:**
- Create: `backend/src/steno10k/stages/merge.py`
- Test: `backend/tests/stages/test_merge.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_merge.py`:

```python
from __future__ import annotations

from steno10k.contracts.status import StageStatus
from steno10k.stages.merge import MergeStage
from tests.stages.support import make_ctx, make_manifest, seed_clean, seed_raw


def test_name_and_deps():
    stage = MergeStage()
    assert stage.name == "merge"
    assert stage.depends_on == ["transcribe"]


def test_merges_raw_and_clean(set_dir):
    seed_raw(set_dir, "rec-1", ["raw a", "raw b"])
    seed_clean(set_dir, "rec-1", ["clean a", "clean b"])
    ctx = make_ctx(set_dir, manifest=make_manifest(["rec-1.m4a"]))

    result = MergeStage().run(ctx)

    assert result.status == StageStatus.OK
    raw_md = (set_dir / "merged" / "raw_transcript.md").read_text(encoding="utf-8")
    clean_md = (set_dir / "merged" / "clean_transcript.md").read_text(encoding="utf-8")
    assert "## rec-1" in raw_md and "### chunk_000" in raw_md
    assert "raw a" in raw_md and "raw b" in raw_md
    assert "clean a" in clean_md and "clean b" in clean_md


def test_raw_only_when_clean_disabled(set_dir):
    seed_raw(set_dir, "rec-1", ["only raw"])
    ctx = make_ctx(set_dir)
    ctx.cfg.output.save_merged_clean_transcript = False

    result = MergeStage().run(ctx)

    assert (set_dir / "merged" / "raw_transcript.md").exists()
    assert not (set_dir / "merged" / "clean_transcript.md").exists()
    assert result.stats == {"raw": 1, "clean": 0}


def test_recording_order_follows_manifest(set_dir):
    seed_raw(set_dir, "b-rec", ["from b"])
    seed_raw(set_dir, "a-rec", ["from a"])
    ctx = make_ctx(set_dir, manifest=make_manifest(["b-rec.m4a", "a-rec.m4a"]))

    MergeStage().run(ctx)

    raw_md = (set_dir / "merged" / "raw_transcript.md").read_text(encoding="utf-8")
    assert raw_md.index("## b-rec") < raw_md.index("## a-rec")


def test_no_inputs_writes_nothing(set_dir):
    ctx = make_ctx(set_dir)
    result = MergeStage().run(ctx)
    assert not (set_dir / "merged" / "raw_transcript.md").exists()
    assert result.stats == {"raw": 0, "clean": 0}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_merge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.merge'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/merge.py`:

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


class MergeStage:
    """Concatenates per-recording chunk transcripts into single Markdown files."""

    name = StageName.MERGE
    depends_on = [StageName.TRANSCRIBE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        stems = [Path(r.normalized_name).stem for r in ctx.manifest.recordings]
        merged_dir = ctx.set_dir / "merged"

        wrote_raw = 0
        wrote_clean = 0
        if ctx.cfg.output.save_merged_raw_transcript:
            wrote_raw = int(
                self._merge(ctx, stems, "transcripts_raw", "chunk_*.txt", merged_dir / "raw_transcript.md")
            )
        if ctx.cfg.output.save_merged_clean_transcript:
            wrote_clean = int(
                self._merge(ctx, stems, "transcripts_clean", "chunk_*.md", merged_dir / "clean_transcript.md")
            )
        return StageResult(StageStatus.OK, stats={"raw": wrote_raw, "clean": wrote_clean})

    def _merge(
        self, ctx: StageContext, stems: list[str], subdir: str, glob: str, dst: Path
    ) -> bool:
        parts: list[str] = []
        for stem in stems:
            d = ctx.set_dir / subdir / stem
            if not d.is_dir():
                continue
            files = sorted(d.glob(glob))
            if not files:
                continue
            parts.append(f"\n\n## {stem}\n")
            for f in files:
                parts.append(f"\n### {f.stem}\n")
                try:
                    parts.append(f.read_text(encoding="utf-8").strip())
                except (OSError, UnicodeDecodeError) as e:
                    ctx.errors.log("merge", str(f), e)
        if not parts:
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
        return True
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_merge.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/merge.py backend/tests/stages/test_merge.py
git commit -m "feat(stages): merge stage (assemble raw + clean transcripts)"
```

---

## Task 6: `stages/summarize.py` — LLM summary

Per spec §4.3. Read `merged/clean_transcript.md`; format the `summarize` prompt with `cfg.prompts.target_output_language`; write `ctx.llm.complete(...)` to `cfg.output.summary_filename`. Missing/empty transcript → FAILED. Idempotent; `ctx.llm is None` → SKIPPED.

**Files:**
- Create: `backend/src/steno10k/stages/summarize.py`
- Test: `backend/tests/stages/test_summarize.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_summarize.py`:

```python
from __future__ import annotations

from steno10k.contracts.status import StageStatus
from steno10k.stages.summarize import SummarizeStage
from tests.stages.support import FakeLLM, make_ctx


def _seed_merged_clean(set_dir, text: str) -> None:
    d = set_dir / "merged"
    d.mkdir(parents=True, exist_ok=True)
    (d / "clean_transcript.md").write_text(text, encoding="utf-8")


def test_name_and_deps():
    stage = SummarizeStage()
    assert stage.name == "summarize"
    assert stage.depends_on == ["merge", "clean"]


def test_writes_summary_from_merged_clean(set_dir):
    _seed_merged_clean(set_dir, "the full clean transcript")
    llm = FakeLLM(lambda system, user: f"SUMMARY of: {user}")
    ctx = make_ctx(set_dir, llm=llm)

    result = SummarizeStage().run(ctx)

    assert result.status == StageStatus.OK
    summary = (set_dir / "summary.md").read_text(encoding="utf-8")
    assert summary == "SUMMARY of: the full clean transcript\n"
    # Target output language is threaded into the system prompt.
    system, user = llm.calls[0]
    assert "en" in system and user == "the full clean transcript"


def test_target_language_is_formatted_into_prompt(set_dir):
    _seed_merged_clean(set_dir, "text")
    llm = FakeLLM()
    ctx = make_ctx(set_dir, llm=llm)
    ctx.cfg.prompts.target_output_language = "French"

    SummarizeStage().run(ctx)

    system, _user = llm.calls[0]
    assert "French" in system
    assert "{target_output_language}" not in system  # placeholder was substituted


def test_custom_summary_filename(set_dir):
    _seed_merged_clean(set_dir, "text")
    ctx = make_ctx(set_dir, llm=FakeLLM(lambda s, u: "S"))
    ctx.cfg.output.summary_filename = "notes.md"

    SummarizeStage().run(ctx)

    assert (set_dir / "notes.md").exists()
    assert not (set_dir / "summary.md").exists()


def test_missing_transcript_fails(set_dir):
    ctx = make_ctx(set_dir, llm=FakeLLM())
    result = SummarizeStage().run(ctx)
    assert result.status == StageStatus.FAILED
    assert ctx.errors.count == 1


def test_empty_transcript_fails(set_dir):
    _seed_merged_clean(set_dir, "   ")
    ctx = make_ctx(set_dir, llm=FakeLLM())
    result = SummarizeStage().run(ctx)
    assert result.status == StageStatus.FAILED


def test_idempotent_skip_unless_force(set_dir):
    _seed_merged_clean(set_dir, "text")
    (set_dir / "summary.md").write_text("EXISTING", encoding="utf-8")

    ctx = make_ctx(set_dir, llm=FakeLLM(lambda s, u: "NEW"))
    result = SummarizeStage().run(ctx)
    assert (set_dir / "summary.md").read_text(encoding="utf-8") == "EXISTING"
    assert result.stats.get("skipped") == 1

    ctx_force = make_ctx(set_dir, force=True, llm=FakeLLM(lambda s, u: "NEW"))
    SummarizeStage().run(ctx_force)
    assert (set_dir / "summary.md").read_text(encoding="utf-8") == "NEW\n"


def test_no_llm_client_skips(set_dir):
    _seed_merged_clean(set_dir, "text")
    ctx = make_ctx(set_dir, llm=None)
    assert SummarizeStage().run(ctx).status == StageStatus.SKIPPED
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_summarize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.summarize'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/summarize.py`:

```python
from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.prompts import load_prompts
from steno10k.stages._prompts import resolve_override_dir


class SummarizeStage:
    """Produces the summary document from the merged clean transcript via the LLM."""

    name = StageName.SUMMARIZE
    depends_on = [StageName.MERGE, StageName.CLEAN]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return cfg.llm.enabled and not opts.skip_llm

    def run(self, ctx: StageContext) -> StageResult:
        if ctx.llm is None:
            return StageResult(StageStatus.SKIPPED, message="no LLM client")

        dst = ctx.set_dir / ctx.cfg.output.summary_filename
        if dst.exists() and not ctx.force:
            return StageResult(StageStatus.OK, stats={"skipped": 1})

        transcript_path = ctx.set_dir / "merged" / "clean_transcript.md"
        if not transcript_path.is_file():
            ctx.errors.log("summarize", ctx.manifest.set_slug, "merged/clean_transcript.md missing")
            return StageResult(StageStatus.FAILED, message="clean transcript missing")
        transcript = transcript_path.read_text(encoding="utf-8").strip()
        if not transcript:
            ctx.errors.log("summarize", ctx.manifest.set_slug, "clean transcript empty")
            return StageResult(StageStatus.FAILED, message="clean transcript empty")

        prompts = load_prompts(resolve_override_dir(ctx.cfg, ctx.set_dir))
        system = prompts.summarize.format(
            target_output_language=ctx.cfg.prompts.target_output_language
        )
        summary = ctx.llm.complete(system, transcript)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(summary + "\n", encoding="utf-8")
        return StageResult(StageStatus.OK, stats={"chars": len(summary)})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_summarize.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/summarize.py backend/tests/stages/test_summarize.py
git commit -m "feat(stages): summarize stage (LLM summary from merged clean transcript)"
```

---

## Task 7: `stages/bundle.py` — render `.docx` bundles

Per spec §4.4. Call `lib.docx.build_bundle` over two fixed pairs under `bundle/`: `merged/clean_transcript.md → transcript.docx`, `<summary_filename> → summary.docx`. Missing source skipped silently (transcript-only bundle valid). FAILED iff `ctx.errors.count` rose during the render. Gated by `output.save_bundle_docx`.

**Files:**
- Create: `backend/src/steno10k/stages/bundle.py`
- Test: `backend/tests/stages/test_bundle.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_bundle.py`:

```python
from __future__ import annotations

from docx import Document

from steno10k.contracts.config import Config
from steno10k.contracts.stage import RunOptions
from steno10k.contracts.status import StageStatus
from steno10k.stages.bundle import BundleStage
from tests.stages.support import make_ctx


def _seed(set_dir, *, clean=None, summary=None) -> None:
    if clean is not None:
        (set_dir / "merged").mkdir(parents=True, exist_ok=True)
        (set_dir / "merged" / "clean_transcript.md").write_text(clean, encoding="utf-8")
    if summary is not None:
        (set_dir / "summary.md").write_text(summary, encoding="utf-8")


def test_name_and_deps():
    stage = BundleStage()
    assert stage.name == "bundle"
    assert stage.depends_on == ["merge"]


def test_enabled_gates_on_save_bundle_docx():
    stage = BundleStage()
    cfg = Config()
    assert stage.enabled(cfg, RunOptions()) is True
    cfg.output.save_bundle_docx = False
    assert stage.enabled(cfg, RunOptions()) is False


def test_builds_both_docx(set_dir):
    _seed(set_dir, clean="# Transcript\n\nBody.", summary="# Summary\n\nPoints.")
    result = BundleStage().run(set_dir_ctx := make_ctx(set_dir))

    assert result.status == StageStatus.OK
    assert result.stats["built"] == 2
    transcript = set_dir / "bundle" / "transcript.docx"
    summary = set_dir / "bundle" / "summary.docx"
    assert transcript.is_file() and summary.is_file()
    assert any(p.text == "Transcript" for p in Document(str(transcript)).paragraphs)
    assert set_dir_ctx.errors.count == 0


def test_missing_summary_yields_transcript_only(set_dir):
    _seed(set_dir, clean="# Transcript\n\nBody.")  # no summary.md
    ctx = make_ctx(set_dir)

    result = BundleStage().run(ctx)

    assert result.status == StageStatus.OK
    assert (set_dir / "bundle" / "transcript.docx").is_file()
    assert not (set_dir / "bundle" / "summary.docx").exists()
    assert result.stats["built"] == 1


def test_render_failure_reports_failed(set_dir, monkeypatch):
    import steno10k.lib.docx as docxmod

    _seed(set_dir, clean="# Transcript\n\nBody.", summary="# Summary")

    def boom(source, dst, force):
        raise RuntimeError("render exploded")

    monkeypatch.setattr(docxmod, "_build_one", boom)
    ctx = make_ctx(set_dir)

    result = BundleStage().run(ctx)

    assert result.status == StageStatus.FAILED
    assert ctx.errors.count >= 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_bundle.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.bundle'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/bundle.py`:

```python
from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.docx import build_bundle


class BundleStage:
    """Renders the merged clean transcript and the summary to `.docx` files."""

    name = StageName.BUNDLE
    depends_on = [StageName.MERGE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return cfg.output.save_bundle_docx

    def run(self, ctx: StageContext) -> StageResult:
        bundle_dir = ctx.set_dir / "bundle"
        pairs = [
            (ctx.set_dir / "merged" / "clean_transcript.md", bundle_dir / "transcript.docx"),
            (ctx.set_dir / ctx.cfg.output.summary_filename, bundle_dir / "summary.docx"),
        ]

        before = ctx.errors.count
        build_bundle(pairs, ctx.force, ctx.errors)
        built = sum(1 for _src, dst in pairs if dst.is_file())

        if ctx.errors.count > before:
            return StageResult(
                StageStatus.FAILED, stats={"built": built}, message="one or more bundle files failed"
            )
        return StageResult(StageStatus.OK, stats={"built": built})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_bundle.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/bundle.py backend/tests/stages/test_bundle.py
git commit -m "feat(stages): bundle stage (render transcript + summary to docx)"
```

---

## Task 8: `stages/notify.py` — emit-only completion signal

Per spec §4.5. Collect the produced artifact paths (relative to `set_dir`) and emit `Event(EventKind.STAGE_PROGRESS, payload={"stage": "notify", "artifacts": [...]})` via `ctx.events`. Return `StageResult(OK, stats={"artifacts": <count>})`. No external sink (Telegram deferred).

**Files:**
- Create: `backend/src/steno10k/stages/notify.py`
- Test: `backend/tests/stages/test_notify.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_notify.py`:

```python
from __future__ import annotations

from steno10k.contracts.events import EventKind
from steno10k.contracts.status import StageStatus
from steno10k.stages.notify import NotifyStage
from tests.stages.support import RecordingBus, make_ctx


def _touch(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_name_and_deps():
    stage = NotifyStage()
    assert stage.name == "notify"
    assert stage.depends_on == ["bundle"]


def test_emits_artifact_list_and_counts(set_dir):
    _touch(set_dir / "merged" / "clean_transcript.md")
    _touch(set_dir / "summary.md")
    _touch(set_dir / "bundle" / "transcript.docx")
    _touch(set_dir / "bundle" / "summary.docx")
    bus = RecordingBus()
    ctx = make_ctx(set_dir, events=bus)

    result = NotifyStage().run(ctx)

    assert result.status == StageStatus.OK
    assert result.stats["artifacts"] == 4
    progress = [e for e in bus.events if e.kind == EventKind.STAGE_PROGRESS]
    assert len(progress) == 1
    payload = progress[0].payload
    assert payload["stage"] == "notify"
    assert set(payload["artifacts"]) == {
        "merged/clean_transcript.md",
        "summary.md",
        "bundle/transcript.docx",
        "bundle/summary.docx",
    }


def test_only_lists_existing_artifacts(set_dir):
    _touch(set_dir / "summary.md")  # nothing else produced
    bus = RecordingBus()
    ctx = make_ctx(set_dir, events=bus)

    result = NotifyStage().run(ctx)

    assert result.stats["artifacts"] == 1
    payload = next(e for e in bus.events if e.kind == EventKind.STAGE_PROGRESS).payload
    assert payload["artifacts"] == ["summary.md"]


def test_honors_custom_summary_filename(set_dir):
    _touch(set_dir / "notes.md")
    bus = RecordingBus()
    ctx = make_ctx(set_dir, events=bus)
    ctx.cfg.output.summary_filename = "notes.md"

    NotifyStage().run(ctx)

    payload = next(e for e in bus.events if e.kind == EventKind.STAGE_PROGRESS).payload
    assert "notes.md" in payload["artifacts"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_notify.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.notify'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/notify.py`:

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


class NotifyStage:
    """Terminal emit-only stage: announces the produced artifacts as an event.

    No external sink (Telegram is deferred to M3+). Subscribers (SSE bridge, future
    Telegram) read the emitted `STAGE_PROGRESS` event's `artifacts` payload.
    """

    name = StageName.NOTIFY
    depends_on = [StageName.BUNDLE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        candidates = [
            ctx.set_dir / "merged" / "raw_transcript.md",
            ctx.set_dir / "merged" / "clean_transcript.md",
            ctx.set_dir / ctx.cfg.output.summary_filename,
            ctx.set_dir / "bundle" / "transcript.docx",
            ctx.set_dir / "bundle" / "summary.docx",
        ]
        artifacts = [p.relative_to(ctx.set_dir).as_posix() for p in candidates if p.is_file()]
        ctx.events.emit(
            Event(kind=EventKind.STAGE_PROGRESS, payload={"stage": "notify", "artifacts": artifacts})
        )
        return StageResult(StageStatus.OK, stats={"artifacts": len(artifacts)})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_notify.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/notify.py backend/tests/stages/test_notify.py
git commit -m "feat(stages): notify stage (emit-only artifacts event)"
```

---

## Task 9: Rewire the F2 prompts router onto `lib.prompts`

Per spec §6. Replace the placeholder `DEFAULT_PROMPTS` dict with `lib.prompts` (`default_prompt`, `PROMPT_NAMES`). **The API surface stays byte-identical** — same routes, `PromptDTO`, and `source` values; only the default text + its source module change. No DTO/OpenAPI change → no contract lock; still check the locks dir first.

**Files:**
- Modify: `backend/src/steno10k/api/routers/prompts.py`
- Modify: `backend/tests/api/test_config_prompts.py`

- [ ] **Step 1: Check for an active contract lock**

Run: `ls ~/.claude/locks/steno10k/ 2>/dev/null`
Expected: no lock file covering `api/` (only the unrelated `adr-numbering.lock.md` may exist). If a lock covers the prompts router / API surface, **stop and wait** per AGENTS.md. Proceed only when clear.

- [ ] **Step 2: Update the router test to assert against `lib.prompts` defaults**

In `backend/tests/api/test_config_prompts.py`, any assertion that pins the old placeholder default text must target the `lib.prompts` default. Add this import near the top:

```python
from steno10k.lib.prompts import PROMPT_NAMES, default_prompt
```

Replace any hard-coded expected default string for a prompt (e.g. an assertion like `assert body["content"] == "Clean up this raw transcript chunk: ..."`) with:

```python
    assert body["content"] == default_prompt("clean")
```

And any assertion enumerating the known prompt names (e.g. `{"clean", "summarize"}`) with:

```python
    assert {p["name"] for p in items} == set(PROMPT_NAMES)
```

Leave the list/put/reset behavior, `source` values (`"default"`/`"override"`), and status-code assertions unchanged — the surface does not move.

- [ ] **Step 3: Run the router test to verify it now fails**

Run: `cd backend && uv run pytest tests/api/test_config_prompts.py -v`
Expected: FAIL — the router still returns the old placeholder text, so the new `default_prompt(...)` assertions mismatch.

- [ ] **Step 4: Rewire the router implementation**

In `backend/src/steno10k/api/routers/prompts.py`:

Add the import:

```python
from steno10k.lib.prompts import PROMPT_NAMES, default_prompt
```

Delete the `DEFAULT_PROMPTS` dict (the whole `DEFAULT_PROMPTS: dict[str, str] = { ... }` block and its explanatory comment). Then update the three references:

- In `_dto`, replace `content=DEFAULT_PROMPTS[name]` with `content=default_prompt(name)`.
- In `_require_known`, replace `if name not in DEFAULT_PROMPTS:` with `if name not in PROMPT_NAMES:`.
- In `list_prompts`, replace `for name in sorted(DEFAULT_PROMPTS)` with `for name in sorted(PROMPT_NAMES)`.

The `PromptDTO`, routes, `_override_dir`/`_override_path` helpers, and `source` values are untouched.

- [ ] **Step 5: Run the router test + the DTO/OpenAPI surface tests to verify green**

Run: `cd backend && uv run pytest tests/api/test_config_prompts.py tests/api/test_dto.py -v`
Expected: PASS. The prompts-router behavior matches `lib.prompts` defaults; DTO/OpenAPI surface tests are unaffected (surface unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/src/steno10k/api/routers/prompts.py backend/tests/api/test_config_prompts.py
git commit -m "refactor(api): source prompt defaults from lib.prompts (surface unchanged)"
```

---

## Task 10: Full-suite verification, lint, types, PR

Confirm the whole unit is green under the repo's gates and open the PR.

**Files:** none (verification + PR).

- [ ] **Step 1: Run the full backend test suite**

Run: `cd backend && uv run pytest -q`
Expected: PASS — all `tests/stages/*`, the rewired `tests/api/test_config_prompts.py`, and every pre-existing suite. No ffmpeg/whisper/network needed.

- [ ] **Step 2: Lint + type-check (repo gates)**

Run: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src`
Expected: clean. If mypy flags the `FakeLLM`/`llm` protocol assignment in tests, the `# type: ignore[arg-type]` in `make_ctx` (Task 0) covers it; do not weaken `src` typing.

- [ ] **Step 3: Run the repo pre-commit gate**

Run: `cd /Users/vladyslavbardin/Docs/Personal/steno10k-s2 && pre-commit run --all-files`
Expected: all hooks pass (per AGENTS.md "Before pushing").

- [ ] **Step 4: Push the branch**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k-s2
git push -u origin feat/m1-s2-llm-assembly-stages
```

- [ ] **Step 5: Open the PR**

```bash
gh pr create --fill --base main \
  --title "M1·S2: LLM + assembly stages (clean, merge, summarize, bundle, notify)" \
  --body "$(cat <<'EOF'
Implements M1·S2 — the LLM + assembly stages under steno10k/stages/, plus the F2 prompts-router rewiring onto lib.prompts.

Closes #<ISSUE>

Spec: docs/specs/2026-07-11-steno10k-m1-s2-llm-assembly-stages-design.md
Plan: docs/plans/2026-07-12-m1-s2-llm-assembly-stages.md

- Five Stage implementations (clean, merge, summarize, bundle, notify) on the F1 Stage protocol; depends_on matches api/stages.py::STAGE_DEPS.
- stages -> lib/contracts only (import-boundary guard); registry wiring + RunOptions threading remain M1·W.
- Prompts router now sources defaults from lib.prompts with the API surface unchanged (no contract lock).
- Full stage + router suite green (no ffmpeg/whisper/network).
EOF
)"
```

- [ ] **Step 6: Confirm CI is green**

Run: `gh pr checks --watch`
Expected: all required checks pass. Address any failures before requesting review. PRs are squash-merged (AGENTS.md).

---

## Notes for the executor

- **Fill `#<ISSUE>`** everywhere from Task 0's `gh issue create` output.
- **`depends_on` must stay identical to `api/stages.py::STAGE_DEPS`** (clean←transcribe, merge←transcribe, summarize←[merge,clean], bundle←merge, notify←bundle). If a test of a `depends_on` value fails, fix the stage to match `STAGE_DEPS` — never edit the frozen `STAGE_DEPS`.
- **Do not touch** `contracts/`, `api/` DTOs/OpenAPI, or the runner. The only `api/` edit is the internal prompts-router source swap (Task 9), which leaves the surface byte-identical.
- **Test wiring:** the `set_dir` fixture lives in `tests/stages/conftest.py` (auto-injected by name); `FakeLLM`, `RecordingBus`, `make_ctx`, `make_manifest`, `seed_raw`, `seed_clean` are imported explicitly from `tests.stages.support`.
