# F1 — Domain & Core Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frozen contracts every stage, endpoint, and screen builds against — domain models, slug rules, config schema, per-set manifest, the Stage contract (incl. cascade-disable), the stage registry, and the in-process event bus — with tests. **No stage logic yet.**

**Architecture:** Pure Python contracts under `backend/src/steno10k/contracts/` (the frozen path from `AGENTS.md`/CODEOWNERS). Cycle-free layering: leaf modules `status`, `names`, `ids`, `errors`, `llm`, `events` depend on nothing internal; `domain`, `config`, `manifest`, `stage`, `registry`, `runner` build on them. A generic runner loops the registry, running stages and emitting events — proven here with a fake stage. Rules: `from __future__ import annotations`, modern types, `mypy --strict`, narrow exceptions. IDs are GUIDs generated at the creation boundary (`new_id()` via `uuid4`), not inside pure functions.

**Tech Stack:** Python 3.12 · pydantic v2 · pytest · ruff · mypy (already configured in `backend/`).

**Source spec:** `docs/specs/2026-07-11-steno10k-f1-domain-core-contracts-design.md`.

**Git:** This creates (not edits) the frozen contracts, so no contract-lock is needed. One branch → one PR. **The maintainer reviews and merges — this plan only pushes and opens the PR; it does NOT merge.**

---

## Task 0: Tracking issue + branch

- [ ] **Step 1: Create the F1 tracking issue**

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k
gh issue create --title "F1: domain & core contracts" --label "area:backend" \
  --body "Implement the frozen contracts per docs/specs/2026-07-11-steno10k-f1-domain-core-contracts-design.md. Blocks the stage fan-out."
```

- [ ] **Step 2: Branch off main** (use the issue number `N`)

```bash
git switch main && git pull -q
git switch -c feat/N-f1-contracts
mkdir -p backend/src/steno10k/contracts
: > backend/src/steno10k/contracts/__init__.py
```

---

## Task 1: Slug utility (pure, tested)

**Files:** Create `backend/src/steno10k/contracts/slug.py`, `backend/tests/test_slug.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from steno10k.contracts.slug import resolve_collision, slugify


def test_slugify_lowercases_and_hyphenates() -> None:
    assert slugify("Judicial Review — Part 1") == "judicial-review-part-1"


def test_slugify_handles_unicode() -> None:
    assert slugify("Івана Франка") == "ivana-franka"


def test_slugify_empty_falls_back() -> None:
    assert slugify("   ") == "untitled"


def test_resolve_collision_suffixes() -> None:
    assert resolve_collision(set(), "week-1") == "week-1"
    assert resolve_collision({"week-1"}, "week-1") == "week-1_2"
    assert resolve_collision({"week-1", "week-1_2"}, "week-1") == "week-1_3"
```

- [ ] **Step 2: Run, verify it fails** — `cd backend && uv run pytest tests/test_slug.py -q`

- [ ] **Step 3: Implement `slug.py`**

```python
from __future__ import annotations

import re
import unicodedata


def slugify(title: str) -> str:
    """Unicode-safe, lowercased, hyphenated slug. Empty -> 'untitled'."""
    normalized = unicodedata.normalize("NFKD", title)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    hyphenated = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return hyphenated or "untitled"


def resolve_collision(existing: set[str], slug: str) -> str:
    """Return `slug`, or `slug_2`, `slug_3`, ... if it collides with `existing`."""
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}_{n}" in existing:
        n += 1
    return f"{slug}_{n}"
```

- [ ] **Step 4: Run tests + lint + types, verify pass**

Run: `cd backend && uv run pytest tests/test_slug.py -q && uv run ruff check . && uv run mypy`

- [ ] **Step 5: Commit** — `git commit -am "feat: unicode-safe slug + collision resolver"` (after `git add`)

---

## Task 2: Low-level enums + id generator

**Files:** Create `backend/src/steno10k/contracts/status.py`, `.../names.py`, `.../ids.py`, `backend/tests/test_primitives.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from steno10k.contracts.ids import new_id
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


