# steno10k M1·S2 — LLM + Assembly Stages

_Second stage-bundle of M1's fan-out. Five concrete `Stage` implementations —
`clean`, `merge`, `summarize`, `bundle`, `notify` — that turn a set's raw chunk
transcripts into a cleaned transcript, a merged document, a summary, and `.docx`
bundles, then emit a completion signal. They sit on the F1 `Stage` backbone and
call into the M1·L capability library; they consume M1·S1's output purely by an
on-disk contract._

Parent vision: `2026-07-11-new-audio-pipeline-vision-design.md`.
Parent decomposition: `2026-07-11-steno10k-m1-decomposition-design.md`.
Sibling library: `2026-07-11-steno10k-m1-l-utility-library-design.md`.
Depends on: F1 (contracts), **M1·L** (prompts, docx). Consumes **M1·S1** output by
contract. Reference/parts bin: `lecturemate10k`.
Status: design spec, for review. Date: 2026-07-11.

---

## 1. Goal & boundary

Deliver the pipeline's back half — the LLM and assembly stages — as five black
boxes implementing the F1 `Stage` protocol, one module each under a **new,
non-frozen** package `steno10k/stages/`. Each stage reads a `StageContext`, does
one job, writes its outputs under the set directory, and returns a `StageResult`.

**Hard boundary — S2 delivers stages, not wiring.**

- **Registry population (`api/stages.py::build_registry()`) and `RunOptions`
  threading are M1·W's job**, under the contract-change lock. S2 must **not** edit
  the frozen `api/` DTO/OpenAPI surface, `contracts/`, or the runner. S2 stages
  are plain classes; W imports and registers them.
- **Dependency direction:** `stages → lib`, `stages → contracts`. Stages never
  import from `api`. (The one `api/` edit S2 makes — the prompts-router rewiring,
  §6 — is an internal-source swap that leaves the API surface byte-identical.)
- **No new fields on frozen F1/F2 contracts.** Where a stage needs a value the
  contracts don't carry, it derives it (see §4, prompt override dir) rather than
  extending a frozen dataclass.

## 2. What S2 consumes (pinned surfaces)

S1 and L are not merged when this spec is written; S2 is planned against their
**declared** surfaces so the units stay consistent.

**From M1·L** (`steno10k/lib/`, per its spec/plan):

- `lib.prompts.load_prompts(override_dir: Path | None) -> Prompts` returning a
  frozen `Prompts(clean: str, summarize: str)`. Each prompt is a **single
  system-prompt string**; `summarize` carries a literal `{target_output_language}`
  placeholder the stage formats. Also `default_prompt(name)` / `resolve_prompt(
  name, override_dir) -> (content, source)` for the router rewiring (§6).
- `lib.docx.build_bundle(pairs: list[tuple[Path, Path]], force: bool,
  err_log: ErrorLog) -> None` — renders each `(markdown_path → docx_path)` pair;
  missing sources skipped silently; one bad render logged and isolated.

**From F1 contracts:** `Stage`/`StageContext`/`StageResult`/`RunOptions`
(`contracts.stage`), `StageName` (`contracts.names`), `StageStatus`
(`contracts.status`), `Config` (`contracts.config`), `ErrorLog`
(`contracts.errors`), `Manifest`/`Recording` (`contracts.manifest`/`.domain`),
and the `LLMClient` protocol — `complete(system, user) -> str` — reached only via
`ctx.llm` (an instance W injects; S2 never constructs one).

**From M1·S1 — on-disk only** (S1 code is never imported): the raw per-chunk
transcripts (§3).

## 3. Inter-stage on-disk contract

S2 pins the layout it reads and writes under each set's directory. **S1 must
produce `transcripts_raw/` in this shape**; recording S2's version here makes it
the shared contract S1 honors.

