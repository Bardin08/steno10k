# steno10k M1·U — Minimal Web UI

- **Status:** Draft (brainstormed 2026-07-11)
- **Milestone:** M1·U (build wave 1, parallel with M1·L)
- **Depends on:** F2 (API), F3 (design tokens + primitive library) — both merged.
- **Blocks:** M1·P (single-container packaging).
- **Touches frozen contracts:** none. Builds entirely against the live F2 API
  and F3 primitives. No backend change; `frontend/src/api/schema.ts` is
  regenerated only if the API surface later grows.

## 1. Goal

Ship the minimal set of web screens that let a single local user drive the
whole pipeline from a browser: organize **projects → sets**, **upload** audio,
**enqueue and monitor** runs live over SSE, **read/download** artifacts, and
edit the handful of **config** fields that change between runs. Least code that
covers the loop; every screen composes F3 primitives and obeys the design law
(`docs/standards/ui-design-system.md`).

Non-goals: prompt editing, Telegram config, run-option passthrough
(`from_stage`/`only`), auth, multi-user. See §11 and the M1·U deferrals ADR
(`docs/adr/*-m1-u-web-ui-deferrals.md`).

## 2. Information architecture (shell)

The data is a tree — **Project → Set → (recordings, runs, artifacts)** — and a
*set* is the unit of work. Chosen shell (option A from brainstorming):

- A persistent **sidebar** renders the project→set tree, always navigable.
- A **top nav** exposes the three destinations: Library · Queue · Config.
- Selecting a set opens a **tabbed detail** view (Recordings · Run · Artifacts).

Routing uses `react-router` (`createBrowserRouter`):

| Route | Screen | Notes |
|---|---|---|
| `/` | Library landing | Empty-state / "pick a set" when nothing selected. |
| `/p/:project/s/:set` | Set detail | Active tab via `?tab=recordings\|run\|artifacts` (default `recordings`). |
| `/queue` | Queue | All runs; a row deep-links to that set's Run tab. |
| `/config` | Config | Global pipeline settings. |

A **run already belongs to a set** (`project`/`set_` on `RunDTO`), so there is
no dedicated run-monitor route: the monitor is a component rendered inside the
Run tab and reused from the queue. Clicking a queue row navigates to
`/p/:project/s/:set?tab=run` (decision from brainstorming — deep-link, not a
drawer overlay).

## 3. Architecture & layers

New directories under `frontend/src/`:

```
api/
  client.ts    typed fetch wrapper; unwraps {data,error}; throws ApiError
  keys.ts      TanStack Query key factory
  hooks.ts     query + mutation hooks (one per endpoint group)
  sse.ts       useRunEvents(runId): EventSource -> reduced run state
  schema.ts    (existing, generated) OpenAPI types
app/
  router.tsx   route table (createBrowserRouter)
  AppLayout.tsx  sidebar + top-nav shell; <Outlet/>
screens/
  Library.tsx / Sidebar.tsx
  SetDetail.tsx  + RecordingsTab / RunTab / ArtifactsTab (colocated parts)
  QueueScreen.tsx  (wraps existing QueueMonitor)
  ConfigScreen.tsx
```

Primitives in `components/` are **not modified** (frozen-ish per F3 note; screens
compose them). New composed pieces (UploadZone, StageStepper, RecordingList,
ArtifactList, MarkdownView) are colocated with their screen, not added to the
primitive index.

### 3.1 Typed client (`api/client.ts`)

- Base URL `/api/v1`; in dev a Vite proxy forwards `/api` to the backend
  (`vite.config.ts`). In the packaged container (M1·P) the API is same-origin,
  so the relative base needs no change.
- One low-level `request()` that: sets JSON/multipart headers, parses the
  `{data, error}` envelope, and on a non-null `error` throws
  `ApiError{code, message, details}` (mirrors `backend/api/envelope.py`).
- Thin typed functions per endpoint, parameters/returns typed from `schema.ts`.

### 3.2 Data layer (`api/hooks.ts`, `keys.ts`)

TanStack Query. Queries: `useProjects`, `useProject`, `useSet`, `useRecordings`,
`useArtifacts`, `useRuns`, `useConfig`, `useConfigDefaults`, `useSystem`.
Mutations (each invalidates the affected keys): `createProject`, `createSet`,
`deleteProject/Set/Recording`, `uploadRecordings`, `enqueueRun`, `cancelRun`,
`putConfig`. A `keys.ts` factory keeps invalidation consistent (e.g.
`keys.set(project, set)`, `keys.artifacts(project, set)`, `keys.runs()`).