def test_stage_status_values() -> None:
    assert StageStatus.OK == "ok"


def test_stage_names_ordered() -> None:
    assert list(StageName) == [
        StageName.NORMALIZE, StageName.CHUNK, StageName.TRANSCRIBE, StageName.CLEAN,
        StageName.MERGE, StageName.SUMMARIZE, StageName.BUNDLE, StageName.NOTIFY,
    ]
    assert StageName.SUMMARIZE == "summarize"


def test_new_id_is_a_unique_guid() -> None:
    a, b = new_id(), new_id()
    assert len(a) == 36 and a.count("-") == 4
    assert a != b
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `status.py`**

```python
from __future__ import annotations

from enum import StrEnum


class StageStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"
```

- [ ] **Step 4: Implement `names.py`** (stages are a string enum)

```python
from __future__ import annotations

from enum import StrEnum


class StageName(StrEnum):
    NORMALIZE = "normalize"
    CHUNK = "chunk"
    TRANSCRIBE = "transcribe"
    CLEAN = "clean"
    MERGE = "merge"
    SUMMARIZE = "summarize"
    BUNDLE = "bundle"
    NOTIFY = "notify"
```

- [ ] **Step 5: Implement `ids.py`** (GUIDs, generated at the creation boundary)

```python
from __future__ import annotations

import uuid


def new_id() -> str:
    """A fresh GUID string. Called at object-creation boundaries only."""
    return str(uuid.uuid4())
```

- [ ] **Step 6: Run tests + lint + types, verify pass. Commit** `feat: stage status/name enums + guid generator`

---

## Task 3: Domain models (GUID ids)

**Files:** Create `backend/src/steno10k/contracts/domain.py`, `backend/tests/test_domain.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import uuid

from steno10k.contracts.domain import Project, Recording, RecordingSet
from steno10k.contracts.status import StageStatus


def test_recording_defaults() -> None:
    r = Recording(source_name="a.m4a", normalized_name="a.m4a")
    assert r.duration_seconds is None and r.chunks == []


def test_set_gets_a_guid_id_and_holds_recordings() -> None:
    s = RecordingSet(slug="week-1", title="Week 1", project_slug="law")
    uuid.UUID(s.id)  # raises if not a valid GUID
    s.recordings.append(Recording(source_name="a.m4a", normalized_name="a.m4a"))
    s.stages[StageName_key()] = StageStatus.OK
    assert len(s.recordings) == 1


def StageName_key() -> str:
    from steno10k.contracts.names import StageName

    return StageName.NORMALIZE


def test_project_gets_guid_and_holds_sets() -> None:
    p = Project(slug="law", title="Law")
    uuid.UUID(p.id)
    p.sets.append(RecordingSet(slug="week-1", title="Week 1", project_slug="law"))
    assert p.sets[0].project_slug == "law"
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `domain.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field

from steno10k.contracts.ids import new_id
from steno10k.contracts.status import StageStatus


@dataclass
class Recording:
    source_name: str
    normalized_name: str
    duration_seconds: float | None = None
    chunks: list[str] = field(default_factory=list)


@dataclass
class RecordingSet:
    slug: str
    title: str
    project_slug: str
    id: str = field(default_factory=new_id)  # GUID
    recordings: list[Recording] = field(default_factory=list)
    stages: dict[str, StageStatus] = field(default_factory=dict)


@dataclass
class Project:
    slug: str
    title: str
    id: str = field(default_factory=new_id)  # GUID
    sets: list[RecordingSet] = field(default_factory=list)
```

- [ ] **Step 4: Run tests + lint + types, verify pass. Commit** `feat: domain models (project/set/recording) with guid ids`

---

## Task 4: Config schema (Pydantic, partial-valid)

**Files:** Create `backend/src/steno10k/contracts/config.py`, `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test** (defaults: **small** model, **English** everywhere)

