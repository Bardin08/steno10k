# Changelog

All notable changes to steno10k are recorded here, following
[Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/). Curated entries take precedence; the
release workflow only auto-generates a section when none exists for the tag.

## [1.0.0] - 2026-07-15

First public release. steno10k turns folders of audio — lectures, calls, voice
memos — into clean Markdown transcripts and summaries. Transcription runs fully
locally via faster-whisper; cleanup and summarization go through any
OpenAI-compatible endpoint. Ships as one container + one volume.

### Added

- **Eight-stage pipeline** with per-file disk caching — normalize, chunk,
  transcribe (parallel CPU workers), clean (LLM), merge, summarize (LLM),
  bundle (`.docx`), notify (Telegram, optional). Stages enable/disable from
  config with an automatic dependency cascade.
- **Web UI** — projects/sets sidebar, set detail, live run monitor over SSE, and
  a two-pane configuration screen, built on a design-token system.
- **CLI** (`steno10k`) — a terminal driver over the same on-disk store, with
  per-run stage scoping (`--only` / `--from` / `--skip-llm` / `--force`) and
  `--json` output for scripting.
- **REST API** (FastAPI) with a published OpenAPI schema; the React SPA is served
  from the same container with SPA fallback.
- **Single-container packaging** — one image, one mounted volume holding
  recordings, artifacts, `config.yaml`, and the cached Whisper model; the release
  image is published to GHCR on tag.
- **Docs site** (MDX on GitHub Pages) — getting started, configuration, CLI, and
  self-hosting guides.

[1.0.0]: https://github.com/Bardin08/steno10k/releases/tag/v1.0.0
