# M1·S1 — Heavy Stages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `normalize`, `chunk`, and `transcribe` pipeline stages as concrete `Stage` implementations in a new `steno10k/stages/` package, orchestrating the merged `steno10k/lib/` capabilities over the F1 `StageContext`.

**Architecture:** Each stage is a thin adapter — it holds no media/transcription logic, only wiring: read `ctx.manifest.recordings`, call `lib.ffmpeg`/`lib.transcriber`, mutate the manifest, emit progress, isolate per-item failures to `ctx.errors`. A shared `_scope.in_run_scope` helper implements the `only`/`from_stage` gate for every stage. Registry wiring (`build_registry()`) and API run-option passthrough are explicitly **out of scope** (M1·W), so stages are verified by direct unit tests plus binary-gated integration tests.

**Tech Stack:** Python 3.12, `steno10k.lib` (ffmpeg + faster-whisper wrappers, already merged), pytest, mypy (strict), ruff. `ffmpeg` system binary for integration tests only.

**Spec:** `docs/specs/2026-07-11-steno10k-m1-s1-heavy-stages-design.md`.

**Depends on:** M1·L — **merged** to `main` (`#14`, `c89b23f`). This plan's branch starts from current `origin/main`, which already contains `steno10k/lib/`.

---

## File Structure

Created under `backend/`:

- `src/steno10k/stages/__init__.py` — package marker.
- `src/steno10k/stages/_scope.py` — `in_run_scope(name, opts)` run-option gate (shared by S1 + S2).
- `src/steno10k/stages/normalize.py` — `NormalizeStage`: validate + probe durations.
- `src/steno10k/stages/chunk.py` — `ChunkStage`: `plan_chunks` + `extract_chunk` into `chunks/<stem>/`.
- `src/steno10k/stages/transcribe.py` — `TranscribeStage`: `transcribe_chunks` into `transcripts_raw/<stem>/`.
- `tests/stages/__init__.py` — test package marker.
- `tests/stages/conftest.py` — `make_ctx` fixture (builds `StageContext` + captures events).
- `tests/stages/test_scope.py`, `test_normalize.py`, `test_chunk.py`, `test_transcribe.py`.

Layering guardrail: `stages` imports only `steno10k.lib` and `steno10k.contracts` — never `steno10k.api`.

---

## Task 0: Ticket, branch, package skeleton

Per AGENTS.md: **one issue → one branch → one PR**, branch `<type>/<issue>-<slug>` (no `#`).

**Files:**
- Create: `backend/src/steno10k/stages/__init__.py`
- Create: `backend/tests/stages/__init__.py`

- [ ] **Step 1: Create the GitHub issue**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k/.claude/worktrees/feat+m1-s1-heavy-stages
ISSUE_URL=$(gh issue create \
  --title "M1·S1: heavy stages (normalize, chunk, transcribe)" \
  --label "area:backend,type:feat" \
  --body "$(cat <<'EOF'
Implements the M1·S1 fan-out unit — the three compute-heavy pipeline stages.

Spec: docs/specs/2026-07-11-steno10k-m1-s1-heavy-stages-design.md
Plan: docs/plans/2026-07-11-m1-s1-heavy-stages.md
Umbrella: docs/specs/2026-07-11-steno10k-m1-decomposition-design.md

Acceptance (spec §8):
- [ ] steno10k/stages/ has normalize/chunk/transcribe satisfying the F1 Stage protocol; stages import only lib/contracts.
- [ ] normalize records duration_seconds, fails fast without ffmpeg, skips missing files.
- [ ] chunk writes chunks/<stem>/chunk_{i:03d}.<fmt>, populates recording.chunks, idempotent unless force.
- [ ] transcribe writes transcripts_raw/<stem>/<chunk>.txt, parallel, injects M1 decode knobs, isolates per-chunk failures.
- [ ] All stages emit STAGE_PROGRESS and honor only/from_stage via in_run_scope.
- [ ] Logic tests pass with no binaries; binary tests skip cleanly.
- [ ] build_registry() untouched (left to M1·W); no frozen contract changed.
EOF
)")
echo "Created: $ISSUE_URL"
ISSUE=$(basename "$ISSUE_URL")
echo "Issue number: $ISSUE"
```

- [ ] **Step 2: Create the feature branch from current origin/main (has L)**

```bash
git fetch origin --quiet
git checkout -b "feat/${ISSUE}-s1-heavy-stages" origin/main
```

- [ ] **Step 3: Create the package markers**

```bash
mkdir -p backend/src/steno10k/stages backend/tests/stages
printf '' > backend/src/steno10k/stages/__init__.py
printf '' > backend/tests/stages/__init__.py
```

- [ ] **Step 4: Verify the clean baseline**

Run: `cd backend && uv run pytest -q`
Expected: the existing suite passes (L + F1/F2/F3 tests), confirming the environment resolves `faster-whisper`/`openai`/`python-docx`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/__init__.py backend/tests/stages/__init__.py
git commit -m "chore(stages): add stages package skeleton (#${ISSUE})"
```

