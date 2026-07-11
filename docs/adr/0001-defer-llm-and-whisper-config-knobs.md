# 0001 — Defer LLM retry/timeout and Whisper decode knobs to M2

Status: Accepted · Date: 2026-07-11 · Milestone: M1·L

## Context

The utilities ported from `lecturemate10k` read config fields that the frozen F1
contracts do not define:

- `LLMConfig` (F1) has no `timeout_seconds`, `max_retries`, `retry_initial_wait`,
  `retry_backoff_base`, `retry_max_wait`, `retry_rate_limit_wait`, no direct
  `api_key`, and no `output_language`.
- `TranscriptionConfig` (F1) has no `beam_size`, `vad_filter`, or
  `min_silence_duration_ms`.

F1 is a frozen contract; adding fields is a coordinated change (AGENTS.md lock
protocol). M1's value is a working pipeline, not exhaustive configurability.

## Decision

- LLM **retry/timeout policy is hardcoded** as M1 constants in `lib/llm`
  (`_TIMEOUT_SECONDS=120`, `_MAX_RETRIES=3`, backoff 2·2ⁿ capped at 60s, rate-limit
  floor 60s). Not a user knob in M1.
- Whisper `beam_size`/`vad_filter`/`min_silence_duration_ms` are supplied as **M1
  defaults by the transcribe stage** when it builds `TranscribeSettings`.
- Direct `api_key` stays **dropped** — F1 is env-only by secrets policy; `lib/llm`
  reads `api_key_env` only.
- `output_language` is **not** an LLM-client concern — it lives in
  `PromptsConfig.target_output_language` and is threaded into the summarize prompt
  by the stage.

Net: L adds **zero** fields to F1/F2. No contract-change lock is needed for L.

## Consequences

- Simpler M1, no contract churn, `lib` stays provider-neutral and config-light.
- Users cannot tune retry/decode behavior in M1.
- **M2 ("configurability polish")** revisits this: if these become user knobs, that
  is a coordinated `LLMConfig`/`TranscriptionConfig` change then, surfaced in config
  and the UI.
