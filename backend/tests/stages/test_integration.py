from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from stages.conftest import MakeCtx
from steno10k.contracts.config import AudioConfig, Config, TranscriptionConfig
from steno10k.contracts.domain import Recording
from steno10k.contracts.status import StageStatus
from steno10k.stages.chunk import ChunkStage
from steno10k.stages.normalize import NormalizeStage
from steno10k.stages.transcribe import TranscribeStage

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
_RUN_WHISPER = os.environ.get("STENO10K_RUN_WHISPER") == "1"


def _make_tone(path: Path, seconds: int) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_normalize_probes_real_duration(make_ctx: MakeCtx) -> None:
    rec = Recording(source_name="tone.wav", normalized_name="tone.wav")
    ctx, _ = make_ctx([rec])
    _make_tone(ctx.set_dir / "tone.wav", seconds=2)
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert rec.duration_seconds is not None
    assert 1.8 <= rec.duration_seconds <= 2.2


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_chunk_extracts_real_windows(make_ctx: MakeCtx) -> None:
    cfg = Config(
        audio=AudioConfig(
            chunk_seconds=1, overlap_seconds=0, min_chunk_seconds=0, output_format="wav"
        )
    )
    rec = Recording(source_name="tone.wav", normalized_name="tone.wav")
    ctx, _ = make_ctx([rec], cfg=cfg)
    _make_tone(ctx.set_dir / "tone.wav", seconds=3)
    result = ChunkStage().run(ctx)
    assert result.status is StageStatus.OK
    chunks = sorted((ctx.set_dir / "chunks" / "tone").glob("chunk_*.wav"))
    assert len(chunks) >= 2
    assert rec.chunks[0] == "chunks/tone/chunk_000.wav"


@pytest.mark.skipif(
    not (_HAS_FFMPEG and _RUN_WHISPER),
    reason="set STENO10K_RUN_WHISPER=1 (and install ffmpeg) to run the real model",
)
def test_transcribe_real_tiny_model(make_ctx: MakeCtx) -> None:
    cfg = Config(
        audio=AudioConfig(output_format="wav"),
        transcription=TranscriptionConfig(
            model="tiny",
            device="cpu",
            compute_type="int8",
            language="en",
            max_workers=1,
            cpu_threads_per_worker=1,
        ),
    )
    rec = Recording(source_name="tone.wav", normalized_name="tone.wav")
    ctx, _ = make_ctx([rec], cfg=cfg)
    chunk = ctx.set_dir / "chunks" / "tone" / "chunk_000.wav"
    chunk.parent.mkdir(parents=True)
    _make_tone(chunk, seconds=1)
    result = TranscribeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert result.stats["failed"] == 0
    assert (ctx.set_dir / "transcripts_raw" / "tone" / "chunk_000.txt").exists()
