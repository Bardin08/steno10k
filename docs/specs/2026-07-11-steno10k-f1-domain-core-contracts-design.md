# steno10k F1 — Domain & Core Contracts

_Foundation spec 1: the frozen contracts every stage, endpoint, and screen builds
against — domain models, on-disk layout, config schema, the per-set manifest, the
Stage contract, and the in-process event mechanism. Small and stable **by design**:
the smaller this surface, the less cross-agent coordination the fan-out needs._

Parent vision: `2026-07-11-new-audio-pipeline-vision-design.md`.
Depends on: F0 (repo operating model). Status: design spec, for review.
Date: 2026-07-11.

---

## 1. Goal

Define the shared interfaces so a stage can be built as a black box — "give me a
`StageContext`, I return a `StageResult`, I emit events" — with no knowledge of
other stages, the CLI, or the UI. Keep the surface minimal (KISS/DRY); anything
here is a coordinated change under F0 §3.2, so we freeze only what must be shared.

## 2. On-disk layout (the store)

The file system is the store (vision §4). **Projects are first-class from day one**
— a real folder, a real structure, real navigation. One mounted volume:

```
<data-root>/
  <project-slug>/
    project.json             # project metadata (id, title, created)
    <set-slug>/
      manifest.json          # per-set job-status record (§5)
      errors.log
      normalized_audio/      # normalize
      chunks/<recording>/    # chunk
      transcripts_raw/<recording>/
      transcripts_clean/<recording>/
      merged/{raw,clean}_transcript.md
      summary.md             # (filename configurable — §4)
      bundle/*.docx
      notify/sent.json
```

- **`project`** is a fully-usable organizational container (create, list, navigate,
  delete); a CLI run with no project specified uses an implicit `default` project.
- **`set`** is the unit of processing; it produces exactly one summary document.
- **Slugs** are unicode-safe, lowercased, collision-resolved derivations of the
  display title. On collision, suffix with `_2`, `_3`, … The display title is
  preserved in metadata/manifest and never lost.

## 3. Domain models

Plain dataclasses (in-memory view; persisted via `project.json` + the manifest +
filesystem):

- **`Project`** — `id`, `slug`, `title`, `sets: list[RecordingSet]`. Fully usable
  from day one (create / list / navigate / delete).
- **`RecordingSet`** (the "set") — `id`, `slug`, `title`, `project_slug`,
  `recordings: list[Recording]`, `stages: dict[str, StageStatus]`. Produces exactly
  one summary document.
- **`Recording`** — one audio file: `source_name`, `normalized_name`,
  `duration_seconds`, `chunks: list[str]`.
- The output document (**summary**) is a file on disk, not a model — its path/name
  comes from config (§4).

IDs are stable unique identifiers assigned at creation (generated at the creation
boundary, e.g. a UUID — never inside pure functions, per the no-clock/no-random
rule for testable code).

## 4. Config schema (Pydantic v2, partial-valid)

Nested models with defaults so a partial `config.yaml` is valid. Groups: `audio`,
`transcription`, `llm`, `output`, `stages`, `prompts`, and optional sinks
(`telegram`).

- **`stages`** — enable/disable flags per stage, validated against the registry's
  dependency graph (§6). **Cascade disable:** disabling a stage automatically
  disables every stage that (transitively) depends on it — e.g. if `summarize`
  depends on `merge`, disabling `merge` disables `summarize`. The resolver returns
  the effective set of enabled stages and reports which were cascaded off, so the
  CLI and the UI editor show the user the consequence rather than erroring.
- **`output.summary_filename`** — default `summary.md`; overridable (vision §3).
- **`prompts`** — `language` (default English), `target_output_language`, and an
  override directory; overridable via config and UI with rollback (vision §8).
- **Precedence (defined, predictable):** built-in defaults → `config.yaml` → env
  vars → explicit CLI/UI overrides (last wins). Documented in one place.
- Secrets (`llm` key, `telegram` token) come from env vars, never committed.

## 5. Manifest (per-set job-status record)

`manifest.json` per set is the source of truth for what's done — output on disk ⇔
stage done (vision §4). Schema:

- `id` — stable unique set identifier
- `project_slug`, `set_slug`, `title`
- `source_files: list[str]`
- `recordings: list[Recording]` (with chunks + durations)
- `stages: dict[str, StageStatus]`  (`ok` | `failed` | `skipped` | `pending`)
- `generated_files: list[str]`, `errors: int`
- timestamps (`created`, `updated`) — passed in, not read from a clock in pure code

