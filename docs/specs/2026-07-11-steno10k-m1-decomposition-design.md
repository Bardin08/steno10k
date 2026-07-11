# steno10k M1 — Decomposition (umbrella)

_M1 is "the complete self-hosted solution" (vision §11): the stage pipeline + all
stages through `summary` + FastAPI backend + a minimal React UI, in one container.
It is large, so this umbrella defines the M1 **fan-out units**, their contract
boundaries, dependencies, and build order. Each unit gets its own spec → plan →
implementation cycle._

Parent vision: `2026-07-11-new-audio-pipeline-vision-design.md`.
Status: design spec (umbrella). Date: 2026-07-11.

---

## 1. What already exists (verify-only, not rebuild)

M0/F0 (repo & OSS baseline), F1 (domain & core contracts), and F3 (design tokens +
primitive components) are merged. **F2 (#11) shipped a working API skeleton** that
already delivers much of what a naive M1 plan would rebuild:

- `api/storage.py` — filesystem `Storage` (projects/sets/recordings + manifest I/O).
- `api/runq.py` — background **sequential** `RunQueue` (one set at a time) with a
  per-run event bus.
- `api/sse.py` — SSE streaming of F1 events.
- `api/configsvc.py` — config load/save/resolve.
- All `api/routers/*` wired to those services.

F2 deliberately left three holes, which is exactly the M1 work:

- **`api/stages.py::build_registry()` returns an empty registry** — the pipeline
  runs but does nothing.
- **No `lib/` layer** — zero salvaged utilities; runtime deps are only
  `fastapi` + `pydantic`.
- **`stage_overrides`/`force` accepted by the API but not threaded** into the queue.

## 2. Fan-out units

Grouped bundles (not one-unit-per-stage), per the granularity decision.

| Unit | Scope | Depends on |
|---|---|---|
| **M1·L** — Ported utility library | `steno10k/lib/`: ffmpeg, transcriber, llm (impl of the F1 protocol), retry, docx, prompts. Salvage from `lecturemate10k`. Own spec: `…-m1-l-utility-library-design.md`. | F1 |
| **M1·S1** — Heavy stages | `normalize`, `chunk`, `transcribe` (faster-whisper + ffmpeg) against the F1 `Stage` protocol. | L |
| **M1·S2** — LLM + assembly stages | `clean`, `summarize`, `merge`, `bundle`, `notify`-emit. Includes rewiring the F2 prompts router to `lib/prompts`. | L; S1 outputs by contract |
| **M1·W** — Registry wire-up + run options | Populate `build_registry()` with S1+S2; thread `stage_overrides`/`force`/`only`/`from_stage` → `RunOptions` through `RunQueue.enqueue` + the runs router. **Touches the frozen `api/` surface → contract-change lock protocol.** | S1, S2 |
| **M1·C** — Thin CLI | Drive `Storage` + `RunQueue` from the terminal (power users / de-risk before UI). | W |
| **M1·U** — Minimal Web UI | React screens (projects/sets, upload, queue, run monitor via SSE, artifact view, minimal config) over F3 primitives + F2 API. **Own sub-spec** (vision §10). | F2, F3 |
| **M1·P** — Single-container packaging | Make the M0 Dockerfile skeleton real: build the frontend, serve the SPA from FastAPI, wire the mounted volume, e2e smoke. | U, W |

## 3. Build waves (parallelism)

1. **L** and **U** in parallel now — U codes against the live F2 API + F3 primitives,
   so it does not wait on stages.
2. **S1** + **S2** in parallel (both need L).
3. **W** — needs S1+S2; grab the contract-change lock for the `api/` edits.
4. **C** and **P** — need W; P also needs U.

## 4. Scope guards (carried from the vision)

- **Filesystem is the store — no SQLite in M1** (SQLite only "if ever needed", still
  one volume).
- **Notify is event + UI/SSE only**; the Telegram sink is deferred to M3+.
- **Config/prompt editing in the UI stays minimal**; full configurability is M2.
- **`verify` stage stays dropped** (reintroduced only if it earns its place).
- **No new fields on the frozen F1/F2 contracts from feature units**; genuine
  contract changes follow the lock protocol (AGENTS.md).

## 5. Note

This umbrella is a map, not an implementation plan. Each unit's own spec refines its
design; each plan sequences its tasks. M1·L is specced first and is the current
active unit.
