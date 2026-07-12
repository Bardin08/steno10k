# steno10k M1·P — Single-container packaging (design)

**Milestone unit:** M1·P (last unit of M1). **Depends:** M1·U, M1·W (both merged).
**Status:** design → plan.

## 1. Framing

The M0 skeleton already exists and is substantial:

- multi-stage `Dockerfile` (build frontend → serve SPA from FastAPI),
- `docker-compose.yml` with a named volume + `.env` passthrough,
- SPA static mount in `api/__init__.py` (`StaticFiles(html=True)` at `/`),
- a CI `docker` job that builds the image (`push: false`),
- a `release.yml` job that pushes `ghcr.io/<owner>/steno10k` on tags.

So M1·P is **not** "build packaging from scratch." It is: **make the skeleton
genuinely run end-to-end, prove it with a smoke gate, and make the resource
(memory) story honest** — closing the real gaps a first boot would expose.

**Prime directive holds:** simplicity first. Close real gaps; do not gold-plate.

## 2. Goals / non-goals

**Goals**

- A fresh `docker compose up` serves the UI and API and survives a hard refresh
  on a client-side route.
- The whisper model downloads **once** and persists across restarts.
- An **ML-free e2e smoke** proves boot + SPA + API round-trip, gating every PR.
- Users can find honest **hardware/memory prerequisites** in the maintained docs
  site, and a fresh install does not silently OOM out of the box.
- A **non-blocking memory preflight** turns "silent OOM stall" into a visible
  warning.

**Non-goals (guardrails)**

- No new `EventKind` or any other edit to frozen contracts (`contracts/`, `api/`,
  `tokens.css`, `standards/`). The preflight rides existing event payloads.
- No interactive syscheck logic (recommend/refuse a model) — **deferred to M2 and
  recorded in §3.F** (vision roadmap + ADR), not dropped.
- No UI model-management / download-from-UI — **deferred to M2 and recorded in
  §3.F** (vision roadmap + ADR), not dropped.
- Smoke stays ML-free (no whisper model, no LLM key).
- No GPU/CUDA packaging; CPU-only int8 as today.

## 3. Scope

### A. Make the container work end-to-end (fix skeleton gaps)

1. **SPA deep-link fallback.** The frontend uses react-router v7
   (`createBrowserRouter`). `StaticFiles(html=True)` serves `index.html` for `/`
   but returns **404** on a hard refresh / deep link like `/p/x/s/y`. Add a
   catch-all that serves `index.html` (HTTP 200) for any path that is **not**
   under `/api` and is not an existing static asset. API 404s must still be JSON
   errors — the fallback only applies to non-`/api` paths.
2. **Model cache → mounted volume.** faster-whisper downloads model weights to the
   default HF cache, which is ephemeral in a container. Set `HF_HOME`
   (and `HF_HUB_CACHE`) to a path under the mounted volume
   (`/data/.cache/huggingface`) in the `Dockerfile` (ENV) and `docker-compose.yml`
   so the model downloads once and persists across restarts.
3. **Runtime hardening.**
   - Run as a **non-root** user.
   - Add a `HEALTHCHECK` hitting `/api/v1/health`.
   - `PYTHONUNBUFFERED=1` so the first-run model-download progress **streams to
     logs** instead of looking hung.
   - Verify the installed-package static path resolves under the uv-synced
     runtime: `api/__init__.py` computes `static` as
     `Path(__file__).parent.parent / "static"`; the Dockerfile copies the built
     SPA to `src/steno10k/static`. Confirm this resolves once the project is
     `uv sync`-installed (editable) — the smoke (B) exercises it.

### B. e2e smoke — the headline; CI gate on every PR

- `scripts/smoke.sh`: `docker build` → `docker run` with a **throwaway volume** →
  poll `GET /api/v1/health` until ready → assert:
  - `GET /` returns `index.html` (200),
  - a **deep link** (e.g. `GET /p/smoke`) also returns `index.html` (200, not 404),
  - an API round-trip: create project → create set → upload a tiny recording →
    assert the artifacts/listing endpoint responds 200.
  - **No whisper, no LLM.** Teardown (container + volume) always, even on failure.
- **Wire into `ci.yml`'s existing `docker` job:** after the build step, run the
  container and the smoke script, then tear down. A regression blocks merge.

### C. Prerequisites & hosting docs — on the MDX docs site (maintained)

The docs site is Astro + MDX (`docs-site/src/pages/*.mdx`, nav in
`docs-site/src/nav.ts`). Documentation is **maintained there**, not the README.

- **New page `docs-site/src/pages/self-hosting.mdx`** (registered in `nav.ts`):
  - the **hardware / RAM table** from vision §9 (per-worker int8/CPU RAM by model),
  - the memory math: **total RAM ≈ per-worker footprint × `max_workers`** (each
    worker loads its own model copy),
  - **Docker Desktop memory guidance** — Mac defaults to ~8 GB (min floor ~4 GB);
    Windows/WSL2 via `.wslconfig`; how to raise it,
  - **CTranslate2 is CPU-only on Apple Silicon** (no Metal/MPS) caveat,
  - `.env` / secrets (`OPENAI_API_KEY`), volume layout,
  - **first-run model-download note**: "downloads the model on first transcribe;
    may take minutes — it is not stuck."
- **Update `getting-started.mdx`** — model-cache volume note + `OPENAI_API_KEY`
  env; cross-link to Self-hosting.