---

## Task 1: `stages/_scope.py` — run-option gate

Shared `enabled()` logic: `only` selects a single stage; `from_stage` selects that stage and every later one in `StageName` declaration order; otherwise everything is in scope.

**Files:**
- Create: `backend/src/steno10k/stages/_scope.py`
- Test: `backend/tests/stages/test_scope.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions
from steno10k.stages._scope import in_run_scope


def test_default_all_in_scope() -> None:
    assert in_run_scope(StageName.CHUNK, RunOptions()) is True


def test_only_matches_single_stage() -> None:
    opts = RunOptions(only=StageName.CHUNK)
    assert in_run_scope(StageName.CHUNK, opts) is True
    assert in_run_scope(StageName.TRANSCRIBE, opts) is False


def test_from_stage_includes_self_and_later() -> None:
    opts = RunOptions(from_stage=StageName.CHUNK)
    assert in_run_scope(StageName.NORMALIZE, opts) is False
    assert in_run_scope(StageName.CHUNK, opts) is True
    assert in_run_scope(StageName.TRANSCRIBE, opts) is True


def test_only_takes_precedence_over_from_stage() -> None:
    opts = RunOptions(only=StageName.NORMALIZE, from_stage=StageName.TRANSCRIBE)
    assert in_run_scope(StageName.NORMALIZE, opts) is True
    assert in_run_scope(StageName.TRANSCRIBE, opts) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_scope.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages._scope'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/_scope.py`:

```python
from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions

# Canonical stage order = StageName declaration order.
_ORDER: list[StageName] = list(StageName)


def in_run_scope(name: StageName, opts: RunOptions) -> bool:
    """Whether `name` is in scope for this run given the run options.

    `only` wins over everything (single-stage run). Otherwise `from_stage`
    selects that stage and every later stage in canonical order. With neither
    set, every stage is in scope. (Config `stages.enabled` and its cascade are
    resolved separately by the generic `run_set` before `enabled` is called.)
    """
    if opts.only is not None:
        return name == opts.only
    if opts.from_stage is not None:
        return _ORDER.index(name) >= _ORDER.index(opts.from_stage)
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_scope.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/_scope.py backend/tests/stages/test_scope.py
git commit -m "feat(stages): shared only/from_stage run-scope gate"
```

---

## Task 2: `tests/stages/conftest.py` + `stages/normalize.py`

The `make_ctx` fixture is created here (first stage that needs it) and reused by Tasks 3–4. `NormalizeStage` fails fast without ffmpeg, else probes durations onto the manifest with per-recording isolation.

**Files:**
- Create: `backend/tests/stages/conftest.py`
- Create: `backend/src/steno10k/stages/normalize.py`
- Test: `backend/tests/stages/test_normalize.py`

- [ ] **Step 1: Write the shared fixture**

