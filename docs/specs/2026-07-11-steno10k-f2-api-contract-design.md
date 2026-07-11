# steno10k F2 — API Contract

_Foundation spec 2: the HTTP surface between the React SPA and the FastAPI backend.
Freezing this contract is what lets frontend and backend be built in parallel — the
frontend generates its TypeScript types from this schema, so both sides code against
one source of truth._

Parent vision: `2026-07-11-new-audio-pipeline-vision-design.md`.
Depends on: F0 (repo operating model), F1 (domain & core contracts).
Status: design spec, for review. Date: 2026-07-11.

---

## 1. Goal & conventions

- **REST + JSON**, resource-oriented, all under **`/api/v1`** (versioned prefix so
  the contract can evolve without breaking old clients). The SPA is served by the
  same container at `/`.
- **OpenAPI is the frozen contract.** FastAPI auto-generates the OpenAPI schema from
  Pydantic request/response models; the frontend generates types from it
  (`openapi-typescript`). No hand-written, drift-prone client. Changing the schema
  is a coordinated change (F0 §3.2).
- **Stable response envelope (§3.1)** wraps every JSON response as a
  data-or-error pair — one reusable shape the frontend always handles the same way.
- **Live progress via SSE** (not WebSocket): long runs stream events to the UI.
- **Single-user, local, no auth** (vision non-goals). The surface leaves room for a
  future auth middleware.
- Keep the surface small and predictable (KISS).

## 2. Resource model & endpoints

### Projects
- `GET  /api/v1/projects` — list.
- `POST /api/v1/projects` — create `{title}` → `Project`.
- `GET  /api/v1/projects/{project}` — get (with its sets).
- `DELETE /api/v1/projects/{project}` — delete.

### Sets (within a project)
- `GET  /api/v1/projects/{project}/sets` — list.
- `POST /api/v1/projects/{project}/sets` — create `{title}` → `RecordingSet`.
- `GET  /api/v1/projects/{project}/sets/{set}` — get (recordings + per-stage status).
- `DELETE /api/v1/projects/{project}/sets/{set}` — delete.

### Recordings (audio files in a set)
- `POST /api/v1/projects/{project}/sets/{set}/recordings` — **multipart upload** of
  one or more audio files → `[Recording]`. **Max 1 GB per file** (§5).
- `GET  /api/v1/projects/{project}/sets/{set}/recordings` — list.
- `DELETE /api/v1/projects/{project}/sets/{set}/recordings/{recording}` — delete.

### Artifacts (generated outputs) — preview and download are **separate endpoints**
- `GET /api/v1/projects/{project}/sets/{set}/artifacts` — list generated files (name,
  kind, size, producing stage).
- `GET …/artifacts/{path}/preview` — **preview**: returns raw text/markdown content
  for the frontend to render (keeps Python out of the UI, vision).
- `GET …/artifacts/{path}/download` — **download**: streams the file as an attachment
  (binary-safe, correct content type; e.g. `.docx`).

### Runs / queue (processing)
A `Run` is a queued processing request for one set; when it reaches the front it
becomes the active run. Statuses: `queued | running | completed | failed | cancelled`.
- `POST /api/v1/runs` — enqueue `{project, set, stage_overrides?, force?}` → `Run`
  (with `id`, `position`). Optional per-run stage overrides layer on global config.
- `GET  /api/v1/runs` — the queue + recent history (statuses, positions, progress).
- `GET  /api/v1/runs/{id}` — one run's status + latest progress snapshot.
- `DELETE /api/v1/runs/{id}` — cancel a running run or remove a queued one.
- `GET  /api/v1/runs/{id}/events` — **SSE** stream of this run's events (§4).

### Config
- `GET /api/v1/config` — current effective config.
- `PUT /api/v1/config` — update; response includes the **cascade-disable resolution**
  (effective enabled stages + which were cascaded off, F1 §4).
- `GET /api/v1/config/defaults` — built-in defaults (for "reset to default").

