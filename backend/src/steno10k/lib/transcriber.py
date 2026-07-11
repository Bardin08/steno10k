from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("steno10k.transcriber")


@dataclass
class TranscribeJob:
    chunk_path: Path
    output_path: Path


@dataclass
class TranscribeSettings:
    model: str
    device: str
    compute_type: str
    language: str
    beam_size: int
    vad_filter: bool
    min_silence_duration_ms: int
    cpu_threads: int


# Per-process cached WhisperModel. Loading the model is expensive, so each worker
# process loads it once on its first job and reuses it. ProcessPoolExecutor gives
# each worker its own interpreter, so these globals are per-process state — no
# cross-worker sharing and no locking. The settings are cached alongside so a job
# with different settings rebuilds the model.
_WORKER_MODEL: Any = None
_WORKER_SETTINGS: TranscribeSettings | None = None


def _ensure_model(settings: TranscribeSettings) -> Any:  # noqa: ANN401
    global _WORKER_MODEL, _WORKER_SETTINGS
    if _WORKER_MODEL is not None and _WORKER_SETTINGS == settings:
        return _WORKER_MODEL
    from faster_whisper import WhisperModel

    _WORKER_MODEL = WhisperModel(
        settings.model,
        device=settings.device,
        compute_type=settings.compute_type,
        cpu_threads=settings.cpu_threads,
    )
    _WORKER_SETTINGS = settings
    return _WORKER_MODEL


def _transcribe_one(job: TranscribeJob, settings: TranscribeSettings) -> tuple[Path, str | None]:
    """Runs inside a worker process. Returns (output_path, error_or_None)."""
    try:
        model = _ensure_model(settings)
        vad_params = (
            {"min_silence_duration_ms": settings.min_silence_duration_ms}
            if settings.vad_filter
            else None
        )
        segments, _info = model.transcribe(
            str(job.chunk_path),
            language=settings.language,
            beam_size=settings.beam_size,
            vad_filter=settings.vad_filter,
            vad_parameters=vad_params,
        )
        text = "\n".join(p for p in (seg.text.strip() for seg in segments) if p).strip()
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        job.output_path.write_text(text, encoding="utf-8")
        return job.output_path, None
    except Exception as e:  # isolation: return the error to the parent process
        return job.output_path, f"{type(e).__name__}: {e}"


def transcribe_chunks(
    jobs: list[TranscribeJob],
    settings: TranscribeSettings,
    max_workers: int,
) -> list[tuple[Path, str | None]]:
    if not jobs:
        return []
    if max_workers <= 1:
        return [_transcribe_one(j, settings) for j in jobs]
    results: list[tuple[Path, str | None]] = []
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_transcribe_one, j, settings): j for j in jobs}
        for fut in as_completed(futures):
            results.append(fut.result())
    return results