### 3.3 SSE (`api/sse.ts`)

`useRunEvents(runId)` opens a native `EventSource` on
`/api/v1/runs/{runId}/events` and reduces the stream into:

```ts
interface RunView {
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  stages: Record<StageName, { status: StageStatus; progress?: number }>;
  log: RunEvent[];        // chronological, for the collapsible log
}
```

- Event kinds consumed (frozen `EventKind`): `run_started`, `stage_started`,
  `stage_progress`, `stage_completed`, `stage_failed`, `run_completed`, `error`.
- **Consumed payload shape** (documented contract the reducer relies on):
  `stage_*` events carry `{ stage: StageName, progress?: number /*0..1*/,
  message?: string }`; failures carry `{ stage, error: string }`. This is the
  key names the UI expects — the concrete emitting stages are M1·S1/S2 (§11,
  soft dependency); until then U is tested against this mocked shape.
- On a terminal event (`run_completed`/`error` or a terminal status) the hook
  invalidates `keys.runs()` and `keys.artifacts(project, set)` so the queue and
  Artifacts tab refresh, then closes the source. Reconnects with backoff on a
  transport drop while the run is still non-terminal.

The 8-stage order for the stepper is the frozen `StageName` enum:
`normalize · chunk · transcribe · clean · merge · summarize · bundle · notify`.

## 4. Screens

### 4.1 Sidebar / Library
Project→set tree from `useProjects`. Inline **New project** and **New set**
(both `CreateTitle`). Selecting a set routes to its detail. Empty state
(`EmptyState`) when no projects exist; loading uses `Skeleton`; error uses
`ErrorState` with retry.

### 4.2 Set detail — tabs (`Tabs` primitive, driven by `?tab=`)

- **Recordings** — drag-drop **UploadZone** posting multipart to
  `POST …/recordings`. Supports **multiple files per drop** (a small batch, ~10;
  the endpoint already accepts `files: list`). Client-side guard mirrors the
  backend rules (`_SUPPORTED_EXTENSIONS`, 1 GB cap) for fast feedback; the
  backend remains the authority. Recording list (`RecordingDTO`: source/
  normalized name, duration, chunk count) with per-row delete.
- **Run** — a single **Run set** action calling `enqueueRun({project, set})`.
  Per-run stage/force selection is intentionally omitted: which stages execute
  is a **global** setting on the Config screen (§4.5, `StagesConfig`). Below the
  action, the live **RunMonitor** for the set's active/most-recent run.
- **Artifacts** — list from `useArtifacts` (`ArtifactDTO`: name, kind, size,
  stage). Text/`.md` → click opens a **rendered-markdown** preview
  (`GET …/preview`); any artifact has **download** (`GET …/download`); `docx`
  and binary are download-only. Before a run has produced outputs, the tab
  renders **skeleton placeholders** for the expected artifacts (summary, merged
  transcripts, bundle) — the F3 loading pattern — so the surface reads as
  "pending" rather than showing a bare empty state.

### 4.3 RunMonitor (component, layout A)
Vertical **stage stepper**: one row per stage reusing `QueueRow` /
`StatusPill` / `ProgressBar`; the active stage shows live `stage_progress`. A
**collapsible event log** (collapsed by default) renders `RunView.log`. A
**Cancel** action calls `cancelRun` (visible only while non-terminal). Respects
`useReducedMotion` like the existing QueueMonitor reference.

### 4.4 Queue
Wraps the existing `QueueMonitor` reference screen, fed by `useRuns`. Each
`RunDTO` is mapped to a `QueueItem`; the human title is enriched from the
projects cache (fallback to the `set_` slug). Row → `…/s/:set?tab=run`.

### 4.5 Config
Loads `useConfig`, saves via `putConfig`. Editable sections (per brainstorming
scope):
- **Transcription** — model picker sourced from `/system` `whisper_models`
  (current highlighted), `device`, `compute_type`.
- **LLM** — `model`, `base_url`, `api_key_env`, `enabled` (+ temperature,
  max_tokens).
