# steno10k M1·C — Thin CLI (design)

_A thin, in-process command-line driver over the steno10k logic surface. Power-user
path and pre-UI de-risking tool: the full local workflow (create → import → run →
inspect) from the terminal, plus per-run stage scoping the web UI deliberately does
not expose._

Parent umbrella: `2026-07-11-steno10k-m1-decomposition-design.md` (unit **M1·C**).
Depends on: **M1·W** (registry wire-up) — merged.
Status: design spec. Date: 2026-07-12.

---

## 1. Purpose & framing

The CLI drives the **logic surface directly** — `Storage`, `ConfigService`,
`build_registry()`, `run_set`, `RunOptions`, `StageContext` — **in-process**. It is
**not** an HTTP client to the API; it imports and calls the same services the API
mounts, over the same on-disk store (`<data_root>/<project>/<set>/`). CLI and a
running server therefore operate on one shared filesystem store.

Two jobs:

1. **De-risk before the UI** — exercise the real pipeline end-to-end from a terminal.
2. **Power-user run scoping** — because the CLI is not the API, **ADR 0002 does not
   bind it**. ADR 0002 deferred `only` / `from_stage` / `stage_overrides` *for the
   API* and explicitly names the CLI as the intended home for `only` / `from_stage`.
   `RunOptions` already carries `force`, `only`, `from_stage`, `skip_llm`, and
   `run_set` already honours all four — the CLI just builds a full `RunOptions` and
   hands it over. No contract change.

**Prime directive alignment:** stdlib `argparse`, **zero new runtime dependencies**;
maximal reuse of existing services; thin handlers.

## 2. Command surface

Entry point `steno10k` (registered as a `console_scripts` in `backend/pyproject.toml`),
also runnable as `python -m steno10k`.

**Global options** (before the subcommand):

- `--data-root PATH` — the store root. Resolution mirrors the API exactly:
  explicit flag → `$STENO10K_DATA_ROOT` → `./data`. Config is `<data-root>/config.yaml`;
  prompt overrides live at `<data-root>/prompt_overrides` (or `config.prompts.override_dir`).
- `--json` — machine-readable output on read/list verbs (see §5).
- `-v`, `--verbose` — verbose logging / per-event detail on `run`.

**Addressing:** a recording set is identified by **two explicit, mandatory
positionals `PROJECT SET`** (both slugs), never a combined `project/set` token.
Different projects can hold sets with the same slug, so both parts must be given
explicitly and unambiguously on every set-scoped verb — `--only` alone cannot
disambiguate *what* is being run. Project-only verbs take a single `PROJECT` slug.

```
steno10k projects list
steno10k projects create TITLE [--icon NAME]
steno10k projects delete PROJECT [-y]

steno10k sets list PROJECT
steno10k sets create PROJECT TITLE
steno10k sets delete PROJECT SET [-y]

steno10k import PROJECT SET FILE [FILE ...]
steno10k recordings list PROJECT SET
steno10k recordings rm   PROJECT SET RECORDING [-y]
steno10k status PROJECT SET
steno10k run    PROJECT SET [--force] [--only STAGE | --from STAGE] [--skip-llm]

steno10k config show
```

Verb notes:

- **`projects create --icon NAME`** — `NAME` is a **Phosphor icon name**, the same set
  the web UI renders (`@phosphor-icons/react`; kebab-case identity, e.g. `book`,
  `wave-sine`, `folder-simple`). **Emoji are rejected** — the repo standard is *"icons
  from Phosphor, never emoji"* (`docs/standards/typescript.md`), and the UI draws the
  glyph from the Phosphor package by name, so an emoji in `Project.icon` would simply
  fail to render. `--icon` is optional (a project may have no icon). The CLI does not
  hard-code the full Phosphor set; it documents in `--help` that the value must be a
  valid Phosphor icon name and points to the canonical Phosphor gallery, and rejects
  obvious non-names (empty, whitespace, or any non-ASCII/emoji character). If a curated
  shared subset is later introduced for the UI picker, the CLI validates against it.
- **`import`** copies audio files into the set directory using the **same logic as the
  API upload route** (`api/routers/recordings.py`): reject extensions outside
  `_SUPPORTED_EXTENSIONS`, slugify each stem with F1 slug rules, dedupe against files
  already in the set dir (`a.m4a` + `a.m4a` → `a_2.m4a`), then
  `storage.add_recordings(...)`. Files are **copied**, not moved; `duration_seconds`
  is left `None` (the pipeline fills chunk/duration data), matching upload behaviour.
  To avoid drift, the shared constants/naming helper are factored so the CLI and the
  route use one definition (see §3).
