# steno10k M1·L — Ported Utility Library

_First fan-out unit of M1. A pure **capability library** (`steno10k/lib/`) that
brings the good parts of `lecturemate10k` onto the F1 contracts. Some modules port
near-intact; others are partial ports (reuse the core, rewrite the surface); the
prompt content is written from scratch. The stages (M1·S1/S2), the CLI (M1·C), and
tests all call into it._

Parent vision: `2026-07-11-new-audio-pipeline-vision-design.md`.
Parent decomposition: `2026-07-11-steno10k-m1-decomposition-design.md`.
Depends on: F1 (domain & core contracts). Reference/parts bin: `lecturemate10k`.
Status: design spec, for review. Date: 2026-07-11.

---

## 1. Goal & boundary

Bring the salvageable utilities from `lecturemate10k` (vision §6) into a clean
`steno10k/lib/` package, adapted to the F1 contracts. **Least code wins** — reuse
what F1/F2 already provide, port pure helpers near-intact, and rewrite anything the
old lecture/conspect/Telegram flow coupled to itself.

**Hard boundary — L is a capability library, nothing more.** It knows nothing
about the `Stage` protocol, `StageContext`, the manifest, the event bus, or the
run queue. Those belong to the stage adapters (M1·S1/S2) that *call* L.

- **Dependency direction is one-way: `lib → contracts` only.** `lib` never imports
  from `api`, `stages`, or the runner. Keeps every capability independently
  unit-testable and equally usable by stages, the CLI, and tests.
- Each module is a small black box with one clear job and a typed signature.

## 2. Per-module port classification

Grounded in the reference source (`src/audio_pipeline/`, ~670 lines). The point of
this table is to be honest about **what is ported vs. rewritten** — not to claim a
blanket "port near-intact".

| L module | ← reference | Classification | What actually happens |
|---|---|---|---|
| `lib/ffmpeg.py` | `ffmpeg_utils.py` | **Port near-intact** | `plan_chunks`, `extract_chunk`, `get_duration_seconds`, `ensure_ffmpeg_available` are pure/self-contained; every `plan_chunks` arg already lives in `AudioConfig`, and `output_format` matches. Only change: module logger → stdlib `logging`. |
| `lib/retry.py` | `retry_utils.py` | **Port near-intact, minus the provider-specific branch** | `compute_backoff_wait`, `extract_retry_after_seconds` are pure and kwarg-driven. **Drop the reference's provider-specific `retry_delay` regex branch** — `extract_retry_after_seconds` keeps only the standard HTTP `Retry-After` header path, which any OpenAI-compatible gateway returns. Provider-neutral (see §3a). |
| `lib/docx.py` — render | `markdown_docx.py` | **Port near-intact** | `render_markdown_to_docx` + `_split_inline` markdown-subset renderer; no domain coupling. Straight copy. |
| `lib/docx.py` — bundle | `bundle.py` | **Partial — rewrite orchestration** | Keep the `_build_one` (render-one-file) core. **Rewrite** `build_bundle`: take explicit `(markdown_path → docx_path)` pairs from the caller and use `contracts.errors.ErrorLog`; **drop** the `filenames` import, the old error-logger dependency, and the hardcoded `conspect.md` / `_raw` / `_conspect` naming. |
| `lib/transcriber.py` | `transcriber.py` | **Port near-intact (L-owned dataclasses)** | Worker + per-process model cache + `transcribe_chunks` port intact. `TranscribeJob`/`TranscribeSettings` stay L-owned. See §3 — `TranscribeSettings` needs three knobs F1 config doesn't have; the transcribe stage supplies M1 defaults. |
| `lib/llm.py` | `llm_client.py` | **Partial — port core, rewrite surface** | Port the `_chat` transport + `_compute_wait` retry logic and expose a single `complete(system, user) -> str` that **implements `contracts.llm.LLMClient`**. **Drop** `clean_transcript` / `make_conspect` / `verify_conspect` (those become prompt+`complete` calls in the stages; `verify` is dropped entirely). See §3 for the config gap. |
| `lib/prompts.py` | `prompts.py` | **Loader reworked + content from scratch** | Rework the default/override loader to **F2's** convention (`PromptsConfig.override_dir`, else `<data-root>/prompt_overrides`, per-name `<name>.md`) — not the reference's `PROMPTS_DIR/<flavor>/` scheme. Name set = the M1 LLM stages (`clean`, `summarize`); drop `conspect`/`verify`. **Write all default prompt content from scratch**: English, domain-neutral (no "lecture"/"conspect"/"Ukrainian"), with target-output-language as a parameter (vision §8). |
| filename normalization | `filenames.py` | **Reuse existing — do not port** | `contracts.slug` already provides `slugify()` + `resolve_collision()` (used by `Storage`). Add only a thin `normalize_recording_name(name) = slugify(stem) + ext` (extension preservation) that reuses `contracts.slug`. |
| — | `logging_utils.py`, `pipeline.py`, `telegram_notify.py`, `cli.py` | **Not ported** | Use stdlib `logging` + F1 events; the god-function is never recreated; Telegram is deferred (M3+); the CLI is its own unit (M1·C). |

