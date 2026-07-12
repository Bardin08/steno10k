# 0003 — Defer resource syscheck and UI model download to M2

## Status
Accepted

## Context
M1·P (single-container packaging) surfaced two resource-UX gaps around Whisper:

1. Each transcription worker loads its own model copy, so RAM scales with
   `max_workers`. A user can pick a model/worker combo that OOM-kills the
   container on a default Docker Desktop — which looks like a silent stall.
2. On first transcription the model downloads (minutes), with no in-UI signal, so
   the run appears hung.

M1·P's prime directive is simplicity; a full interactive syscheck and a UI
model-download manager are their own features and would balloon the packaging
unit.

## Decision
M1·P ships only:
- a **non-blocking memory preflight** — logs a warning and records it on the run
  when the configured model × workers likely exceeds the cgroup memory limit;
- **hosting docs** with the hardware/RAM table and Docker memory guidance;
- **model caching to the volume** (download once, persist) with a documented
  "first run downloads the model" note.

Deferred to **M2 — Configurability polish**:
- an **interactive resource syscheck** that recommends a config and warns/refuses
  infeasible selections in config + UI;
- **UI-initiated model download with progress**, with a selector reflecting cached
  models.

## Consequences
- M1·P stays small and shippable; users get honest docs and a safety-net warning.
- The M2 features have a recorded home (vision §9) and this ADR as their rationale.