- **Audio & Output** — chunk/overlap seconds; output toggles (bundle docx,
  merged raw/clean transcript, summary filename).
- **Stages** — enable/disable each of the 8 pipeline stages
  (`StagesConfig.enabled`, keyed by `StageName`). This is the **single place** a
  run's stage set is chosen; it replaces per-run overrides on the Run tab.

Out: Telegram, Prompts.

## 5. Cross-cutting

- **Four states** — every data view uses the F3 pattern already established in
  `QueueMonitor`: loading (`Skeleton`), empty (`EmptyState`), error
  (`ErrorState` + retry), ready.
- **Errors** — `ApiError.code`/`message` surfaced via the existing `toast`
  (`sonner`). Query errors drive the `ErrorState`; mutation errors toast.
- **Design law** — tokens only, motion within Emil's numbers, ban list enforced
  by the existing lint rule; markdown is styled with prose/design tokens and
  rendered without `dangerouslySetInnerHTML`.

## 6. New dependencies

| Dep | Why |
|---|---|
| `@tanstack/react-query` | Caching, refetch, invalidation, mutations across ~15 endpoints. |
| `react-router` | URL-addressable shell (sidebar tree, set tabs, queue, config). |
| `react-markdown` + `remark-gfm` | Render `.md` artifacts safely (no raw HTML injection). |

## 7. Dev & build

- `vite.config.ts` gains a `/api` dev proxy → backend (`http://localhost:8000`).
- Same-origin in the packaged container (M1·P) — relative base needs no change.
- `openapi-typescript` regen (`npm run gen:api`) only if the API surface grows.

## 8. Testing

Vitest + Testing Library (existing setup, conventions in
`docs/standards/typescript.md`). Data-fetching is tested by **mocking the typed
client functions** (`vi.mock`), avoiding an MSW dependency. Per screen: the four
states + the primary interaction (create, upload, enqueue, cancel, save config,
open preview). `useRunEvents` is tested against a **fake `EventSource`** driving
the documented payload shape (§3.3), asserting the reduced `RunView` and
terminal-event invalidation. Follows existing `*.test.tsx` files.

## 9. Acceptance criteria

1. Sidebar lists projects/sets; can create a project and a set; empty/loading/
   error states render.
2. Upload accepts supported audio into a set and the recording appears; delete
   removes it.
3. Run tab enqueues a run and the RunMonitor shows live stage progress over SSE,
   ending on a terminal event; Cancel works.
4. Queue lists runs and a row deep-links to the set's Run tab.
5. Artifacts list renders; `.md`/text previews as rendered markdown; download
   works; docx/binary are download-only; the pre-output state shows skeleton
   placeholders.
6. Config loads, edits (transcription/LLM/audio+output/**stages**), and saves.
7. `pre-commit run --all-files` green; `npm run typecheck`, `lint`, `test`,
   `format:check` green; no design-law lint violations.

## 10. Implementation slices (for the plan)

Vertical, each independently reviewable:

1. **Foundation** — deps, Vite proxy, `api/client.ts`, `keys.ts`, QueryClient
   provider, `app/router.tsx` + `AppLayout` shell, sidebar with projects/sets.
2. **Recordings** — Set detail scaffold + Recordings tab (upload + list/delete).
3. **Runs** — `api/sse.ts`, RunMonitor, Run tab (Run action); wire Queue.
4. **Artifacts** — Artifacts tab + MarkdownView + download.
5. **Config** — Config screen.

## 11. Out of scope / soft dependencies

- **Deferred (see the M1·U deferrals ADR):** prompts editor, Telegram config, run-option
  passthrough (`from_stage`/`only`), auth/multi-user.
- **Per-run stage/force selection is not surfaced.** Which stages run is chosen
  globally on the Config screen (`StagesConfig`). The API's `stage_overrides`/
  `force` request fields are left **unused** by the UI; wiring them (and
  `RunOptions` passthrough like `from_stage`/`only`) remains **M1·W**'s concern —
  the enqueue path needs no UI change when W lands.
- **SSE payload keys** — the reducer depends on the §3.3 key names. Concrete
  stages are **M1·S1/S2**; the integration is verified at the **M1·P** e2e
  smoke. U is unit-tested against the mocked shape and does not block on S.
- **No frozen contract is edited.** If a real gap in the API is discovered
  during U, stop and follow the contract-change lock protocol (AGENTS.md).