Create `backend/tests/stages/conftest.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from steno10k.contracts.config import Config
from steno10k.contracts.domain import Recording
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import Event, EventBus
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.stage import StageContext

MakeCtx = Callable[..., tuple[StageContext, list[Event]]]


@pytest.fixture
def make_ctx(tmp_path: Path) -> MakeCtx:
    """Factory: build a StageContext over `tmp_path` and capture emitted events.

    Usage: `ctx, events = make_ctx([Recording(...)], force=True)`. `set_dir` is
    always `tmp_path`, so tests place source files / chunks under `tmp_path`.
    """

    def _make(
        recordings: list[Recording],
        *,
        force: bool = False,
        cfg: Config | None = None,
    ) -> tuple[StageContext, list[Event]]:
        manifest = Manifest(project_slug="p", set_slug="s", title="S", recordings=recordings)
        bus = EventBus()
        events: list[Event] = []
        bus.subscribe(events.append)
        ctx = StageContext(
            set_dir=tmp_path,
            cfg=cfg or Config(),
            force=force,
            manifest=manifest,
            errors=ErrorLog(tmp_path / "errors.log"),
            events=bus,
            llm=None,
        )
        return ctx, events

    return _make
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/stages/test_normalize.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

import steno10k.stages.normalize as normalize_mod
from steno10k.contracts.domain import Recording
from steno10k.contracts.events import EventKind
from steno10k.contracts.status import StageStatus
from steno10k.lib.ffmpeg import FFmpegError
from steno10k.stages.normalize import NormalizeStage
from stages.conftest import MakeCtx


def test_ffmpeg_missing_fails_fast(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise FFmpegError("no ffmpeg")

    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", boom)
    ctx, _ = make_ctx([Recording(source_name="a.m4a", normalized_name="a.m4a")])
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.FAILED
    assert ctx.errors.count == 1


def test_probes_duration_and_records_on_manifest(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(normalize_mod, "get_duration_seconds", lambda p: 123.0)
    rec = Recording(source_name="a.m4a", normalized_name="a.m4a")
    ctx, events = make_ctx([rec])
    (ctx.set_dir / "a.m4a").write_bytes(b"x")
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert rec.duration_seconds == 123.0
    assert result.stats == {"recordings": 1}
    assert any(e.kind is EventKind.STAGE_PROGRESS for e in events)


def test_missing_source_is_logged_not_fatal(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(normalize_mod, "get_duration_seconds", lambda p: 10.0)
    present = Recording(source_name="a.m4a", normalized_name="a.m4a")
    missing = Recording(source_name="b.m4a", normalized_name="b.m4a")
    ctx, _ = make_ctx([present, missing])
    (ctx.set_dir / "a.m4a").write_bytes(b"x")
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK  # sibling survived
    assert present.duration_seconds == 10.0
    assert missing.duration_seconds is None
    assert ctx.errors.count == 1
    assert result.stats == {"recordings": 1}


def test_probe_error_is_isolated(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def flaky(p: Path) -> float:
        raise RuntimeError("probe blew up")

    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(normalize_mod, "get_duration_seconds", flaky)
    rec = Recording(source_name="a.m4a", normalized_name="a.m4a")
    ctx, _ = make_ctx([rec])
    (ctx.set_dir / "a.m4a").write_bytes(b"x")
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert ctx.errors.count == 1
    assert result.stats == {"recordings": 0}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.normalize'`.

- [ ] **Step 4: Write the implementation**

Create `backend/src/steno10k/stages/normalize.py`:

```python
from __future__ import annotations

import logging

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.ffmpeg import (
    FFmpegError,
    ensure_ffmpeg_available,
    get_duration_seconds,
)
from steno10k.stages._scope import in_run_scope

log = logging.getLogger("steno10k.stages.normalize")


class NormalizeStage:
    """Validate uploaded recordings and probe their durations.

    Upload already slug-names source audio into `set_dir/<normalized_name>`
    (see api/routers/recordings.py), so there is no copy/rename step. This stage
    fails fast if ffmpeg is unavailable, then records each recording's duration
    on the manifest (feeding the recordings table and the chunk stage).
    """

    name = StageName.NORMALIZE
    depends_on: list[StageName] = []

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return in_run_scope(self.name, opts)

    def run(self, ctx: StageContext) -> StageResult:
        try:
            ensure_ffmpeg_available()
        except FFmpegError as exc:
            ctx.errors.log("normalize", "ffmpeg", exc)
            return StageResult(status=StageStatus.FAILED, message=str(exc))

        recordings = ctx.manifest.recordings
        total = len(recordings)
        probed = 0
        for i, rec in enumerate(recordings):
            src = ctx.set_dir / rec.normalized_name
            if not src.is_file():
                ctx.errors.log("normalize", rec.normalized_name, "source file missing")
            else:
                try:
                    rec.duration_seconds = get_duration_seconds(src)
                    probed += 1
                except Exception as exc:  # per-recording isolation
                    ctx.errors.log("normalize", rec.normalized_name, exc)
            ctx.events.emit(
                Event(
                    kind=EventKind.STAGE_PROGRESS,
                    payload={
                        "stage": self.name,
                        "progress": (i + 1) / total if total else 1.0,
                        "current": i + 1,
                        "total": total,
                    },
                )
            )
        return StageResult(status=StageStatus.OK, stats={"recordings": probed})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_normalize.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/stages/conftest.py backend/src/steno10k/stages/normalize.py backend/tests/stages/test_normalize.py
git commit -m "feat(stages): normalize stage (validate + probe durations)"
```

