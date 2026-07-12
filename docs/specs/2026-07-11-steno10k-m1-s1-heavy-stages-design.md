# M1·S1 — Heavy Stages (normalize · chunk · transcribe) Design

Status: Draft · Date: 2026-07-11 · Milestone: M1·S1 · Depends on: M1·L (utility library, **merged** — `#14`, `c89b23f`)

## 1. Purpose & scope

Implement the three compute-heavy pipeline stages as concrete `Stage`
implementations against the frozen F1 protocol:

1. **normalize** — validate uploaded recordings and probe their durations.
2. **chunk** — split each recording into overlapping windows with ffmpeg.
3. **transcribe** — run faster-whisper over the chunks, in parallel.

Each stage is a thin adapter: it orchestrates `steno10k/lib/` (M1·L) capabilities
and mutates the shared `Manifest`, and holds no media/transcription logic of its
own. The god-function `pipeline.py` from the `lecturemate10k` reference is **not**
ported; its per-stage bodies are re-expressed against the F1 `StageContext`.

### Out of scope

- **Registry wiring.** Populating `api/stages.py::build_registry()` and threading
  `only`/`from_stage`/`force`/`stage_overrides` from the API into `RunOptions` is
  **M1·W** — it touches the frozen `api/` surface under the contract-change lock.
  S1 delivers the stage classes and is verified by direct unit/integration tests,
  not through the live run queue.
- The LLM/assembly stages (clean, merge, summarize, bundle, notify) — **M1·S2**.

## 2. Dependency on M1·L (available)

**M1·L is merged to `main`** (`#14`, `c89b23f`), so S1 branches straight from
current `origin/main` — no stacking or rebasing dance. S1 imports, from the ported
library (signatures confirmed against the merged code):

- `steno10k.lib.ffmpeg`: `ensure_ffmpeg_available() -> None`,
  `get_duration_seconds(audio_path) -> float`,
  `plan_chunks(duration, chunk_seconds, overlap_seconds, min_chunk_seconds) ->
  list[tuple[float, float]]`,
  `extract_chunk(src, dst, start_seconds, end_seconds, output_format) -> None`,
  `FFmpegError`, `SUPPORTED_EXTENSIONS`.
- `steno10k.lib.transcriber`: `TranscribeJob(chunk_path, output_path)`,
  `TranscribeSettings(model, device, compute_type, language, beam_size, vad_filter,
  min_silence_duration_ms, cpu_threads)`,
  `transcribe_chunks(jobs, settings, max_workers) -> list[tuple[Path, str | None]]`.

## 3. File layout

New top-level package (matches the boundary L's import guard already reserves —
`lib` may never import `steno10k.stages`):

```
backend/src/steno10k/stages/
  __init__.py
  _scope.py          # in_run_scope(name, opts) — shared run-option gate (S1 + S2)
  normalize.py       # NormalizeStage
  chunk.py           # ChunkStage
  transcribe.py      # TranscribeStage
backend/tests/stages/
  __init__.py
  test_scope.py
  test_normalize.py
  test_chunk.py
  test_transcribe.py
```

Layering: `lib → contracts`; `stages → lib + contracts`; `api → stages`. Stages
never import `api`. One class per module.

> **Note on `api/stages.py`.** Its docstring says "one module per stage under
> `api/`". That is a stale F2 placeholder: L's import-boundary guard reserves the
> top-level `steno10k.stages` package, which is the cleaner layering. Concrete
> stages live in `steno10k/stages/`, and M1·W imports them into `build_registry()`.

## 4. On-disk layout under `set_dir`

`set_dir = <data_root>/<project-slug>/<set-slug>/`.

| Producer | Path | Notes |
|---|---|---|
| upload (F2) | `set_dir/<normalized_name>` | source audio, already slug-named at upload time |
| chunk | `set_dir/chunks/<stem>/chunk_{i:03d}.<fmt>` | `stem = Path(normalized_name).stem`, `fmt = cfg.audio.output_format` |
| transcribe | `set_dir/transcripts_raw/<stem>/<chunk_stem>.txt` | one `.txt` per chunk |

