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

> **Status:** early development. This milestone (M0) stands up the repo, CI/CD,
> and tooling; the pipeline and UI land in subsequent milestones. See
> `docs/specs/` for the design and `docs/plans/` for the build plans.

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
cp config.example.yaml config.yaml
docker compose up
```

Then open the UI at `http://localhost:8000`.

## Hardware

Only transcription is heavy — LLM stages are remote calls. Pick the Whisper size
that fits your machine (total RAM ≈ per-worker footprint × `max_workers`):

| Model     | Disk   | RAM / worker | Quality   | Fits          |
| --------- | ------ | ------------ | --------- | ------------- |
| tiny      | 75 MB  | ~1 GB        | rough     | any laptop    |
| small     | 490 MB | ~2 GB        | good      | 16 GB         |
| medium    | 1.5 GB | ~3 GB        | very good | 16 GB         |
| large-v3  | 3 GB   | ~5 GB        | best      | workstation   |

> Note: faster-whisper (CTranslate2) is **CPU-only on Apple Silicon** (no
> Metal/MPS; GPU acceleration is CUDA-only).

## Docs

- Design specs — `docs/specs/`
- Build plans — `docs/plans/`
- Standards & agent rules — `docs/standards/`, `AGENTS.md`
- Contributing — `CONTRIBUTING.md`

## License

MIT © 2026 Vladyslav Bardin