## 3. Config gaps (grounded) & the decision

The reference modules read config fields that **F1 froze without**. Enumerated so
the choice is explicit rather than discovered mid-implementation:

- **`LLMConfig` is missing:** `timeout_seconds`, `max_retries`, `retry_initial_wait`,
  `retry_backoff_base`, `retry_max_wait`, `retry_rate_limit_wait`. It also has no
  direct `api_key` and no `output_language`.
- **`TranscriptionConfig` is missing:** `beam_size`, `vad_filter`,
  `min_silence_duration_ms`.

**Decision (KISS — keep F1 frozen, no contract-change lock for L):**

- **Retry/timeout policy is hardcoded as M1 constants in `lib/llm`.** It is not a
  user knob in M1; revisit as configurable in M2 ("configurability polish").
- **Whisper `beam_size`/`vad_filter`/`min_silence_duration_ms` are supplied as M1
  defaults by the transcribe stage** when it maps `TranscriptionConfig` →
  `TranscribeSettings`. Also M2 candidates.
- **Direct `api_key` stays dropped** — F1 is env-only by policy (secrets hygiene);
  `lib/llm` reads `api_key_env` only.
- **`output_language` is not a client concern** — it lives in
  `PromptsConfig.target_output_language` and is threaded into the summarize prompt
  by the stage, not the LLM client.

Net: L adds **zero** fields to the frozen F1 contracts. If M2 wants these knobs,
that is a coordinated `LLMConfig`/`TranscriptionConfig` change then, not now.

**These deferrals are recorded durably as an ADR** —
`docs/adr/0001-defer-llm-and-whisper-config-knobs.md` (status: accepted) — so the
choice and the M2 follow-up are tracked in `docs/`, not just implied in this spec.
Writing that ADR is a deliverable of L (§7).

## 3a. Provider neutrality (no provider-specific bindings)

The LLM layer targets **any OpenAI-API-compatible endpoint** and contains **no
vendor-specific code**. Concretely:

- `lib/llm` talks only the OpenAI-compatible chat-completions surface (base URL +
  model come from `LLMConfig`); it never branches on a specific provider.
- Rate-limit backoff uses the standard HTTP `Retry-After` header plus exponential
  backoff. The reference's provider-specific `retry_delay` string-parsing branch is
  **removed** (§2, `lib/retry`).
- No provider name appears in code, config defaults, or dependencies.

## 4. Dependencies

Add to `backend/pyproject.toml` **runtime** deps:

- `faster-whisper` — pulls `ctranslate2`. Heavy; **CPU-only on Apple Silicon**
  (no Metal/MPS). Document the RAM-per-worker footprint (vision §9).
- `openai` — the OpenAI-compatible client surface.
- `httpx` — promote from dev to runtime (LLM transport / HTTP error introspection).
- `python-docx` — `.docx` rendering.