Directory names (`chunks/`, `transcripts_raw/`) and the `chunk_{i:03d}` pattern
match the `lecturemate10k` reference and are the conventions M1·U reads (by
convention, not a typed contract). Intermediates live in per-recording subdirs so
`set_dir`'s root holds only source audio + bookkeeping (`manifest.json`,
`errors.log`).

### Why there is no copy/rename step

In `lecturemate10k`, `normalize` copied an external input directory into
`normalized_audio/` with safe names. In steno10k that work already happened:
`api/routers/recordings.py::_normalized_filename` slugifies each upload's stem
(F1 slug rules) and writes the file straight to `set_dir/<normalized_name>`, and
records `Recording(source_name, normalized_name)` in the manifest. Re-copying
would duplicate already-normalized (up to 1 GB) audio for no gain. The normalize
**stage** therefore does not copy; see §5.

## 5. Stage behavior

### Shared: `enabled(cfg, opts)` via `in_run_scope`

Every stage implements `enabled` as `return in_run_scope(self.name, opts)`:

```python
def in_run_scope(name: StageName, opts: RunOptions) -> bool:
    if opts.only is not None:
        return name == opts.only
    if opts.from_stage is not None:
        order = list(StageName)
        return order.index(name) >= order.index(opts.from_stage)
    return True
```

Config-level `stages.enabled` and its cascade-disable are already resolved by the
generic `run_set` before it calls `enabled`, so the stage gate only interprets the
run-scope options. `skip_llm` does not affect S1 (no LLM use). One helper, shared
by S1 and S2, keeps this DRY; M1·W's job is only to *populate* `RunOptions` at the
API boundary, not to re-implement the gate.

### normalize — lightweight prepare

- Call `ensure_ffmpeg_available()`. If it raises, log to `ctx.errors` and return
  `StageResult(FAILED)` — the whole pipeline needs ffmpeg, so fail fast.