---

## Task 3: `stages/chunk.py`

Split each recording into overlapping windows via `lib.ffmpeg.plan_chunks` + `extract_chunk`, writing `chunks/<stem>/chunk_{i:03d}.<fmt>`, populating `recording.chunks`, idempotent unless `force`, per-recording isolation.

**Files:**
- Create: `backend/src/steno10k/stages/chunk.py`
- Test: `backend/tests/stages/test_chunk.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_chunk.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

import steno10k.stages.chunk as chunk_mod
from steno10k.contracts.domain import Recording
from steno10k.contracts.events import EventKind
from steno10k.contracts.status import StageStatus
from steno10k.stages.chunk import ChunkStage
from stages.conftest import MakeCtx


def _fake_extract(src: Path, dst: Path, start: float, end: float, fmt: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(b"chunk")


def test_extracts_chunks_and_records_relative_paths(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunk_mod, "plan_chunks", lambda *a, **k: [(0.0, 600.0), (585.0, 900.0)])
    calls: list[tuple[str, float, float, str]] = []

    def rec_extract(src: Path, dst: Path, start: float, end: float, fmt: str) -> None:
        _fake_extract(src, dst, start, end, fmt)
        calls.append((dst.name, start, end, fmt))

    monkeypatch.setattr(chunk_mod, "extract_chunk", rec_extract)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a", duration_seconds=900.0)
    ctx, events = make_ctx([rec])
    (ctx.set_dir / "rec.m4a").write_bytes(b"x")
    result = ChunkStage().run(ctx)
    assert result.status is StageStatus.OK
    assert rec.chunks == ["chunks/rec/chunk_000.m4a", "chunks/rec/chunk_001.m4a"]
    assert (ctx.set_dir / "chunks" / "rec" / "chunk_000.m4a").exists()
    assert result.stats == {"recordings": 1, "chunks": 2}
    assert calls[0] == ("chunk_000.m4a", 0.0, 600.0, "m4a")
    assert any(e.kind is EventKind.STAGE_PROGRESS for e in events)


def test_skips_existing_chunk_unless_force(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunk_mod, "plan_chunks", lambda *a, **k: [(0.0, 600.0)])
    extracted: list[str] = []

    def rec_extract(src: Path, dst: Path, start: float, end: float, fmt: str) -> None:
        _fake_extract(src, dst, start, end, fmt)
        extracted.append(dst.name)

    monkeypatch.setattr(chunk_mod, "extract_chunk", rec_extract)
    ctx, _ = make_ctx(
        [Recording(source_name="rec.m4a", normalized_name="rec.m4a", duration_seconds=600.0)],
        force=False,
    )
    (ctx.set_dir / "rec.m4a").write_bytes(b"x")
    existing = ctx.set_dir / "chunks" / "rec" / "chunk_000.m4a"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    ChunkStage().run(ctx)
    assert extracted == []  # existing chunk left alone

    ctx2, _ = make_ctx(
        [Recording(source_name="rec.m4a", normalized_name="rec.m4a", duration_seconds=600.0)],
        force=True,
    )
    ChunkStage().run(ctx2)
    assert extracted == ["chunk_000.m4a"]  # force re-extracted


def test_probes_duration_when_manifest_lacks_it(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunk_mod, "get_duration_seconds", lambda p: 300.0)
    captured: dict[str, float] = {}

    def fake_plan(
        duration: float, chunk_seconds: int, overlap_seconds: int, min_chunk_seconds: int
    ) -> list[tuple[float, float]]:
        captured["duration"] = duration
        return [(0.0, 300.0)]

    monkeypatch.setattr(chunk_mod, "plan_chunks", fake_plan)
    monkeypatch.setattr(chunk_mod, "extract_chunk", _fake_extract)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")  # no duration
    ctx, _ = make_ctx([rec])
    (ctx.set_dir / "rec.m4a").write_bytes(b"x")
    ChunkStage().run(ctx)
    assert captured["duration"] == 300.0


def test_missing_source_is_logged_and_isolated(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunk_mod, "plan_chunks", lambda *a, **k: [(0.0, 10.0)])
    monkeypatch.setattr(chunk_mod, "extract_chunk", _fake_extract)
    bad = Recording(source_name="b.m4a", normalized_name="b.m4a", duration_seconds=10.0)  # no file
    good = Recording(source_name="g.m4a", normalized_name="g.m4a", duration_seconds=10.0)
    ctx, _ = make_ctx([bad, good])
    (ctx.set_dir / "g.m4a").write_bytes(b"x")
    result = ChunkStage().run(ctx)
    assert ctx.errors.count == 1
    assert good.chunks == ["chunks/g/chunk_000.m4a"]
    assert bad.chunks == []
    assert result.status is StageStatus.OK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_chunk.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.chunk'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/chunk.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.ffmpeg import extract_chunk, get_duration_seconds, plan_chunks
from steno10k.stages._scope import in_run_scope

log = logging.getLogger("steno10k.stages.chunk")


class ChunkStage:
    """Split each recording into overlapping chunks under `chunks/<stem>/`."""

    name = StageName.CHUNK
    depends_on: list[StageName] = [StageName.NORMALIZE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return in_run_scope(self.name, opts)

    def run(self, ctx: StageContext) -> StageResult:
        audio = ctx.cfg.audio
        recordings = ctx.manifest.recordings
        total = len(recordings)
        chunk_total = 0
        for i, rec in enumerate(recordings):
            try:
                src = ctx.set_dir / rec.normalized_name
                if not src.is_file():
                    raise FileNotFoundError(f"source file missing: {rec.normalized_name}")
                duration = rec.duration_seconds
                if duration is None:
                    duration = get_duration_seconds(src)
                windows = plan_chunks(
                    duration,
                    audio.chunk_seconds,
                    audio.overlap_seconds,
                    audio.min_chunk_seconds,
                )
                stem = Path(rec.normalized_name).stem
                chunk_dir = ctx.set_dir / "chunks" / stem
                rel_paths: list[str] = []
                for idx, (start, end) in enumerate(windows):
                    dst = chunk_dir / f"chunk_{idx:03d}.{audio.output_format}"
                    if ctx.force or not dst.exists():
                        extract_chunk(src, dst, start, end, audio.output_format)
                    rel_paths.append(str(dst.relative_to(ctx.set_dir)))
                    chunk_total += 1
                rec.chunks = rel_paths
            except Exception as exc:  # per-recording isolation
                ctx.errors.log("chunk", rec.normalized_name, exc)
            ctx.events.emit(
                Event(
                    kind=EventKind.STAGE_PROGRESS,
                    payload={
                        "stage": self.name,
                        "progress": (i + 1) / total if total else 1.0,
                        "current": i + 1,
                        "total": total,
                    },
                )
            )
        return StageResult(
            status=StageStatus.OK, stats={"recordings": total, "chunks": chunk_total}
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_chunk.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/chunk.py backend/tests/stages/test_chunk.py
git commit -m "feat(stages): chunk stage (plan + extract overlapping chunks)"
```