- **Update `configuration.mdx`** — reflect the `max_workers: 2` default and link
  the RAM math.
- **README** keeps a short "Self-hosting" pointer to the docs site (single source
  of truth stays in MDX).

### D. Lightweight memory preflight (non-blocking safety net)

On run enqueue, estimate demand and compare to the container's memory limit:

- `need = perWorker(model) × max_workers + ~0.5 GB overhead`, where
  `perWorker(model)` is a **small lookup table sourced from vision §9** (tiny …
  large-v3).
- `have = ` the container's cgroup memory limit (cgroup v2 `memory.max`, fallback
  cgroup v1 `memory.limit_in_bytes`; treat "max"/unset as unknown → skip).
- If `need > 0.9 × have`, **log a WARNING** and **attach a `warnings` field to the
  existing `RUN_STARTED` event payload** (`Event.payload` is a free-form
  `dict[str, Any]`, so this needs **no new `EventKind` and no contract lock**).
- The run **still proceeds** — this is advisory only, the cheap precursor to M2's
  interactive syscheck. Detection is best-effort (on Docker Desktop the cgroup
  limit reflects the VM, not a per-container `--memory`); a missing/`max` limit
  simply skips the check.

### E. Config default — soften to container-safe

- `config.example.yaml`: `transcription.max_workers` **4 → 2** (small×2 ≈ ~3.5 GB
  peak) so a fresh `docker compose up` fits a modest Docker Desktop allocation out
  of the box. The Self-hosting page documents how to raise it once RAM is
  confirmed.

### F. Record M2 forward-work

Capture the two deferred features so they are not lost — in the vision roadmap
(§9/§11) **and** a new ADR (take the `adr.lock.md` lock to reserve the number):

1. **Interactive syscheck** — inspect container memory/CPU (cgroup), **recommend**
   a model/worker config, and **warn/refuse** infeasible selections (e.g.
   large-v3 × 8 workers on 10 GB), surfaced in both config and the UI.
2. **UI-initiated model download with progress** — let the user pick and download
   a model from the UI with a visible progress indicator, so first-run downloads
   are never mistaken for a hang; selection reflects which models are present.

## 4. Memory model (grounding for C and D)

Per-worker int8/CPU RAM (each worker process loads its own copy); the `small`
figure is measured, the rest extrapolated from parameter counts and the vision §9
table:

| Model | RAM / worker | ×4 (old default) | ×2 (new default) |
| --- | --- | --- | --- |
| tiny | ~0.3–0.5 GB | ~1.5–2 GB | ~1–1.5 GB |
| base | ~0.5–0.7 GB | ~2–3 GB | ~1.5–2 GB |
| **small** | **~1.5 GB** | ~7 GB | **~3.5 GB** |
| medium | ~2.5–3 GB | ~10–12 GB | ~6 GB |
| large-v3 | ~4–5 GB | ~16–20 GB | ~9–10 GB |

Docker Desktop defaults (~8 GB on a 16 GB Mac; min floor ~4 GB) explain why the
old `small×4` default flirts with the ceiling and `large-v3×N` OOM-kills on a
default install — an OOM kill of a worker looks like a silent stall, which D and C
address.

## 5. Components & boundaries

- **`api/__init__.py`** — add the SPA fallback route (A1). Keep the `/api` routers
  registered before the fallback so JSON 404s are preserved.
- **`Dockerfile` / `docker-compose.yml`** — ENV for `HF_HOME`, non-root user,
  `HEALTHCHECK`, `PYTHONUNBUFFERED` (A2, A3).
- **`scripts/smoke.sh`** + **`.github/workflows/ci.yml`** — the smoke gate (B).
- **A small preflight module** (e.g. `api/preflight.py` or within the run-enqueue
  path) — pure function `estimate_need(model, workers)` + `read_cgroup_limit()`;
  unit-testable in isolation; emits WARNING + augments the `RUN_STARTED` payload
  (D). No contract edit.
- **`docs-site/`** — new `self-hosting.mdx` + `nav.ts` + edits to two pages (C).
- **`config.example.yaml`** — default change (E).
- **vision spec + new ADR** — M2 forward-work (F).

## 6. Testing & verification

- **Smoke (B)** green in CI — the primary gate.
- **Unit tests** for the preflight estimator and cgroup parsing (D): known
  model/worker → expected `need`; a stubbed cgroup file → warn/no-warn.
- **SPA fallback** test: a request to a non-`/api` deep link returns the SPA HTML;
  an unknown `/api/...` path returns a JSON 404.
- **Manual acceptance:** `docker compose up` → upload → (with a real key) one full
  run produces a bundle; **restart reuses the cached model** (no re-download);
  the preflight WARNING fires when the configured model×workers exceeds the cgroup
  limit.

## 7. Risks

- **cgroup detection is best-effort** on Docker Desktop (VM-wide, not
  per-container). Mitigated by making D advisory and skipping on unknown limits.
- **Editable-install static path** (A3) — if `uv sync` does not install editable,
  `Path(__file__)` may not point at `src/steno10k/static`. The smoke (B) catches
  this; if it breaks, copy the SPA to the resolved package location instead.
- **Image size** from ffmpeg + deps is acceptable; model stays out of the image
  (cached to volume), keeping the image lean.

## 8. Tracker (Task 0 in the plan)

Per repo convention: create the M1·P issue, add it to project board #16, cut the
issue-numbered branch. The ADR in F takes the shared `adr.lock.md` lock.
