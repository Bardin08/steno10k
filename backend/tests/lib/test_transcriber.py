from __future__ import annotations

import os
from pathlib import Path

import pytest

from steno10k.lib.transcriber import TranscribeJob, TranscribeSettings, transcribe_chunks

_RUN_WHISPER = os.environ.get("STENO10K_RUN_WHISPER") == "1"


def _settings() -> TranscribeSettings:
    return TranscribeSettings(
        model="tiny",
        device="cpu",
        compute_type="int8",
        language="en",
        beam_size=1,
        vad_filter=False,
        min_silence_duration_ms=500,
        cpu_threads=1,
    )


def test_empty_jobs_returns_empty_list() -> None:
    assert transcribe_chunks([], _settings(), max_workers=1) == []


@pytest.mark.skipif(not _RUN_WHISPER, reason="set STENO10K_RUN_WHISPER=1 to run the real model")
def test_transcribes_a_generated_tone(tmp_path: Path) -> None:
    import subprocess

    wav = tmp_path / "clip.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            str(wav),
        ],
        check=True,
        capture_output=True,
    )
    out = tmp_path / "clip.txt"
    results = transcribe_chunks([TranscribeJob(wav, out)], _settings(), max_workers=1)
    assert results == [(out, None)]
    assert out.exists()
