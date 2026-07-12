# Audio Pipeline — Vision & Design Foundation

_**`steno10k`** — a greenfield rewrite of `lecturemate10k`: a **self-hostable,
local-first** tool that turns folders of audio into clean transcripts and
summaries, with a configurable stage pipeline and a **browser UI from day one**.
("steno" = transcription of speech; "10k" keeps the author's signature and the
`lecturemate10k` → `steno10k` portfolio through-line, while shedding "lecture".)_

Status: **vision doc** — the shared starting point for dispatching per-milestone
spec/plan/implementation work. Not itself an implementation plan.
Date: 2026-07-11.

---

## 1. Context & motivation

`lecturemate10k` is a working, genuinely useful local pipeline (transcribe →
clean → summarize any audio, fully local transcription + any OpenAI-compatible
LLM). But it was vibe-coded and carries structural debt: it is tightly coupled to
the term *lecture*, its orchestration is a 100+ line god-function, stages have
ad-hoc signatures, and notification is hardwired to Telegram.

**Decision:** do **not** refactor it in place. Build a **new application from
scratch** in a new GitHub repo, applying lessons learned and reusing the good
parts. The old repo becomes a reference + parts bin.

## 2. Goals & non-goals

**Goals**

- Portfolio-quality open-source project: clean architecture, clear module
  boundaries, tests, approachable README. **Open-sourceable from commit one** —
  every milestone lands in a publishable state.
- **Self-hostable anywhere, local-first**: fully local transcription; LLM stages
  via any OpenAI-compatible endpoint. Shipped as **one container + a mounted
  volume** — simplest possible deployment/start curve.
- **Browser UI from day one** — the primary interface; users need not touch CLI
  or filesystem. (A CLI still exists for power users / automation.)
- Domain-neutral: works for lectures, calls, meetings, consulting sessions,
  voice memos — no term baked to one use case.
- Maximum flexibility / overridability: because it's open source, a user can fork
  and change anything, but the common knobs (prompts, output naming, which stages
  run, language) are overridable via config **and** the UI without editing code.

**Non-goals (for now)**

- SaaS / multi-tenant / hosted service. (Possible future: the author may host and
  sell it as a cheap SaaS later — explicitly **not** a current goal, but the
  architecture should not foreclose it.)
- Multi-user, auth, public-internet deployment. Design targets **self-hosted,
  single-user**.
- Real-time / streaming transcription. This is batch processing (a run can take
  **hours** for large audio + `large-v3`).
- No microservices, no third-party message broker, no separate DB service — see §4.

## 3. Terminology (decided)

A three-level vocabulary, neutral across use cases:

- **`project`** — the top-level container. Groups related **sets** by topic
  (e.g. a course, a client, a research theme). A user organizes their work into
  projects.