```python
from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName


def test_defaults_are_small_model_and_english() -> None:
    cfg = Config()
    assert cfg.transcription.model == "small"
    assert cfg.transcription.language == "en"
    assert cfg.prompts.language == "en"
    assert cfg.output.summary_filename == "summary.md"


def test_partial_override_keeps_other_defaults() -> None:
    cfg = Config.model_validate({"transcription": {"model": "large-v3"}})
    assert cfg.transcription.model == "large-v3"
    assert cfg.audio.chunk_seconds == 600


def test_stage_flags_default_enabled() -> None:
    cfg = Config()
    assert cfg.stages.enabled[StageName.TRANSCRIBE] is True
    assert set(cfg.stages.enabled) == set(StageName)
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `config.py`**

```python
from __future__ import annotations

from pydantic import BaseModel, Field

from steno10k.contracts.names import StageName


class AudioConfig(BaseModel):
    chunk_seconds: int = 600
    overlap_seconds: int = 15
    min_chunk_seconds: int = 20
    output_format: str = "m4a"


class TranscriptionConfig(BaseModel):
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    max_workers: int = 4
    cpu_threads_per_worker: int = 3


class LLMConfig(BaseModel):
    enabled: bool = True
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = ""
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 4000
    concurrency: int = 2


class OutputConfig(BaseModel):
    summary_filename: str = "summary.md"
    save_merged_raw_transcript: bool = True
    save_merged_clean_transcript: bool = True
    save_bundle_docx: bool = True


class StagesConfig(BaseModel):
    enabled: dict[StageName, bool] = Field(
        default_factory=lambda: {name: True for name in StageName}
    )


class PromptsConfig(BaseModel):
    language: str = "en"
    target_output_language: str = "en"
    override_dir: str | None = None


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id: int | None = None


