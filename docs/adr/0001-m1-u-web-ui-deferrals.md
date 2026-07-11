# ADR — M1·U Web UI deferrals

- **Number:** provisional `0001` — reserved via
  `~/.claude/locks/steno10k/adr-numbering.lock.md`; the ADR sequence is a shared
  resource, so the final number (and filename) is confirmed at merge to avoid a
  concurrency collision. Do not hard-code this number in other documents.
- **Status:** Accepted
- **Date:** 2026-07-11
- **Context milestone:** M1·U (Minimal Web UI)
- **Related:** `docs/specs/2026-07-11-steno10k-m1-u-web-ui-design.md`

## Context

M1·U ships the minimal web UI over the frozen F2 API and F3 primitives. Several
capabilities are reachable from the API surface but are either out of the
milestone's scope or not yet wired end-to-end. This ADR records what M1·U
deliberately leaves out and why, so later milestones and reviewers don't read
the gaps as oversights.

## Decision

### 1. Deferred screens/features (not built in M1·U)

- **Prompts editor** — the `/prompts` endpoints (list/put/reset) exist, but
  prompt authoring is deferred to a later milestone. Rationale: it is a distinct
  editing surface with its own override/reset semantics; the core pipeline loop
  (organize → upload → run → read) does not depend on it.
- **Telegram config** — `TelegramConfig` is omitted from the Config screen.
  Rationale: notifications are optional and set-once; keeping Config minimal.
- **Run-option passthrough** (`from_stage`, `only`) — not surfaced. These are
  part of the `RunOptions` wiring owned by **M1·W** and are not yet in the API
  request contract. Rationale: no contract to build against yet.
- **Auth / multi-user** — out of scope; the app is a single-user local tool.

### 2. Per-run stage selection omitted in favor of global config

The Run tab exposes only a single **Run set** action — no per-stage toggles and
no `force` control. Which stages execute is a **global** setting on the Config
screen (`StagesConfig.enabled`, keyed by `StageName`).

- **Why:** a single-user local tool rarely needs to vary the stage set per run,
  so a global toggle is simpler and keeps the enqueue path a one-click action. It
  also avoids shipping a control that would be inert until M1·W wired it through.
- **Consequence:** the API's `stage_overrides`/`force` request fields are left
  **unused** by the M1·U UI. Threading them (and `RunOptions` passthrough such as
  `from_stage`/`only`) remains **M1·W**'s concern; the UI needs no change when W
  lands.

### 3. SSE payload-key contract (soft dependency)

The RunMonitor reducer consumes a documented payload shape on `stage_*` events
(`{ stage, progress?, message?, error? }`). The concrete emitting stages are
**M1·S1/S2**. M1·U depends on these key names by convention, not by a typed
contract. Verified at the **M1·P** e2e smoke; unit-tested in U against a mocked
shape. If S1/S2 emit different keys, reconcile there (or promote the payload
shape into the frozen events contract via the lock protocol).

## Consequences

- M1·U touches **no frozen contract** and needs no coordination lock.
- Stage on/off lives globally in Config. If per-run variation is ever needed,
  M1·W's `stage_overrides` wiring plus a Run-tab control can add it later without
  reworking the enqueue path.
- The deferred items (prompts, Telegram, run-options, auth) remain tracked as
  future work; this ADR is the reference for why they are absent from M1·U.