```
<set_dir>/
  transcripts_raw/<stem>/chunk_NNN.txt        # INPUT — written by S1 `transcribe`
  transcripts_clean/<stem>/chunk_NNN.md       # clean
  merged/raw_transcript.md                    # merge (if output.save_merged_raw_transcript)
  merged/clean_transcript.md                  # merge (if output.save_merged_clean_transcript)
  <output.summary_filename>  (default summary.md)   # summarize (set-dir root)
  bundle/transcript.docx                      # bundle (from merged/clean_transcript.md)
  bundle/summary.docx                         # bundle (from the summary file)
  errors.log                                  # shared ErrorLog sink (F1)
  manifest.json                               # F1 manifest (never an artifact)
```

- `stem = Path(recording.normalized_name).stem`.
- **The manifest is the source of truth for the recording list.** Stages iterate
  `ctx.manifest.recordings`, not filesystem globs, so files dropped in by hand are
  ignored by design (matches the reference's manifest-driven downstream model).
- Chunk transcript files sort lexically (`chunk_000`, `chunk_001`, …) to fix
  ordering within a recording; recordings follow manifest order.

## 4. Stage-by-stage design

All five implement `Stage`: a `name: StageName`, `depends_on: list[StageName]`
matching the frozen `api/stages.py::STAGE_DEPS`, `enabled(cfg, opts) -> bool`, and
`run(ctx) -> StageResult`. Idempotency is uniform: an output that already exists is
skipped unless `ctx.force`. `StageResult.stats` carries per-stage counters.

**`enabled()` gates only the *extra* conditions.** `run_set` already applies the
`cfg.stages.enabled` cascade (via `resolve_enabled`) before calling a stage, so
`enabled()` must **not** re-check `cfg.stages.enabled` — it returns only the stage's
additional gate.

### 4.1 `clean` — LLM, `depends_on=[transcribe]`

For each recording, for each `transcripts_raw/<stem>/chunk_NNN.txt`, call
`ctx.llm.complete(prompts.clean, raw_text)` and write
`transcripts_clean/<stem>/chunk_NNN.md`. Empty raw text writes an empty clean file
(no LLM call). LLM calls run through a **bounded thread pool** sized by
`cfg.llm.concurrency` (a small `stages/_pool.py` helper ported from the reference
`_run_llm_pool`; `concurrency <= 1` runs inline). A failed chunk is logged to
`ctx.errors` and does not abort its siblings.

- `enabled = cfg.llm.enabled and not opts.skip_llm`.
- `run` guards `ctx.llm is None` → `StageResult(SKIPPED, message="no LLM client")`
  (defensive: W injects the client only when LLM is configured).
- `stats = {"cleaned": n, "skipped": s, "failed": f}`; status `OK` (per-item
  failures are logged, not fatal, mirroring the reference).

### 4.2 `merge` — non-LLM, `depends_on=[transcribe]`

Concatenate per-recording chunk transcripts into single Markdown files with a
`## <stem>` / `### <chunk stem>` structure. Writes `merged/raw_transcript.md` from
`transcripts_raw/*/chunk_*.txt` when `output.save_merged_raw_transcript`, and
`merged/clean_transcript.md` from `transcripts_clean/*/chunk_*.md` when
`output.save_merged_clean_transcript`. A raw-only run (clean disabled) is valid —
that is why `merge` depends on `transcribe`, not `clean`. Read failures per file →
`ctx.errors`. `enabled = True`. `stats = {"raw": bool, "clean": bool}`.

### 4.3 `summarize` — LLM, `depends_on=[merge, clean]`

Read `merged/clean_transcript.md`; if missing/empty, log to `ctx.errors` and return
`StageResult(FAILED, message=...)`. Otherwise
`system = prompts.summarize.format(target_output_language=cfg.prompts.target_output_language)`,
`user = transcript`, and write `ctx.llm.complete(system, user)` to the set-dir root
under `cfg.output.summary_filename` (default `summary.md`). Depends on `clean`
because it consumes the *clean* merged transcript (matches `STAGE_DEPS`). Idempotent;
`enabled = cfg.llm.enabled and not opts.skip_llm`; same `ctx.llm is None` guard as
`clean`. `stats = {"chars": len(summary)}`.

### 4.4 `bundle` — non-LLM, `depends_on=[merge]`

Call `lib.docx.build_bundle` with two fixed pairs under `bundle/`:

- `merged/clean_transcript.md → bundle/transcript.docx`
- `<summary_filename> → bundle/summary.docx`

Fixed, domain-neutral names (replacing the reference `{name}_raw` /
`{name}_conspect`); the `bundle/` folder scopes them per set. A missing source is
skipped silently by `build_bundle` (e.g. no summary under `--skip-llm`), so a
transcript-only bundle is valid — that is why `bundle` depends on `merge`, not
`summarize`. Failure detection mirrors the reference: capture `ctx.errors.count`
before/after; if it rose, return `StageResult(FAILED, ...)`, else `OK`.
`enabled = cfg.output.save_bundle_docx`. `stats = {"built": n}`.

### 4.5 `notify` — emit-only, `depends_on=[bundle]`

The terminal stage. It **emits**, it does not push to any external sink (Telegram
is deferred to M3+). It collects the produced artifact paths (summary, the two
`bundle/*.docx`, the merged files) relative to `set_dir` and returns them in
`StageResult.stats` (`{"artifacts": [...]}`). `run_set` then emits
`STAGE_COMPLETED` (and, at loop end, `RUN_COMPLETED`) carrying those stats, which
the SSE bridge and any future subscriber read. **No new `EventKind`** is added
(`contracts.events` is frozen); the completion signal rides existing kinds +
stats. `enabled = True`. Status `OK`.

## 5. Config & context usage (no contract changes)

Every value comes from the existing frozen `Config` / `StageContext`:

- `cfg.llm.enabled`, `cfg.llm.concurrency` — LLM gating + clean fan-out.
- `cfg.prompts.target_output_language` — threaded into the summarize prompt (per
  vision §8; output language is a prompt concern, not an LLM-client concern).
- `cfg.prompts.override_dir` — prompt overrides (§4 prompt loading, §6 router).
- `cfg.output.summary_filename`, `save_merged_raw_transcript`,
  `save_merged_clean_transcript`, `save_bundle_docx` — output shaping/gating.
- `ctx.set_dir`, `ctx.cfg`, `ctx.force`, `ctx.manifest`, `ctx.errors`,
  `ctx.events`, `ctx.llm` — the whole stage surface.

**Prompt override directory resolution.** The LLM stages load prompts via
`lib.prompts.load_prompts(override_dir)` where
`override_dir = Path(cfg.prompts.override_dir) if cfg.prompts.override_dir else
data_root / "prompt_overrides"`, and `data_root = ctx.set_dir.parent.parent`
(`set_dir` is `<data_root>/<project>/<set>`). This matches the F2 prompts router's
resolution exactly, so overrides a user sets in the UI are honored by the stages.
It couples the stage to the storage layout; the alternative — adding `data_root`
to the frozen `StageContext` — is rejected to keep F1 frozen.

## 6. Prompts-router rewiring (the one `api/` edit)

Per the decomposition, S2 rewires `api/routers/prompts.py` to source its defaults
from `lib.prompts` instead of the placeholder `DEFAULT_PROMPTS` dict F2 shipped.

- Replace `DEFAULT_PROMPTS[name]` reads with `lib.prompts.default_prompt(name)` and
  the known-name set with `lib.prompts.PROMPT_NAMES`.
- **The API surface stays byte-identical**: same routes, same `PromptDTO`
  (`name`/`source`/`content`), same `source` values (`"default"`/`"override"`),
  same override-dir convention (already `cfg.prompts.override_dir` else
  `<data_root>/prompt_overrides`). Only the *text of the built-in defaults* and
  their *source module* change.
- Because the DTO/OpenAPI surface is unchanged, this is **not** a frozen-contract
  change and needs no contract lock. S2 still checks `~/.claude/locks/steno10k/`
  before the edit and leaves DTOs/routes untouched. The existing prompts-router
  tests are updated to assert against `lib.prompts` defaults.

## 7. Testing (TDD)

Stages are pure-CI testable — **no** ffmpeg/whisper/network — using fakes:

- **Fake `LLMClient`**: a class with `complete(system, user)` returning canned text
  (or raising, to exercise error paths). Injected as `ctx.llm`.
- **Temp set dirs + hand-built `Manifest`** with `Recording` entries; seed
  `transcripts_raw/<stem>/chunk_*.txt` fixtures to stand in for S1 output.
- Per stage: happy path, idempotent skip vs. `force`, per-item error isolation
  (`ctx.errors.count`), and the `enabled()` gate matrix (LLM off / `skip_llm` /
  `save_bundle_docx`). `merge` covers raw-only (clean disabled). `bundle` uses the
  real `lib.docx` (round-trips a `.docx`) and asserts FAILED on a forced render
  error. `notify` asserts the artifact list in `stats`.
- `_pool` helper: inline (`concurrency=1`) and pooled paths, plus one-bad-item
  isolation.
- Router rewiring: existing `tests/api/test_config_prompts.py` retargeted to the
  `lib.prompts` default text; list/put/reset behavior unchanged.
- **Execution note:** S2 imports `steno10k.lib` (and, via `lib.docx`,
  `python-docx`), so the suite is green only once **M1·L is merged to `main`**.
  Per the build waves, L lands first; S2 branches from `main` after. Planning does
  not wait on L.

## 8. Out of scope for S2

- **Registry wire-up / `RunOptions` threading / `only`/`from_stage` activation** —
  M1·W (frozen `api/`, contract lock).
- **The heavy stages** `normalize`/`chunk`/`transcribe` — M1·S1.
- **The Telegram sink** — deferred M3+; notify is emit-only.
- **`verify`** — stays dropped (vision §5).
- **New config knobs** (retry/whisper) — M2, per L's deferred-config ADR.
- **`manifest.generated_files` maintenance** — the artifacts API rglobs the set
  dir and does not read this field; S2 leaves it to whoever needs it (not required
  for artifact listing).

## 9. Acceptance criteria

- `steno10k/stages/` exists with `clean`, `merge`, `summarize`, `bundle`, `notify`,
  each implementing the F1 `Stage` protocol with `depends_on` matching
  `api/stages.py::STAGE_DEPS`; `stages` imports only `lib`/`contracts`/stdlib
  (no `api` import).
- Given seeded `transcripts_raw/`, a `merge → summarize → bundle → notify` run
  (with `clean` ahead) produces `transcripts_clean/`, `merged/{raw,clean}_
  transcript.md`, the configured summary file, `bundle/{transcript,summary}.docx`,
  and a `notify` `stats.artifacts` list — all under the set dir.
- LLM stages call only `ctx.llm.complete`; are gated off by `skip_llm` /
  `llm.enabled`; and degrade to `SKIPPED` when `ctx.llm is None`.
- Stages are idempotent (skip existing outputs) and honor `ctx.force`; per-item
  failures are logged to `ctx.errors` without aborting siblings; `bundle` reports
  FAILED when a render fails.
- A raw-only pipeline (`clean` disabled) yields `merged/raw_transcript.md` and a
  transcript-only bundle without error.
- `api/routers/prompts.py` sources defaults from `lib.prompts` with the API surface
  unchanged (routes, `PromptDTO`, `source` values); prompts-router tests pass
  against the new defaults; no frozen DTO/OpenAPI change.
- The full stage + router suite passes in CI (no ffmpeg/whisper/network) once L is
  on `main`.