- **`set`** — a folder of related audio that collapses into **exactly one** output
  document. Chosen over `lecture`, `session`, `batch` (`session` collides with the
  "a consulting session is one recording" reading; `set` cleanly means "these
  recordings are one result").
- **`recording`** — each individual audio file inside a set. A set holds one or
  more recordings (e.g. lecture parts, or multiple consulting sessions).

So: **a `project` contains `sets`; a `set` contains one or more `recordings` and
produces one output document.**

- The output document is a **`summary`** (replaces the Slavic-jargon `conspect`).
- `set` is a Python builtin → in code the identifier is `recording_set` /
  `set_name`, never a bare `set`. User-facing surfaces stay terse (`--set`).

**Configurable output-file naming (decided).** Output *file names* are defaults,
not hardcoded. The summary defaults to `summary.md`, but a user can override the
filename to anything via config or the UI; the override wins. Scope is **file
names only** — structural terms (`project`, `set`, `recording`) stay fixed.

## 4. Stage architecture & deployment (the backbone)

Designed from scratch so the old god-function never exists — and deliberately
**infrastructure-light**.

- **`StageContext`** — one dataclass carrying everything a stage needs: `out_dir`,
  `cfg`, `force`, error log, manifest, `llm`, and an event emitter.
- **`Stage` protocol** — uniform interface: `name`, `depends_on: list[str]`,
  `enabled(cfg, opts) -> bool`, `run(ctx) -> StageResult`. Each stage lives in its
  own module (`stages/normalize.py`, …): a true black box, one entry point,
  independently testable. `StageResult` carries status + stats, so manifest
  bookkeeping is uniform instead of copy-pasted per stage.
- **Ordered stage registry** — replaces the hardcoded stage list + special cases.
  The pipeline becomes a generic loop: for each active stage, check deps → run →
  record status.
- **In-process, in-memory event mechanism (NOT third-party infrastructure).** The
  pipeline emits events (progress, stage-complete, errors); lightweight in-memory
  subscribers react: a CLI/`tqdm` subscriber, a UI/SSE subscriber, an optional
  Telegram subscriber. This is a plain in-process observer, **not** Kafka/Redis/a
  message broker. Notification stops being "a stage that knows about Telegram"
  without adding any deployable infrastructure.

**Deployment model (decided): one container + one volume.**

- A **single container** holds backend + frontend + everything. No microservices,
  no separate services to orchestrate.
- State lives on a **mounted volume** (the file system is the store): audio,
  transcripts, summaries, manifests. This is what a user mounts on their machine.
- If a real database is ever needed, use **SQLite as a file DB inside the same
  mounted volume** — still one container, still one volume. Not needed initially.

**Preserve from the old design (it was good):** the **disk-cache + manifest**
model. Every stage writes outputs to a dedicated subdir under the set's folder and
skips work if outputs exist. Re-runs and partial runs are cheap, and the manifest
already *is* a job-status model (output on disk ⇔ stage done) — which the UI reads
instead of inventing parallel state. Re-implement it clean.

## 5. Pipeline stages

The proven stage sequence, renamed and placed on the new backbone. One `set` flows
through:

1. **normalize** → copy/rename source recordings to safe, unicode-safe names.
2. **chunk** → split long recordings into overlapping chunks (ffmpeg).
3. **transcribe** → faster-whisper per chunk, in parallel.
4. **clean** → LLM fixes punctuation / obvious recognition errors (conservative).
5. **merge** → concatenate raw + clean transcripts into single Markdown files.
6. **summarize** → LLM produces `summary.md` from the merged clean transcript.
7. **bundle** → render transcript + summary to `.docx` (non-LLM).
8. **notify** → emit a completion event → subscribers (UI, optional Telegram).

**Dropped:** the old `verify` stage (LLM fact-check-worthy claims) is **removed** —
it does not work accurately enough today. It can be reintroduced later if it earns
its place.

## 6. Reuse map (salvage from lecturemate10k)

**Port near-intact** (small, focused, several already unit-tested):

- `ffmpeg_utils.plan_chunks` (pure, tested), `extract_chunk`, duration probing.
- `filenames.normalize_filename` / `resolve_collision` (pure, tested).
- `retry_utils` backoff helpers (pure, tested).
- `llm_client` (OpenAI-compatible + Gemini `retry_delay` parsing).
- `transcriber` faster-whisper worker pattern (per-worker module-global model
  cache — note the RAM implication in §8).
- `markdown_docx` + `bundle` rendering; `prompts` loading + the override concept.

**Redesign from scratch (do NOT port):**

- `pipeline.py` orchestration / `process_lecture` god-function.
- Ad-hoc per-stage signatures + inline manifest bookkeeping.
- Hardwired Telegram notify → replaced by the in-process event mechanism.

## 7. Config-driven stage enable/disable

A `stages` block in config lets users enable/disable stages. Validation rejects
invalid combinations using the registry's `depends_on` graph (e.g. `summarize`
needs `merge`). Useful for the CLI on its own, and it is the contract the UI's
config editor builds on.

## 8. Prompts & language (decided)

- **Default prompt language is English** for all prompts.
- A configurable option tells the model **which language to produce the output
  in** (translate/answer in the target language), independent of prompt language.
- Everything is **overridable** — via config files (fork & edit anything) **and**
  via the UI, with a **rollback-to-default** if a custom prompt misbehaves.

## 9. Hardware & the configurable-Whisper knob

_(Primarily landing-page / README material for later, but accurate and worth
keeping.)_ Only **Whisper transcription** is resource-heavy; LLM stages are remote
API calls (negligible local cost), and the app container is trivial. The single
knob that sets the hardware floor is the Whisper model size.

| Model | Disk | RAM **per worker** (int8/CPU) | Quality | CPU speed (~realtime) |
|---|---|---|---|---|
| tiny | ~75 MB | ~0.5–1 GB | rough | ~10–30× |
| base | ~145 MB | ~1 GB | decent | ~7–15× |
| small | ~490 MB | ~1.5–2 GB | good | ~4–6× |
| medium | ~1.5 GB | ~2.5–4 GB | very good | ~1.5–2× |
| large-v3 | ~3 GB | ~4–6 GB | best | ~0.5–1× |