System dependency: the **`ffmpeg`/`ffprobe` binaries**, guarded at runtime by
`ensure_ffmpeg_available()` and documented for Docker/README (installed in the
image; a clear error locally if missing).

## 5. Testing — ported vs. new

Because §2 is a mix, the tests are a mix too:

- **Ported near-intact** (bring over, retarget imports, keep assertions):
  `test_plan_chunks`, `test_retry_utils`, `test_markdown_docx`.
- **New tests** (for rewritten/from-scratch surfaces):
  - `lib/llm.complete` + retry/backoff mapping, against a mocked transport (no
    network).
  - `lib/prompts` loader: built-in default load, override resolution via
    `PromptsConfig.override_dir`, and rollback-to-default, with the new
    `clean`/`summarize` name set.
  - rewritten `build_bundle` orchestration (explicit source/target pairs, missing
    source skipped, one bad file doesn't abort the sibling).
  - `normalize_recording_name` (extension preservation over `contracts.slug`).
- **Retired / replaced:** the reference `test_filenames` (logic now lives in the
  already-tested `contracts.slug`) and `test_bundle` (asserted the dropped
  `_raw`/`_conspect` naming).
- **Pure-CI rule:** the default suite needs **no** `ffmpeg`/whisper binaries. The
  subprocess/compute paths (`extract_chunk`, `transcribe_chunks`) get thin
  integration tests **skipped when the binary/model is absent** (marker-gated).
- **TDD:** for ported modules, port the test first then the code; for rewritten
  surfaces, write the new test against the target signature first.

## 6. Out of scope for L

- Stage adapters (M1·S1/S2), manifest/event/queue wiring — L is called *by* them.
- `telegram_notify` — deferred sink (M3+); notify is event + UI/SSE only in M1.
- `logging_utils` (the old ad-hoc error logger) — use `contracts.errors.ErrorLog` +
  stdlib logging.
- `pipeline.py` / `process_lecture` god-function — never ported (vision §6).
- **Rewiring the F2 prompts router** to import `lib/prompts` (it currently hardcodes
  its own `DEFAULT_PROMPTS` placeholder) — a coordinated follow-up that touches the
  `api/` surface; lands with the LLM stages (M1·S2) or the wire-up (M1·W).
- Adding retry/whisper knobs to F1 config — an M2 concern, recorded in the §3 ADR.

## 7. Acceptance criteria

- `steno10k/lib/` exists with the §2 modules; `lib` imports only from `contracts`
  and third-party/stdlib — no imports from `api`/`stages` (enforced by an import
  check).
- `lib/llm`’s client satisfies `contracts.llm.LLMClient` (`complete(system, user)`),
  proven by a typed assignment / mypy; it carries **no** domain methods and adds
  **no** fields to F1 config (retry/timeout are in-module constants).
- **No provider-specific code, config, or dependency** anywhere in `lib` — the LLM
  layer works against any OpenAI-compatible endpoint, and backoff relies on the
  standard `Retry-After` header (§3a); a grep for vendor names in `lib/` is empty.
- The deferred-config ADR (`docs/adr/0001-defer-llm-and-whisper-config-knobs.md`)
  exists and states the M1 decision + the M2 follow-up (§3).
- `lib/prompts` ships English, domain-neutral default templates for `clean` and
  `summarize` (no `conspect`/`verify`/Ukrainian text), loads overrides via
  `PromptsConfig.override_dir`, and supports rollback-to-default.
- `normalize_recording_name` reuses `contracts.slug`; no duplicate slug/normalizer
  logic is introduced, and `filenames.py` is not ported.
- `build_bundle` is decoupled from lecture-specific paths/naming and uses
  `contracts.errors.ErrorLog`.
- Ported + new unit tests pass in CI with **no** `ffmpeg`/whisper binaries present;
  binary-dependent tests skip cleanly when absent.
- New runtime deps are declared in `pyproject.toml`; `ffmpeg` is documented as a
  system dependency and guarded by `ensure_ffmpeg_available`.