- **`recordings list` / `recordings rm`** — parity with the UI's recordings tab:
  `list` prints the set's recordings; `rm` removes one by its `RECORDING`
  (normalized name) via `storage.remove_recording(...)`, which drops it from the
  manifest and deletes the file. `-y` skips the confirm.
- **`status`** is the set inspection verb: prints the set's recordings, the
  per-stage status map from the manifest, and the artifacts currently on disk in the
  set dir (e.g. transcripts, `*.docx`, bundle). This folds in what a separate
  `artifacts` verb would show. (`recordings list` is the narrow, scriptable slice of
  the same recording data.)
- **`config show`** prints the resolved `Config` plus `llm_key_present`
  (`bool(os.environ.get(cfg.llm.api_key_env))`) — same signal the system route exposes.
  CLI users **edit config by hand** in `<data-root>/config.yaml`; the CLI does not add
  config-*editing* verbs (§9), which is acceptable precisely because the file is right
  there on disk for a terminal user.
- **`-y`** skips the interactive confirm on destructive `delete` / `rm` verbs
  (non-interactive/CI use).

**Deliberately excluded from M1·C** (§9): config *editing*, prompt-override
management, watch/daemon mode, shell completion.

## 3. Architecture & module layout

New package `backend/src/steno10k/cli/`, small focused files:

| File | Responsibility |
|---|---|
| `cli/app.py` | Build the `argparse` parser tree; resolve global options (data root, json, verbose); dispatch to a handler; own the `ExitCode` enum and the top-level `main(argv)`. |
| `cli/commands.py` | One thin handler per verb — parse the `project/set` positional, call `Storage`/`ConfigService`, hand results to `cli/output.py`. |
| `cli/run.py` | The foreground `run` driver (§4). |
| `cli/output.py` | Rendering: human tables/summaries **and** the `--json` renderer, reusing API DTO shapes so CLI JSON == API JSON. |
| `steno10k/__main__.py` | `python -m steno10k` → `cli.app:main`. |

`console_scripts`: `steno10k = "steno10k.cli.app:main"` in `pyproject.toml`.

**Reuse (no rewrite):** `Storage`, `ConfigService`, `build_registry`,
`run_set`, `RunOptions`, `StageContext`, `ErrorLog`, `EventBus`, the `Recording`
domain model, and the slug helpers are all imported as-is.

**Two small shared-code extractions** (both DRY, neither changes any DTO / route /
OpenAPI, so neither is a frozen-contract change under AGENTS.md):

1. **`make_llm(cfg) -> LLMClient | None`** — the "config → client, graceful skip on
   missing key / disabled" logic currently living as the private `runq._make_llm`.
   Extract to a shared non-API helper (e.g. `steno10k/runtime.py`); `runq` and
   `cli/run.py` both call it. Single definition of the LLM-degradation rule.
2. **Import constants/naming** — `_SUPPORTED_EXTENSIONS` and `_normalized_filename`
   from `api/routers/recordings.py`. Move the reusable pieces to a shared helper the
   route and `import` both import, so the accepted-formats list and naming rule have
   one home.

These extractions are internal refactors of existing modules (behaviour-preserving,
HTTP surface byte-identical). If the reviewer prefers the CLI touch nothing outside
`cli/`, the fallback is a local copy of each helper in `cli/` — noted as the
lower-DRY alternative.

## 4. The `run` driver

`cli/run.py` reconstructs, **synchronously in the foreground**, what
`runq._process` does on its worker thread — but with a full `RunOptions`:

```python
manifest = storage.load_manifest(project, set_)
cfg      = config_service.load()
set_dir  = storage.set_dir(project, set_)
bus      = EventBus()
bus.subscribe(print_event)                       # live per-event output
ctx = StageContext(
    set_dir=set_dir, cfg=cfg, force=force, manifest=manifest,
    errors=ErrorLog(set_dir / "errors.log"), events=bus, llm=make_llm(cfg),
)
run_set(build_registry(), ctx, RunOptions(
    force=force, only=only, from_stage=from_stage, skip_llm=skip_llm,
))
manifest.save(storage.manifest_path(project, set_))
```

**Live output:** the `bus` subscriber prints one concise line per stage lifecycle
event (started / completed + stats / skipped / failed) as it fires — the same events
the SSE bridge feeds the UI. `--verbose` adds per-event detail. After `run_set`
returns, a lecturemate-style summary block prints (stages run, chunks transcribed,
errors, elapsed).

**`--only` / `--from`** take a `StageName` value (validated against the enum, with the
canonical stage list shown in `--help`); they are mutually exclusive (an argparse
mutually-exclusive group, as in lecturemate). **`--skip-llm`** sets
`RunOptions.skip_llm` (LLM stages self-skip). **`--force`** re-runs stages whose
outputs already exist.