---

## Task 4: `stages/transcribe.py`

Transcribe each recording's chunks in parallel via `lib.transcriber.transcribe_chunks`, writing `transcripts_raw/<stem>/<chunk_stem>.txt`. Injects the three F1-deferred decode knobs as M1 constants (per ADR 0001). Discovers chunks from disk (so `from_stage=transcribe` works), skips already-transcribed chunks unless `force`, isolates per-chunk failures.

**Files:**
- Create: `backend/src/steno10k/stages/transcribe.py`
- Test: `backend/tests/stages/test_transcribe.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/stages/test_transcribe.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

import steno10k.stages.transcribe as transcribe_mod
from steno10k.contracts.domain import Recording
from steno10k.contracts.events import EventKind
from steno10k.contracts.status import StageStatus
from steno10k.lib.transcriber import TranscribeJob, TranscribeSettings
from steno10k.stages.transcribe import (
    _M1_BEAM_SIZE,
    _M1_MIN_SILENCE_MS,
    _M1_VAD_FILTER,
    TranscribeStage,
)
from stages.conftest import MakeCtx


def _make_chunk(set_dir: Path, stem: str, idx: int, fmt: str = "m4a") -> Path:
    d = set_dir / "chunks" / stem
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"chunk_{idx:03d}.{fmt}"
    p.write_bytes(b"audio")
    return p


def test_transcribes_pending_chunks_and_maps_settings(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        captured["settings"] = settings
        captured["max_workers"] = max_workers
        out: list[tuple[Path, str | None]] = []
        for j in jobs:
            j.output_path.parent.mkdir(parents=True, exist_ok=True)
            j.output_path.write_text("text", encoding="utf-8")
            out.append((j.output_path, None))
        return out

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")
    ctx, events = make_ctx([rec])
    _make_chunk(ctx.set_dir, "rec", 0)
    _make_chunk(ctx.set_dir, "rec", 1)
    result = TranscribeStage().run(ctx)
    assert result.stats == {"chunks": 2, "transcribed": 2, "failed": 0}
    assert (ctx.set_dir / "transcripts_raw" / "rec" / "chunk_000.txt").read_text() == "text"
    settings = captured["settings"]
    assert isinstance(settings, TranscribeSettings)
    assert settings.beam_size == _M1_BEAM_SIZE
    assert settings.vad_filter is _M1_VAD_FILTER
    assert settings.min_silence_duration_ms == _M1_MIN_SILENCE_MS
    assert settings.cpu_threads == ctx.cfg.transcription.cpu_threads_per_worker
    assert settings.model == ctx.cfg.transcription.model
    assert captured["max_workers"] == ctx.cfg.transcription.max_workers
    assert any(e.kind is EventKind.STAGE_PROGRESS for e in events)


def test_skips_already_transcribed_unless_force(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        for j in jobs:
            seen.append(j.output_path.name)
            j.output_path.parent.mkdir(parents=True, exist_ok=True)
            j.output_path.write_text("new", encoding="utf-8")
        return [(j.output_path, None) for j in jobs]

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    ctx, _ = make_ctx(
        [Recording(source_name="rec.m4a", normalized_name="rec.m4a")], force=False
    )
    _make_chunk(ctx.set_dir, "rec", 0)
    done = ctx.set_dir / "transcripts_raw" / "rec" / "chunk_000.txt"
    done.parent.mkdir(parents=True)
    done.write_text("old", encoding="utf-8")
    r1 = TranscribeStage().run(ctx)
    assert seen == []  # nothing pending
    assert r1.stats == {"chunks": 0, "transcribed": 0, "failed": 0}

    ctx2, _ = make_ctx(
        [Recording(source_name="rec.m4a", normalized_name="rec.m4a")], force=True
    )
    TranscribeStage().run(ctx2)
    assert seen == ["chunk_000.txt"]  # force re-transcribed


def test_per_chunk_failure_is_isolated(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        results: list[tuple[Path, str | None]] = []
        for k, j in enumerate(jobs):
            if k == 0:
                results.append((j.output_path, "WhisperError: boom"))
            else:
                j.output_path.parent.mkdir(parents=True, exist_ok=True)
                j.output_path.write_text("ok", encoding="utf-8")
                results.append((j.output_path, None))
        return results

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")
    ctx, _ = make_ctx([rec])
    _make_chunk(ctx.set_dir, "rec", 0)
    _make_chunk(ctx.set_dir, "rec", 1)
    result = TranscribeStage().run(ctx)
    assert result.stats == {"chunks": 2, "transcribed": 1, "failed": 1}
    assert ctx.errors.count == 1


def test_no_chunks_never_invokes_worker(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[int] = []

    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        called.append(1)
        return []

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")  # no chunks dir
    ctx, _ = make_ctx([rec])
    result = TranscribeStage().run(ctx)
    assert result.stats == {"chunks": 0, "transcribed": 0, "failed": 0}
    assert called == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/stages/test_transcribe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.stages.transcribe'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/stages/transcribe.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.transcriber import TranscribeJob, TranscribeSettings, transcribe_chunks
from steno10k.stages._scope import in_run_scope

log = logging.getLogger("steno10k.stages.transcribe")

# F1 froze TranscriptionConfig without these faster-whisper decode knobs; the
# transcribe stage supplies them as M1 defaults per
# docs/adr/0001-defer-llm-and-whisper-config-knobs.md.
_M1_BEAM_SIZE = 5
_M1_VAD_FILTER = True
_M1_MIN_SILENCE_MS = 500


class TranscribeStage:
    """Transcribe each recording's chunks with faster-whisper, in parallel."""

    name = StageName.TRANSCRIBE
    depends_on: list[StageName] = [StageName.CHUNK]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return in_run_scope(self.name, opts)

    def _settings(self, cfg: Config) -> TranscribeSettings:
        t = cfg.transcription
        return TranscribeSettings(
            model=t.model,
            device=t.device,
            compute_type=t.compute_type,
            language=t.language,
            beam_size=_M1_BEAM_SIZE,
            vad_filter=_M1_VAD_FILTER,
            min_silence_duration_ms=_M1_MIN_SILENCE_MS,
            cpu_threads=t.cpu_threads_per_worker,
        )

    def run(self, ctx: StageContext) -> StageResult:
        fmt = ctx.cfg.audio.output_format
        settings = self._settings(ctx.cfg)
        max_workers = ctx.cfg.transcription.max_workers
        recordings = ctx.manifest.recordings
        total = len(recordings)
        processed = 0
        failed = 0
        for i, rec in enumerate(recordings):
            stem = Path(rec.normalized_name).stem
            chunk_dir = ctx.set_dir / "chunks" / stem
            jobs: list[TranscribeJob] = []
            if chunk_dir.is_dir():
                for chunk_path in sorted(chunk_dir.glob(f"*.{fmt}")):
                    out = ctx.set_dir / "transcripts_raw" / stem / f"{chunk_path.stem}.txt"
                    if out.exists() and not ctx.force:
                        continue
                    jobs.append(TranscribeJob(chunk_path=chunk_path, output_path=out))
            if jobs:
                for out_path, err in transcribe_chunks(jobs, settings, max_workers):
                    processed += 1
                    if err is not None:
                        failed += 1
                        ctx.errors.log("transcribe", out_path.name, err)
            ctx.events.emit(
                Event(
                    kind=EventKind.STAGE_PROGRESS,
                    payload={
                        "stage": self.name,
                        "progress": (i + 1) / total if total else 1.0,
                        "current": i + 1,
                        "total": total,
                    },
                )
            )
        return StageResult(
            status=StageStatus.OK,
            stats={"chunks": processed, "transcribed": processed - failed, "failed": failed},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/stages/test_transcribe.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/stages/transcribe.py backend/tests/stages/test_transcribe.py
git commit -m "feat(stages): transcribe stage (parallel faster-whisper over chunks)"
```

