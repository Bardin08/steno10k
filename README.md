<div align="center">

# steno10k

**The written word, on your own machine.**
Local-first audio → clean transcript + summary. Self-hostable, MIT.

</div>

---

steno10k turns folders of audio — lectures, calls, consulting sessions, voice
memos — into clean Markdown transcripts and summaries. Transcription runs
**fully locally** via faster-whisper; cleanup and summarization go through any
**OpenAI-compatible** LLM endpoint. Nothing leaves your machine unless you send
it. Runs as **one container + one volume**.

> **Status:** v1. The full pipeline (all eight stages), web UI, CLI, and
> single-container packaging have shipped. See `docs/specs/` for the design and
> `docs/plans/` for the build plans.

## Pipeline

A `project` groups `sets`; a `set` holds one or more `recordings` and produces
one summary. Each set flows through eight cached stages:

1. **normalize** — safe, unicode-clean filenames
2. **chunk** — overlapping ffmpeg segments
3. **transcribe** — faster-whisper per chunk, in parallel (CPU)
4. **clean** — LLM fixes punctuation & recognition errors
5. **merge** — raw + clean transcripts → Markdown
6. **summarize** — `summary.md` from the merged transcript
7. **bundle** — transcript + summary → `.docx`
8. **notify** — completion events → subscribers (Telegram optional)

Every stage caches to disk, so re-runs and partial runs are cheap. Stages can be
enabled/disabled from config or the UI (dependencies cascade).

## Quickstart

```bash
docker compose up
```

Then open the UI at `http://localhost:8000`. On first boot a default
`config.yaml` is seeded into the data volume — edit it there (or via the UI).
To enable the LLM clean/summarize stages, put `OPENAI_API_KEY=…` in a `.env`
file (loaded by compose). See the [Self-hosting docs](https://bardin08.github.io/steno10k/docs/self-hosting/).

### CLI

A terminal driver, `steno10k`, manages projects/sets/recordings and runs the
pipeline over the same store — see the [CLI docs](https://bardin08.github.io/steno10k/docs/cli/).

```bash
steno10k run my-project week-1 --from transcribe --skip-llm
```

## Hardware

Only transcription is heavy — LLM stages are remote calls. Pick the Whisper size
that fits your machine (total RAM ≈ per-worker footprint × `max_workers`):

| Model     | Disk   | RAM / worker | Quality   | Fits          |
| --------- | ------ | ------------ | --------- | ------------- |
| tiny      | 75 MB  | ~0.5–1 GB    | rough     | any laptop    |
| small     | 490 MB | ~1.5–2 GB    | good      | 16 GB         |
| medium    | 1.5 GB | ~2.5–4 GB    | very good | 16 GB         |
| large-v3  | 3 GB   | ~4–6 GB      | best      | workstation   |

> Full per-model table (incl. `base` + speed) and Docker memory guidance:
> [Self-hosting docs](https://bardin08.github.io/steno10k/docs/self-hosting/#hardware--memory).

> Note: faster-whisper (CTranslate2) is **CPU-only on Apple Silicon** (no
> Metal/MPS; GPU acceleration is CUDA-only).

## Docs

- User docs (getting started, configuration, CLI, self-hosting) —
  [bardin08.github.io/steno10k/docs](https://bardin08.github.io/steno10k/docs/)
- Design specs — `docs/specs/`
- Build plans — `docs/plans/`
- Standards & agent rules — `docs/standards/`, `AGENTS.md`
- Contributing — `CONTRIBUTING.md`

## License

MIT © 2026 Vladyslav Bardin