**Exit code** derives from terminal state: a run in which any stage fails, or which
raises, exits `1`; a clean run exits `0` (see §6). The manifest is saved on both the
success and handled-failure paths (mirroring `_process`), so partial progress
persists.

## 5. Output modes

- **Human (default):** aligned tables for list verbs; a labelled block for `status`
  and the `run` summary. Written to stdout; errors to stderr.
- **`--json`:** read/list verbs emit JSON built from the **same DTO shapes the API
  returns** (`ProjectDTO`, `RecordingSetDTO`/`SetDTO`, `RecordingDTO`, run summary),
  so scripts get identical structures whether they hit the API or the CLI. `run`
  streams human event lines regardless (it is interactive); `--json` on `run` emits a
  final JSON summary object instead of the human summary block.

## 6. Error handling & exit codes

`ExitCode(IntEnum)` (following lecturemate's pattern, minimally extended):

| Code | Meaning |
|---|---|
| `0` `OK` | Success. |
| `1` `FAILURE` | A run/stage failed, or an unexpected runtime error. |
| `2` `USAGE` | Bad usage, unknown project/set (`Storage.NotFound`), or config load error. |

Handlers translate `Storage.NotFound` → a clear stderr message + exit `2`. Config
load errors (`OSError` / `yaml.YAMLError` / `ValidationError`) → exit `2`.
`run` failures → exit `1`. Unexpected exceptions are logged (with traceback under
`--verbose`) and exit `1`.

## 7. Testing

- `main(argv: list[str] | None) -> int` is the single testable entry; tests drive it
  in-process with a `tmp_path` data root — no subprocess, no server.
- **Coverage:** each verb happy-path; `projects create --icon` accepts a Phosphor
  name and **rejects an emoji / non-name** (exit `2`); `import` (accepted vs rejected
  extension, dedup naming, manifest updated); `recordings rm` (removes from manifest +
  deletes file, unknown recording → exit `2`); `run` with `--only` / `--from` /
  `--skip-llm` / `--force` producing the expected `RunOptions`; `--json` output shape
  parity with the DTO; exit codes for missing project/set, config error, and stage
  failure; the `data-root` resolution precedence (flag > env > default).
- **`run` tests** avoid the heavy ML path: use a minimal/stub registry (or a config
  that disables the heavy stages) so the driver, event streaming, `RunOptions`
  threading, exit-code logic, and manifest save are what's under test — the stage
  internals are already covered by S1/S2.
- Gates: bare `uv run mypy` (strict, over `src` **and** `tests`), `ruff`, `pytest`.

## 8. Documentation (`docs-site/`)

Shipping the CLI includes user-facing docs on the published docs site (Astro + MDX,
`docs-site/`), so the CLI is discoverable alongside the container and configuration
docs. Deliverables:

- **New page `docs-site/src/pages/cli.mdx`** (frontmatter
  `layout: ../layouts/DocsLayout.astro`, `title: CLI`), matching the house style of
  the existing `getting-started.mdx` / `configuration.mdx` pages. Contents:
  - install / invocation (`steno10k …`, `python -m steno10k`, the `--data-root` /
    `$STENO10K_DATA_ROOT` resolution so CLI and container share one store);
  - the full **command reference** (every verb from §2 with its positionals/flags),
    including the `PROJECT SET` addressing convention and the Phosphor `--icon NAME`
    rule (never emoji);
  - the **run-scoping flags** (`--only` / `--from` / `--skip-llm` / `--force`) with
    the canonical stage order and worked examples;
  - `--json` output for scripting; exit-code table.
- **Nav entry** in `docs-site/src/nav.ts`: append `{ title: "CLI", slug: "cli" }`.

The page is copy-editable prose (out of the code test loop); the acceptance check is
that the docs site builds and the new page links from the sidebar. Keep it factual
and terse, consistent with the existing pages.

## 9. Out of scope (M1)

Deferred, each its own future increment if it earns a place:

- Config **editing** from the CLI (M2 — full configurability). A terminal user edits
  `<data-root>/config.yaml` directly, so no config-editing verbs are needed for M1.
- Prompt-override management verbs (steno10k uses a single global
  `prompt_overrides` dir, not lecturemate's per-run `--override-for` named folders).
- Watch/daemon mode, shell completion, coloured/TTY-aware progress bars.
- Going through `RunQueue` (the CLI runs synchronously in the foreground; the queue's
  background-worker + force-only model buys the CLI nothing).

## 10. Scope guards inherited from the umbrella

- Filesystem is the store — no SQLite.
- No new fields on the frozen F1/F2 contracts; the two §3 extractions are
  behaviour-preserving internal refactors, not DTO/OpenAPI changes.
- `verify` stage stays dropped.
