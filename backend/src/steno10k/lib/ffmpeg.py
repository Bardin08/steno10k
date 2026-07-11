from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("steno10k.ffmpeg")

SUPPORTED_EXTENSIONS = {".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg"}


class FFmpegError(RuntimeError):
    pass


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError("ffmpeg not found in PATH. Install it (e.g. `brew install ffmpeg`).")
    if shutil.which("ffprobe") is None:
        raise FFmpegError("ffprobe not found in PATH. Install ffmpeg (e.g. `brew install ffmpeg`).")


def get_duration_seconds(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(audio_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"ffprobe failed for {audio_path}: {e.stderr}") from e
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def extract_chunk(
    src: Path,
    dst: Path,
    start_seconds: float,
    end_seconds: float,
    output_format: str = "m4a",
) -> None:
    """Extract chunk [start, end) into dst, re-encoding for accurate cuts."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.0, end_seconds - start_seconds)
    if duration <= 0:
        raise FFmpegError(f"Invalid chunk duration for {src}: {start_seconds}-{end_seconds}")

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        str(src),
        "-t",
        f"{duration:.3f}",
        "-vn",
    ]
    if output_format == "m4a":
        cmd += ["-c:a", "aac", "-b:a", "96k"]
    elif output_format == "mp3":
        cmd += ["-c:a", "libmp3lame", "-b:a", "96k"]
    elif output_format == "wav":
        cmd += ["-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1"]
    else:
        cmd += ["-c:a", "copy"]
    cmd.append(str(dst))

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"ffmpeg chunk failed for {src}: {e.stderr}") from e


def plan_chunks(
    duration: float,
    chunk_seconds: int,
    overlap_seconds: int,
    min_chunk_seconds: int,
) -> list[tuple[float, float]]:
    """Return (start, end) tuples covering the audio.

    For chunk index i: start = max(0, i*chunk - overlap), end = min(duration, (i+1)*chunk).
    Trailing chunks shorter than min_chunk_seconds are dropped (unless it is the
    first chunk, or min_chunk_seconds <= 0 which disables the drop).
    """
    chunks: list[tuple[float, float]] = []
    if duration <= 0:
        return chunks
    i = 0
    while True:
        nominal_start = i * chunk_seconds
        if nominal_start >= duration:
            break
        start = max(0.0, nominal_start - overlap_seconds)
        end = min(duration, (i + 1) * chunk_seconds)
        if end <= start:
            break
        if i > 0 and min_chunk_seconds > 0 and (end - start) < min_chunk_seconds:
            break
        chunks.append((start, end))
        i += 1
    return chunks
