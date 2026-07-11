from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from steno10k.lib.ffmpeg import get_duration_seconds, plan_chunks

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def test_empty_audio_returns_no_chunks() -> None:
    assert (
        plan_chunks(duration=0, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == []
    )


def test_short_audio_returns_single_chunk() -> None:
    assert plan_chunks(
        duration=300, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20
    ) == [(0.0, 300.0)]


def test_exact_chunk_length_returns_one_chunk() -> None:
    assert plan_chunks(
        duration=600, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20
    ) == [(0.0, 600.0)]


def test_two_chunks_have_overlap_on_second() -> None:
    assert plan_chunks(
        duration=900, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20
    ) == [(0.0, 600.0), (585.0, 900.0)]


def test_first_chunk_never_has_negative_start() -> None:
    chunks = plan_chunks(duration=1200, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20)
    assert chunks[0][0] == 0.0


def test_skips_trailing_chunk_below_min_seconds() -> None:
    assert plan_chunks(
        duration=601, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20
    ) == [(0.0, 600.0)]


def test_keeps_trailing_chunk_at_or_above_min_seconds() -> None:
    assert plan_chunks(
        duration=625, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20
    ) == [(0.0, 600.0), (585.0, 625.0)]


def test_first_chunk_can_be_short() -> None:
    assert plan_chunks(
        duration=10, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20
    ) == [(0.0, 10.0)]


def test_min_chunk_seconds_zero_keeps_short_trailing_chunk() -> None:
    assert plan_chunks(
        duration=601, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=0
    ) == [(0.0, 600.0), (585.0, 601.0)]


def test_chunks_cover_entire_audio() -> None:
    chunks = plan_chunks(
        duration=1800.0, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20
    )
    assert chunks[0][0] == 0.0
    assert chunks[-1][1] == 1800.0


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_get_duration_of_generated_tone(tmp_path: Path) -> None:
    wav = tmp_path / "tone.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            str(wav),
        ],
        check=True,
        capture_output=True,
    )
    assert 1.8 <= get_duration_seconds(wav) <= 2.2