Loaded at the start of a set's processing, mutated in place by stages, saved at the
end. This is what the UI reads for status instead of inventing parallel state.

## 6. Stage contract (the parallelization interface)

The single most important contract — every stage conforms, nothing else needs to.

```python
@dataclass
class StageContext:
    set_dir: Path
    cfg: Config
    force: bool
    manifest: Manifest
    errors: ErrorLog
    events: EventEmitter        # §7
    llm: LLMClient | None       # None when the stage is non-LLM or LLM disabled

class StageStatus(StrEnum): OK; FAILED; SKIPPED; PENDING

@dataclass
class StageResult:
    status: StageStatus
    stats: dict[str, int]       # e.g. {"chunks_transcribed": 42}
    message: str | None = None

class Stage(Protocol):
    name: str
    depends_on: list[str]
    def enabled(self, cfg: Config, opts: RunOptions) -> bool: ...
    def run(self, ctx: StageContext) -> StageResult: ...
```

- **Registry:** an ordered list of `Stage` instances is the single source of stage
  order + dependencies. `--only` / `--from` validate against it; the UI's
  enable/disable validates against `depends_on` and computes the cascade (§4).
- Uniform `StageResult` means manifest bookkeeping is done **once** by the runner,
  not per stage.
- Each stage lives in its own module and is independently testable with a fake
  `StageContext`.

## 7. In-process event mechanism (no third-party infra)

A plain in-process emitter (vision §4) — **not** Kafka/Redis.

```python
class Event:  # kind + payload
    RUN_STARTED; STAGE_STARTED; STAGE_PROGRESS; STAGE_COMPLETED;
    STAGE_FAILED; RUN_COMPLETED; ERROR

class EventEmitter:      # what stages hold (emit only)
    def emit(self, event: Event) -> None: ...

class EventBus(EventEmitter):    # emit + subscribe
    def subscribe(self, handler: Callable[[Event], None]) -> None: ...
```

- **Subscribers** are the "sinks": a CLI/`tqdm` subscriber, an SSE subscriber (feeds
  the UI), an optional Telegram subscriber. Notification is a subscriber, never a
  stage that knows about Telegram.
- Dispatch is **synchronous and thread-safe**; a subscriber that raises never
  breaks the pipeline (isolation boundary). The SSE subscriber bridges to the async
  API via a thread-safe queue (§8).

## 8. Execution model

- **A run processes one set** through its active stages: generic loop over the
  registry → for each active stage, check deps → `run(ctx)` → record `StageResult`
  in the manifest → emit events. No per-stage special-casing.
- **Stages are synchronous.** Long/parallel work inside a stage uses a
  `ProcessPoolExecutor` for faster-whisper (CPU-bound, releases the GIL) and a
  `ThreadPoolExecutor` for LLM calls (I/O-bound). Progress is surfaced via `events`.
- **Runs execute in a background worker** (the API returns immediately; vision §10),
  with events bridged worker → SSE via a thread-safe queue. One run at a time;
  others queue.
- **Error isolation** boundaries: per-set errors to `errors.log`; one bad
  recording/chunk never aborts the run; the run loop wraps each set.

## 9. Frozen vs extensible

- **Frozen (coordinated changes only, F0 §3.2):** `StageContext`, `Stage`,
  `StageResult`, `Event`/`EventEmitter` signatures, the `Config`/`Manifest` schemas,
  the on-disk layout.
- **Extensible without coordination:** adding a new `Stage` module, a new subscriber,
  a new nested config group with defaults.

## 10. Resolved decisions

- **Projects are real from day one** (real folder, structure, navigation); CLI
  defaults to an implicit `default` project.
- **Synchronous pipeline in a background worker**, events bridged to async SSE via a
  thread-safe queue (no async coloring of stage code).
- **Slug collisions** are resolved by numeric suffix (`_2`, `_3`, …).

## 11. Acceptance criteria

- Dataclasses/schemas for domain models, `Config`, `Manifest` exist with tests
  (partial-config validity; manifest round-trip load/save; cascade-disable resolver).
- `StageContext`, `Stage`, `StageResult`, `StageStatus`, and the event types are
  defined and documented as the frozen contract.
- A stage registry with dependency validation exists and is unit-tested: rejects an
  invalid explicit combo and correctly computes cascade disables.
- An `EventBus` with subscribe/emit + a trivial CLI subscriber, unit-tested for
  synchronous dispatch and subscriber-error isolation.
- No stage logic yet — this foundation ships the contracts + tests only, so the
  fan-out can begin against a stable surface.