---

## Task 5: Binary-gated integration tests

One real end-to-end pass per stage over an ffmpeg-generated tone. These exercise the actual `lib` code paths (no monkeypatching) and **skip cleanly** where the binary/model is absent, so CI without ffmpeg/whisper stays green.

**Files:**
- Create: `backend/tests/stages/test_integration.py`

- [ ] **Step 1: Write the integration tests**

Create `backend/tests/stages/test_integration.py`:

```python
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from steno10k.contracts.config import AudioConfig, Config, TranscriptionConfig
from steno10k.contracts.domain import Recording
from steno10k.contracts.status import StageStatus
from steno10k.stages.chunk import ChunkStage
from steno10k.stages.normalize import NormalizeStage
from steno10k.stages.transcribe import TranscribeStage
from stages.conftest import MakeCtx

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
_RUN_WHISPER = os.environ.get("STENO10K_RUN_WHISPER") == "1"


def _make_tone(path: Path, seconds: int) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"sine=frequency=440:duration={seconds}", str(path)],
        check=True, capture_output=True,
    )


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_normalize_probes_real_duration(make_ctx: MakeCtx) -> None:
    rec = Recording(source_name="tone.wav", normalized_name="tone.wav")
    ctx, _ = make_ctx([rec])
    _make_tone(ctx.set_dir / "tone.wav", seconds=2)
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert rec.duration_seconds is not None
    assert 1.8 <= rec.duration_seconds <= 2.2


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_chunk_extracts_real_windows(make_ctx: MakeCtx) -> None:
    cfg = Config(
        audio=AudioConfig(
            chunk_seconds=1, overlap_seconds=0, min_chunk_seconds=0, output_format="wav"
        )
    )
    rec = Recording(source_name="tone.wav", normalized_name="tone.wav")
    ctx, _ = make_ctx([rec], cfg=cfg)
    _make_tone(ctx.set_dir / "tone.wav", seconds=3)
    result = ChunkStage().run(ctx)
    assert result.status is StageStatus.OK
    chunks = sorted((ctx.set_dir / "chunks" / "tone").glob("chunk_*.wav"))
    assert len(chunks) >= 2
    assert rec.chunks[0] == "chunks/tone/chunk_000.wav"


@pytest.mark.skipif(
    not (_HAS_FFMPEG and _RUN_WHISPER),
    reason="set STENO10K_RUN_WHISPER=1 (and install ffmpeg) to run the real model",
)
def test_transcribe_real_tiny_model(make_ctx: MakeCtx) -> None:
    cfg = Config(
        audio=AudioConfig(output_format="wav"),
        transcription=TranscriptionConfig(
            model="tiny", device="cpu", compute_type="int8", language="en",
            max_workers=1, cpu_threads_per_worker=1,
        ),
    )
    rec = Recording(source_name="tone.wav", normalized_name="tone.wav")
    ctx, _ = make_ctx([rec], cfg=cfg)
    chunk = ctx.set_dir / "chunks" / "tone" / "chunk_000.wav"
    chunk.parent.mkdir(parents=True)
    _make_tone(chunk, seconds=1)
    result = TranscribeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert result.stats["failed"] == 0
    assert (ctx.set_dir / "transcripts_raw" / "tone" / "chunk_000.txt").exists()
```