- **Total RAM ≈ per-worker footprint × `max_workers`** (each worker loads its own
  model copy). Document this so users don't OOM.
- **CTranslate2 is CPU-only on Apple Silicon** (no Metal/MPS; GPU accel is CUDA
  only). Document — it surprises Mac users.
- **M2 — Resource syscheck (deferred from M1·P):** inspect the container's
  memory/CPU (cgroup limits), *recommend* a model + `max_workers` config, and
  *warn or refuse* infeasible selections (e.g. `large-v3 × 8` on 10 GB), surfaced
  in both config and the UI. M1·P ships only the non-blocking warning precursor.
- **M2 — UI-initiated model download (deferred from M1·P):** let the user select
  and download a Whisper model from the UI with a visible progress indicator, so
  the first-run download is never mistaken for a hang; the selector reflects which
  models are already cached. (See ADR 0003.)

## 10. Web UI + FastAPI (from day one; detailed UX in its own spec)

A small **React SPA** (explicitly *not* server-rendered HTML — keep Python out of
the UI) over a **FastAPI** backend, packaged in the single container (§4).
Local, self-hosted, single-user.

- Organize work into **projects → sets**; add recordings; edit config in the
  browser (including stage enable/disable with validation, prompt overrides with
  rollback).
- **Job queue:** the user can add multiple sets to process; they form a **queue**
  and are **processed one at a time** (sequential), reflected live in the UI.
- **View artifacts** (transcripts, merged output, summary) instead of the
  filesystem.
- **Long-running work:** transcription can take **hours**, so runs are background
  jobs with a status model + progress reporting (poll status, or SSE for live
  logs). The disk-cache/manifest already models job status; the UI mostly *reads*
  it. One job runs at a time; the rest wait in the queue. No external job queue
  system — the in-process mechanism (§4) suffices.

The full UI/UX (layout, screens, interactions) gets **its own dedicated spec** to
brainstorm separately.

## 11. Milestones (each lands open-sourceable)

Restructured so **every milestone is a state that can be committed/published**,
and OSS hygiene exists **from the very beginning** — not saved for the end.

- **M0 — Repo & OSS baseline (day one, before feature code):** repo scaffolding,
  project layout, **LICENSE + CONTRIBUTING + basic README**, `config.example.yaml`,
  CI, single-container Dockerfile skeleton. The first committable, public-ready
  state.
- **M1 — Complete self-hosted solution (core pipeline + minimal UI):** the stage
  architecture + all stages (through `summary`) + FastAPI backend + a minimal
  React UI (projects/sets, queue, run, view artifacts), in one container. This is
  the first **complete, publishable** release — it combines what were previously
  "walking skeleton" and "full CLI" into one shippable product, because a partial
  skeleton isn't worth open-sourcing on its own. _(Large — will be decomposed into
  its own spec(s); the UI portion has a dedicated sub-spec per §10.)_
- **M2 — Configurability polish:** config-driven stage enable/disable + prompt
  overrides + output-naming + language options, surfaced in both config and UI.
- **M3+ — Further features** as they earn their place (possible `verify` return,
  more sinks, etc.).

**Landing page (any time from M0 onward):** a basic **GitHub Pages** landing page
for the project — showcase, quick pitch, hardware table (§9), install/self-host
instructions. Small and standalone; can ship as early as M0.x or slot in later.

Each milestone is a separate spec → plan → implementation cycle.

## 12. Open questions / decisions

- **Project name: `steno10k` (decided).** Neutral ("steno" = transcription of
  speech), keeps the author's "10k" signature and the `lecturemate10k` lineage.
  Verified available on PyPI, GitHub, and npm.
- **License: MIT (decided).** Chosen for maximal adoption; simplest, best for a
  portfolio project, and permissive enough that the author can later host a paid
  SaaS.
- **Secrets hygiene:** secrets are **never** committed. They live in environment
  variables / CI-CD secret stores; the repo ships only `config.example.yaml` with
  placeholders. (Not a scrub-history problem — a "never put them in the repo"
  policy.)
- **Prompt default language:** decided — English default, target-output-language
  configurable, fully overridable (see §8).
- **Milestone structure:** restructured per §11; pending confirmation.