class Config(BaseModel):
    audio: AudioConfig = Field(default_factory=AudioConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    stages: StagesConfig = Field(default_factory=StagesConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
```

- [ ] **Step 4: Run tests + lint + types, verify pass. Commit** `feat: pydantic config schema (small/english defaults, partial-valid)`

---

## Task 5: In-process event bus

**Files:** Create `backend/src/steno10k/contracts/events.py`, `backend/tests/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from steno10k.contracts.events import Event, EventBus, EventKind


def test_subscribers_receive_events() -> None:
    bus = EventBus()
    seen: list[Event] = []
    bus.subscribe(seen.append)
    bus.emit(Event(kind=EventKind.STAGE_STARTED, payload={"stage": "normalize"}))
    assert seen[0].kind is EventKind.STAGE_STARTED
    assert seen[0].payload["stage"] == "normalize"


def test_subscriber_error_is_isolated() -> None:
    bus = EventBus()
    good: list[Event] = []

    def boom(_: Event) -> None:
        raise RuntimeError("subscriber blew up")

    bus.subscribe(boom)
    bus.subscribe(good.append)
    bus.emit(Event(kind=EventKind.RUN_STARTED, payload={}))
    assert len(good) == 1
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `events.py`**

```python
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from typing import Any

log = logging.getLogger("steno10k.events")


class EventKind(StrEnum):
    RUN_STARTED = "run_started"
    STAGE_STARTED = "stage_started"
    STAGE_PROGRESS = "stage_progress"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    RUN_COMPLETED = "run_completed"
    ERROR = "error"


@dataclass
class Event:
    kind: EventKind
    payload: dict[str, Any] = field(default_factory=dict)


class EventEmitter:
    """Emit-only handle held by stages."""

    def emit(self, event: Event) -> None:  # pragma: no cover - overridden
        raise NotImplementedError


class EventBus(EventEmitter):
    def __init__(self) -> None:
        self._subscribers: list[Callable[[Event], None]] = []
        self._lock = Lock()

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        with self._lock:
            self._subscribers.append(handler)

    def emit(self, event: Event) -> None:
        with self._lock:
            handlers = list(self._subscribers)
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # isolation: one bad subscriber must not break dispatch
                log.exception("event subscriber failed for %s", event.kind)
```

- [ ] **Step 4: Run tests + lint + types, verify pass. Commit** `feat: in-process event bus with subscriber-error isolation`

---

## Task 6: Manifest (schema + JSON round-trip)

**Files:** Create `backend/src/steno10k/contracts/manifest.py`, `backend/tests/test_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import uuid
from pathlib import Path

from steno10k.contracts.domain import Recording
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


def test_manifest_round_trip(tmp_path: Path) -> None:
    m = Manifest(project_slug="law", set_slug="week-1", title="Week 1")
    uuid.UUID(m.id)  # id is a GUID
    m.recordings.append(Recording(source_name="a.m4a", normalized_name="a.m4a"))
    m.stages[StageName.NORMALIZE] = StageStatus.OK
    path = tmp_path / "manifest.json"
    m.save(path)

    loaded = Manifest.load(path)
    assert loaded.id == m.id
    assert loaded.recordings[0].source_name == "a.m4a"
    assert loaded.stages[StageName.NORMALIZE] is StageStatus.OK
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `manifest.py`** (pydantic for JSON; GUID id; timestamps injected, not read from a clock)

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from steno10k.contracts.domain import Recording
from steno10k.contracts.ids import new_id
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


class Manifest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=new_id)  # GUID
    project_slug: str
    set_slug: str
    title: str
    source_files: list[str] = Field(default_factory=list)
    recordings: list[Recording] = Field(default_factory=list)
    stages: dict[StageName, StageStatus] = Field(default_factory=dict)
    generated_files: list[str] = Field(default_factory=list)
    errors: int = 0
    created: str | None = None
    updated: str | None = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Manifest:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))
```

Note: `Recording` is a stdlib dataclass; pydantic v2 accepts dataclasses as field types. If mypy/pydantic objects, convert `Recording` to `pydantic.dataclasses.dataclass` in `domain.py` (identical fields) and re-run.

- [ ] **Step 4: Run tests + lint + types, verify pass. Commit** `feat: per-set manifest with json round-trip (guid id)`

---

## Task 7: Stage contract + cascade-disable resolver

The cascade resolver lives with the stage contract (it is stage-graph logic).

**Files:** Create `backend/src/steno10k/contracts/errors.py`, `.../llm.py`, `.../stage.py`, `backend/tests/test_stage.py`

- [ ] **Step 1: Write the failing test** (fake stage conforms; cascade covers multiple + transitive)

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import EventBus
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import Stage, StageContext, StageResult, resolve_enabled
from steno10k.contracts.status import StageStatus

DEPS = {
    StageName.NORMALIZE: [],
    StageName.TRANSCRIBE: [StageName.NORMALIZE],
    StageName.MERGE: [StageName.TRANSCRIBE],
    StageName.SUMMARIZE: [StageName.MERGE],
    StageName.BUNDLE: [StageName.MERGE],
}


def test_all_enabled_stays_enabled() -> None:
    enabled, cascaded = resolve_enabled(DEPS, {k: True for k in DEPS})
    assert enabled == set(DEPS) and cascaded == {}


def test_disable_cascades_to_all_dependents_transitively() -> None:
    flags = {k: True for k in DEPS}
    flags[StageName.TRANSCRIBE] = False
    enabled, cascaded = resolve_enabled(DEPS, flags)
    # transcribe off -> merge off -> summarize AND bundle off
    assert enabled == {StageName.NORMALIZE}
    assert cascaded[StageName.MERGE] == StageName.TRANSCRIBE
    assert StageName.SUMMARIZE in cascaded and StageName.BUNDLE in cascaded


class FakeStage:
    name = StageName.NORMALIZE
    depends_on: list[StageName] = []

    def enabled(self, cfg: Config, opts: object) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        return StageResult(status=StageStatus.OK, stats={"files": 1})


def test_fake_stage_satisfies_protocol(tmp_path: Path) -> None:
    stage: Stage = FakeStage()
    ctx = StageContext(
        set_dir=tmp_path, cfg=Config(), force=False,
        manifest=Manifest(project_slug="p", set_slug="s", title="S"),
        errors=ErrorLog(tmp_path / "errors.log"), events=EventBus(), llm=None,
    )
    assert stage.run(ctx).status is StageStatus.OK
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `errors.py`**

```python
from __future__ import annotations

from pathlib import Path


class ErrorLog:
    """Per-set error sink. Appends to errors.log and counts."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.count = 0

    def log(self, stage: str, item: str, error: object) -> None:
        self.count += 1
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{stage}] {item}: {error}\n")
```

- [ ] **Step 4: Implement `llm.py`** (minimal interface; concrete client ported later)

```python
from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...
```

- [ ] **Step 5: Implement `stage.py`** (contract types + cascade resolver)

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from steno10k.contracts.config import Config
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import EventEmitter
from steno10k.contracts.llm import LLMClient
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


@dataclass
class RunOptions:
    force: bool = False
    only: StageName | None = None
    from_stage: StageName | None = None
    skip_llm: bool = False


@dataclass
class StageResult:
    status: StageStatus
    stats: dict[str, int] = field(default_factory=dict)
    message: str | None = None


@dataclass
class StageContext:
    set_dir: Path
    cfg: Config
    force: bool
    manifest: Manifest
    errors: ErrorLog
    events: EventEmitter
    llm: LLMClient | None


class Stage(Protocol):
    name: StageName
    depends_on: list[StageName]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool: ...
    def run(self, ctx: StageContext) -> StageResult: ...


def resolve_enabled(
    deps: dict[StageName, list[StageName]], flags: dict[StageName, bool]
) -> tuple[set[StageName], dict[StageName, StageName]]:
    """Effective enabled stages after cascade-disable.

    Iterates to a FIXED POINT, so disabling one stage propagates to every
    transitive dependent (and to multiple dependents), not just the first.
    Returns (enabled, cascaded) where `cascaded` maps each forced-off stage to
    the disabled dependency that first caused it.
    """
    enabled = {name for name, on in flags.items() if on}
    cascaded: dict[StageName, StageName] = {}
    changed = True
    while changed:
        changed = False
        for name in list(enabled):
            for dep in deps.get(name, []):
                if dep not in enabled:
                    enabled.discard(name)
                    cascaded.setdefault(name, dep)
                    changed = True
                    break
    return enabled, cascaded
```

- [ ] **Step 6: Run tests + lint + types, verify pass. Commit** `feat: stage contract (context/result/protocol) + cascade-disable resolver`

---

## Task 8: Stage registry (order + dependency validation)

**Files:** Create `backend/src/steno10k/contracts/registry.py`, `backend/tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import pytest

from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.stage import StageResult
from steno10k.contracts.status import StageStatus


def _mk(name: StageName, deps: list[StageName]):
    class _S:
        pass

    s = _S()
    s.name = name
    s.depends_on = deps
    s.enabled = lambda cfg, opts: True
    s.run = lambda ctx: StageResult(status=StageStatus.OK)
    return s


def test_registry_preserves_order() -> None:
    reg = StageRegistry([_mk(StageName.NORMALIZE, []), _mk(StageName.TRANSCRIBE, [StageName.NORMALIZE])])
    assert reg.names == [StageName.NORMALIZE, StageName.TRANSCRIBE]


def test_registry_rejects_unknown_dependency() -> None:
    with pytest.raises(ValueError, match="unknown dependency"):
        StageRegistry([_mk(StageName.TRANSCRIBE, [StageName.NORMALIZE])])


def test_registry_rejects_forward_dependency() -> None:
    with pytest.raises(ValueError, match="after"):
        StageRegistry([_mk(StageName.NORMALIZE, [StageName.TRANSCRIBE]), _mk(StageName.TRANSCRIBE, [])])
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `registry.py`**

```python
from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.stage import Stage, resolve_enabled


class StageRegistry:
    """Ordered stages + dependency validation. Source of truth for stage order."""

    def __init__(self, stages: list[Stage]) -> None:
        self._stages = stages
        self._validate()

    @property
    def names(self) -> list[StageName]:
        return [s.name for s in self._stages]

    @property
    def stages(self) -> list[Stage]:
        return list(self._stages)

    def deps(self) -> dict[StageName, list[StageName]]:
        return {s.name: list(s.depends_on) for s in self._stages}

    def resolve_enabled(
        self, flags: dict[StageName, bool]
    ) -> tuple[set[StageName], dict[StageName, StageName]]:
        return resolve_enabled(self.deps(), flags)

    def _validate(self) -> None:
        seen: set[StageName] = set()
        names = self.names
        for stage in self._stages:
            for dep in stage.depends_on:
                if dep not in names:
                    raise ValueError(f"stage '{stage.name}' has unknown dependency '{dep}'")
                if dep not in seen:
                    raise ValueError(f"stage '{stage.name}' depends on '{dep}' declared after it")
            seen.add(stage.name)
```

- [ ] **Step 4: Run tests + lint + types, verify pass. Commit** `feat: stage registry with order + dependency validation`

---

## Task 9: Generic runner (proves the loop with a fake stage)

**Files:** Create `backend/src/steno10k/contracts/runner.py`, `backend/tests/test_runner.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import EventBus, EventKind
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.runner import run_set
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


def _stage(name: StageName, deps: list[StageName], status: StageStatus):
    class _S:
        pass

    s = _S()
    s.name = name
    s.depends_on = deps
    s.enabled = lambda cfg, opts: True
    s.run = lambda ctx: StageResult(status=status)
    return s


def test_runner_records_status_and_emits(tmp_path: Path) -> None:
    reg = StageRegistry([_stage(StageName.NORMALIZE, [], StageStatus.OK)])
    manifest = Manifest(project_slug="p", set_slug="s", title="S")
    bus = EventBus()
    kinds: list[EventKind] = []
    bus.subscribe(lambda e: kinds.append(e.kind))
    ctx = StageContext(
        set_dir=tmp_path, cfg=Config(), force=False, manifest=manifest,
        errors=ErrorLog(tmp_path / "errors.log"), events=bus, llm=None,
    )
    run_set(reg, ctx, RunOptions())

    assert manifest.stages[StageName.NORMALIZE] is StageStatus.OK
    assert {EventKind.RUN_STARTED, EventKind.STAGE_COMPLETED, EventKind.RUN_COMPLETED} <= set(kinds)
```

- [ ] **Step 2: Run, verify it fails.**

- [ ] **Step 3: Implement `runner.py`**

```python
from __future__ import annotations

from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.stage import RunOptions, StageContext
from steno10k.contracts.status import StageStatus


def run_set(reg: StageRegistry, ctx: StageContext, opts: RunOptions) -> None:
    """Generic loop: for each active stage, run it, record status, emit events."""
    ctx.events.emit(Event(kind=EventKind.RUN_STARTED, payload={"set": ctx.manifest.set_slug}))
    flags = {name: ctx.cfg.stages.enabled.get(name, True) for name in reg.names}
    active, _cascaded = reg.resolve_enabled(flags)

    for stage in reg.stages:
        if stage.name not in active or not stage.enabled(ctx.cfg, opts):
            ctx.manifest.stages[stage.name] = StageStatus.SKIPPED
            continue
        ctx.events.emit(Event(kind=EventKind.STAGE_STARTED, payload={"stage": stage.name}))
        result = stage.run(ctx)
        ctx.manifest.stages[stage.name] = result.status
        kind = (
            EventKind.STAGE_COMPLETED if result.status is StageStatus.OK else EventKind.STAGE_FAILED
        )
        ctx.events.emit(Event(kind=kind, payload={"stage": stage.name, "stats": result.stats}))

    ctx.events.emit(Event(kind=EventKind.RUN_COMPLETED, payload={"set": ctx.manifest.set_slug}))
```

- [ ] **Step 4: Run tests + lint + types, verify pass. Commit** `feat: generic stage runner (loop, status, events)`

---

## Task 10: `config.example.yaml` + README fix

Now that the config schema exists (Task 4), ship the example config (deferred from
M0) and remove the "added later" note from the README.

**Files:** Create `config.example.yaml` (repo root); Modify `README.md`

- [ ] **Step 1: Write `config.example.yaml`** mirroring the Task 4 schema. Secrets are placeholders / env-var names only.

```yaml
# steno10k configuration. Copy to config.yaml and edit.
# Secrets are read from environment variables — NEVER put real keys here.

audio:
  chunk_seconds: 600
  overlap_seconds: 15
  min_chunk_seconds: 20
  output_format: m4a

transcription:
  model: small # tiny | base | small | medium | large-v3
  device: cpu
  compute_type: int8
  language: en
  max_workers: 4
  cpu_threads_per_worker: 3

llm:
  enabled: true
  api_key_env: OPENAI_API_KEY # env var holding the key; never hardcode it
  base_url: "" # any OpenAI-compatible endpoint
  model: ""
  temperature: 0.2
  max_tokens: 4000
  concurrency: 2

output:
  summary_filename: summary.md
  save_merged_raw_transcript: true
  save_merged_clean_transcript: true
  save_bundle_docx: true

stages:
  enabled:
    normalize: true
    chunk: true
    transcribe: true
    clean: true
    merge: true
    summarize: true
    bundle: true
    notify: true # needs telegram.enabled (or a UI subscriber) to do anything

prompts:
  language: en
  target_output_language: en
  override_dir: null

telegram:
  enabled: false
  bot_token_env: TELEGRAM_BOT_TOKEN
  chat_id: null
```

- [ ] **Step 2: Verify it parses AND validates against the schema**

```bash
cd backend && uv run --with pyyaml python -c "import yaml; from steno10k.contracts.config import Config; Config.model_validate(yaml.safe_load(open('../config.example.yaml'))); print('config.example.yaml: valid')"
```
Expected: `config.example.yaml: valid`.

- [ ] **Step 3: Fix the README** — in `README.md`, change the quickstart line
  `cp config.example.yaml config.yaml   # (added in a later milestone)` to just
  `cp config.example.yaml config.yaml` (the file now exists).

- [ ] **Step 4: Commit**

```bash
git add config.example.yaml README.md
git commit -m "docs: add config.example.yaml (matches F1 schema) + README quickstart fix"
```

---

## Task 11: Full check, push, open PR (maintainer reviews & merges)

- [ ] **Step 1: Full backend gate**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run mypy`
Expected: all green.

- [ ] **Step 2: Push the branch + open the PR — do NOT merge**

```bash
git push -u origin feat/N-f1-contracts
gh pr create --base main --title "F1: domain & core contracts" \
  --body "Closes #N. Implements the frozen contracts per docs/specs/...-f1-...md: slug rules, domain models (GUID ids), config schema (small/english defaults), event bus, manifest, stage contract + cascade-disable, registry, generic runner. Contracts only — no stage logic."
```

- [ ] **Step 3: Report the PR URL and CI status; STOP.** The maintainer reviews and merges. Do not run `gh pr merge`.

---

## Self-review notes (coverage vs F1 spec)

- Slugs → Task 1. Enums/GUIDs → Task 2. Domain (GUID ids) → Task 3. Config (partial-valid; **small** model + **English** everywhere; StageName-keyed stage flags) → Task 4. Event bus + isolation → Task 5. Manifest round-trip → Task 6. Stage contract + **cascade-disable folded into `stage.py`**, fixed-point so all transitive/multiple dependents cascade → Task 7. Registry order + dependency validation → Task 8. Generic runner → Task 9.
- Stages are a `StageName` **StrEnum** throughout (config keys, `Stage.name`, `depends_on`, registry, runner).
- `config.example.yaml` (validated against the schema) shipped in Task 10; the README "added later" note removed.
- **Deferred (out of F1):** concrete stages, the background worker + SSE bridge, the real `LLMClient` implementation, filesystem project/set storage.