### Prompts
- `GET  /api/v1/prompts` — current prompts (default vs overridden per name).
- `PUT  /api/v1/prompts/{name}` — set an override.
- `POST /api/v1/prompts/{name}/reset` — **rollback to default** (vision §8).

### System / meta
- `GET /api/v1/health` — liveness.
- `GET /api/v1/system` — read-only info the UI needs: available Whisper models,
  current model, worker counts, data-root path.

## 3. Schemas (DTOs)

Request/response models are Pydantic and mirror F1 domain models, exposed as DTOs
(never leak internal-only fields). Core response types: `Project`, `RecordingSet`
(includes `stages: {name: status}`), `Recording`, `Artifact`, `Run`, `Config`,
`Prompts`, `SystemInfo`. Create requests are minimal (`{title}`); the server assigns
`id`/`slug`.

### 3.1 Response envelope (stable, reusable)

Every JSON response uses one wrapper — a data-or-error pair:

```
ApiResponse<T> = { "data": T | null, "error": ErrorModel | null }
ErrorModel      = { "code": string, "message": string, "details"?: object }
```

- Success → `{ "data": <payload>, "error": null }`.
- Failure → `{ "data": null, "error": { code, message, details? } }`, with the
  matching HTTP status.
- `code` is a stable snake_case string the frontend switches on (e.g.
  `set_not_found`, `file_too_large`, `validation_error`).
- **Exceptions (not enveloped):** the artifact **download** stream and the **SSE**
  event stream are raw by nature.

## 4. Events over SSE

The SSE stream serializes F1 `Event`s to JSON:

```
event: stage_progress
data: {"run_id","project","set","stage","done","total","message"}
```

Kinds mirror F1: `run_started, stage_started, stage_progress, stage_completed,
stage_failed, run_completed, error`. The UI subscribes on run start and updates the
queue/monitor live; on reconnect it re-reads `GET /api/v1/runs/{id}` for the current
snapshot (SSE is for deltas; the manifest/run status is the truth).

## 5. Uploads & downloads

- **Upload:** multipart `POST …/recordings`, accepts supported audio extensions; the
  server normalizes filenames (F1 slug rules) and records them.
- **Max file size: 1 GB per file.** A larger file returns a predictable error
  (`code: "file_too_large"`) whose message says large files aren't supported yet and
  invites the user to open a GitHub issue if they need them. Rejected/unsupported
  types surface the same way.
- **Download:** the artifact download endpoint streams with correct content types;
  `.docx` as attachment.

## 6. Errors

Errors are the `error` half of the §3.1 envelope — no separate error format. Standard
status codes: 404 not found, 409 conflict (duplicate / failed precondition), 413/422
for oversize/validation, 500 unexpected. Every error carries a stable `code`.

## 7. Frozen vs extensible

- **Frozen (coordinated change, F0 §3.2):** the `/api/v1` paths, request/response DTO
  shapes, the `ApiResponse` envelope, the SSE event JSON shape.
- **Extensible without coordination:** adding a new endpoint, adding an *optional*
  response field, adding a new SSE event kind, adding a new error `code`.

## 8. Resolved decisions

- **Path identifiers: slugs** (`/projects/my-course/sets/week-1`); `id` is available
  in bodies. (ID-based navigation is not offered now.)
- **Config scope: one global config** for M1 (single-user); per-project overrides can
  come later.
- **Artifact serving: raw content, frontend renders** markdown; download is a
  separate endpoint (§2).

## 9. Acceptance criteria

- The endpoint set above is defined as FastAPI routes with Pydantic DTOs and the
  `ApiResponse` envelope, producing a valid OpenAPI schema under `/api/v1`.
- `openapi-typescript` generates frontend types from that schema in CI (drift between
  backend and generated types fails CI).
- SSE endpoint contract documented with the event JSON shape; a smoke test proves an
  event round-trips from the bus (F1 §7) to an SSE client.
- Envelope + error middleware produce the §3.1/§6 shape for validation, not-found,
  oversize-upload, and unexpected errors, covered by tests.
- No business logic beyond thin handlers — this foundation freezes the contract and
  wiring so frontend and backend fan-out can proceed in parallel.