- For each `recording` in `ctx.manifest.recordings`:
  - Confirm `set_dir/<normalized_name>` exists; if not, log + continue (skip).
  - `recording.duration_seconds = get_duration_seconds(path)`. Probe error → log +
    continue. (Feeds U's recordings table; reused by chunk.)
  - Emit `STAGE_PROGRESS`.
- Return `StageResult(OK, stats={"recordings": n_ok})`.

### chunk

- For each `recording`:
  - duration = `recording.duration_seconds` if set, else `get_duration_seconds()`.
  - `windows = plan_chunks(duration, cfg.audio.chunk_seconds,
    cfg.audio.overlap_seconds, cfg.audio.min_chunk_seconds)`.
  - For each `(start, end)` at index `i`: `dst = chunks/<stem>/chunk_{i:03d}.<fmt>`.
    Skip if `dst` exists and not `ctx.force`; else `extract_chunk(src, dst, start,
    end, cfg.audio.output_format)`.
  - Set `recording.chunks` to the set-dir-relative chunk paths (U's "chunk count"
    = `len(chunks)`).
  - Per-recording error (missing source, ffmpeg failure) → log to `ctx.errors` +
    continue. Emit `STAGE_PROGRESS`.
- Return `StageResult(OK, stats={"recordings": n, "chunks": total})`.

### transcribe

- Discover chunks by scanning `chunks/<stem>/*.<fmt>` on disk (sorted), so a
  `from_stage=transcribe` re-run works without relying on in-memory manifest state.
- Build `TranscribeJob(chunk_path, transcripts_raw/<stem>/<chunk_stem>.txt)` for
  each chunk whose output `.txt` is missing — or all chunks when `ctx.force`.
- Map config → settings; the three knobs F1 froze without are **M1 default
  constants in `transcribe.py`** (per the L deferred-config ADR: "supplied as M1
  defaults by the transcribe stage"):

  ```python
  _M1_BEAM_SIZE = 5
  _M1_VAD_FILTER = True
  _M1_MIN_SILENCE_MS = 500

  TranscribeSettings(
      model=cfg.transcription.model,
      device=cfg.transcription.device,
      compute_type=cfg.transcription.compute_type,
      language=cfg.transcription.language,
      beam_size=_M1_BEAM_SIZE,
      vad_filter=_M1_VAD_FILTER,
      min_silence_duration_ms=_M1_MIN_SILENCE_MS,
      cpu_threads=cfg.transcription.cpu_threads_per_worker,
  )
  # max_workers = cfg.transcription.max_workers
  ```

- `results = transcribe_chunks(jobs, settings, max_workers)`. Each result is
  `(output_path, error_or_None)`; a non-None error → log to `ctx.errors` + continue
  (the worker already isolates per-chunk failures). Emit `STAGE_PROGRESS` as
  results arrive.
- Return `StageResult(OK, stats={"chunks": n, "transcribed": ok, "failed": err})`.

### Error & event conventions

- **Per-item isolation** throughout: one bad recording or chunk is logged to
  `ctx.errors` (`ErrorLog`) and never aborts its siblings — mirrors the reference
  and F2's philosophy.
- The generic `run_set` emits `STAGE_STARTED`, and `STAGE_COMPLETED`/`STAGE_FAILED`
  (keyed off the returned status) with `stats`. Stages additionally emit
  `STAGE_PROGRESS` with `payload={"stage", "progress": 0..1, "current", "total"}`
  for U's SSE progress bar.
- `StageResult` status: `OK` on full or partial success (per-item errors are logged,
  not fatal). Only a missing ffmpeg binary makes **normalize** return `FAILED`.
- The manifest is mutated in place on `ctx.manifest`; `RunQueue` persists it once
  after `run_set` returns, so `duration_seconds`/`chunks` survive to later runs.

## 6. Testing strategy

- **Logic tests (no binaries, run in CI):**
  - `test_scope` — `only` / `from_stage` / default matrix.
  - Each stage with `lib.ffmpeg` / `lib.transcriber` functions monkeypatched:
    assert manifest mutation (`duration_seconds`, `chunks`), on-disk layout, skip
    vs `force`, error isolation (bad item logged to `ErrorLog`, sibling survives),
    and `STAGE_PROGRESS` emission captured via a fake `EventEmitter`.
- **Binary-gated integration (skip cleanly in CI):**
  - normalize / chunk — one real pass over an ffmpeg-generated tone, gated on
    `shutil.which("ffmpeg")`.
  - transcribe — one real pass with the `tiny` model, gated on
    `STENO10K_RUN_WHISPER=1`.
  This mirrors L's binary-gating pattern.

## 7. Decisions

- **Duration** is probed by normalize and recorded on the manifest; chunk reuses it
  (falling back to a probe) so a `from_stage=chunk` re-run is self-sufficient.
- **`Recording.chunks`** stores set-dir-relative chunk paths; U derives chunk count
  from its length.
- **Deferred whisper knobs** (`beam_size`, `vad_filter`, `min_silence_duration_ms`)
  are constants in `transcribe.py`, per the L deferred-config ADR — S1 adds no
  fields to the frozen F1 config.
- **Stages live in `steno10k/stages/`** (not under `api/`), matching L's import
  guard; `enabled` scope logic is a single shared helper for S1 + S2.
- **Registry wiring and run-option passthrough are M1·W**, so S1 is independently
  testable but not queue-drivable until W lands.

## 8. Acceptance criteria

- [ ] `steno10k/stages/` exists with `normalize`, `chunk`, `transcribe` classes
      satisfying the F1 `Stage` protocol; `stages` imports only `lib`/`contracts`.
- [ ] normalize records `duration_seconds` per recording and fails fast when ffmpeg
      is absent; missing files are skipped, not fatal.
- [ ] chunk writes `chunks/<stem>/chunk_{i:03d}.<fmt>`, populates `recording.chunks`,
      and is idempotent (skips existing unless `force`).
- [ ] transcribe writes `transcripts_raw/<stem>/<chunk_stem>.txt`, runs in parallel,
      injects the three M1-default decode knobs, and isolates per-chunk failures.
- [ ] All three stages emit `STAGE_PROGRESS` and honor `only`/`from_stage` via
      `in_run_scope`.
- [ ] Logic tests pass in CI with no ffmpeg/whisper binaries; binary tests skip
      cleanly.
- [ ] `build_registry()` is **not** modified (left to M1·W); no frozen contract is
      touched.