- [ ] **Step 2: Run the integration tests**

Run: `cd backend && uv run pytest tests/stages/test_integration.py -v`
Expected: with ffmpeg installed, the normalize + chunk tests PASS and the whisper test is SKIPPED (unless `STENO10K_RUN_WHISPER=1`). Without ffmpeg, all three SKIP.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/stages/test_integration.py
git commit -m "test(stages): binary-gated integration tests for the heavy stages"
```

---

## Task 6: Full validation + PR

- [ ] **Step 1: Run the full quality gate**

```bash
cd backend
uv run ruff check --fix .   # auto-resolves import ordering (isort rule I)
uv run ruff format .
uv run mypy
uv run pytest -q
```
Expected: ruff clean, mypy clean (strict), all tests pass (new stage tests + the whole existing suite); binary-gated tests skip or pass per environment. If `ruff --fix`/`format` changed any file, `git commit -am "style: ruff autofixes"`. `build_registry()` is unchanged — confirm with `git diff origin/main -- backend/src/steno10k/api/stages.py` (expect empty).

- [ ] **Step 2: Run repo pre-commit**

```bash
pre-commit run --all-files
```
Expected: all hooks pass. Fix and re-run if anything auto-formats.

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin "feat/${ISSUE}-s1-heavy-stages"
gh pr create --fill --base main \
  --title "M1·S1: heavy stages (normalize, chunk, transcribe)" \
  --body "Closes #${ISSUE}

Implements the M1·S1 fan-out unit: normalize/chunk/transcribe stages in a new
\`steno10k/stages/\` package, over the merged \`steno10k/lib/\`.

- normalize: fail-fast ffmpeg check + per-recording duration probe onto the manifest
- chunk: plan_chunks + extract_chunk into chunks/<stem>/, idempotent unless force
- transcribe: parallel faster-whisper into transcripts_raw/<stem>/, M1 decode knobs (ADR 0001)
- shared only/from_stage gate; STAGE_PROGRESS events; per-item error isolation

Out of scope (M1·W): build_registry() wiring + API run-option passthrough. No frozen
contract touched.

Spec: docs/specs/2026-07-11-steno10k-m1-s1-heavy-stages-design.md
Plan: docs/plans/2026-07-11-m1-s1-heavy-stages.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Expected: CI green; request review; squash-merge per repo policy.

---

## Notes for the next unit (M1·W)

- Register the three stages in `api/stages.py::build_registry()` in `StageName`
  order: `StageRegistry([NormalizeStage(), ChunkStage(), TranscribeStage(), ...S2 stages])`.
- Thread `only`/`from_stage`/`force` from the runs router → `RunOptions` /
  `StageContext.force`; the stage-side gate (`in_run_scope`) already consumes them.
- Touching `api/` requires the contract-change lock protocol (AGENTS.md).
