from __future__ import annotations

from pathlib import Path

from steno10k.contracts.slug import resolve_collision, slugify

# Audio/video containers the pipeline's ffmpeg-based chunker can read. Extend as needed.
SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".ogg",
    ".aac",
    ".wma",
    ".mp4",
    ".mov",
    ".webm",
}


def normalized_filename(source_name: str, existing: set[str]) -> str:
    """Slugify the stem (F1 slug rules) and dedupe against files already in the set dir."""
    stem = Path(source_name).stem
    suffix = Path(source_name).suffix.lower()
    base_slug = slugify(stem)
    # resolve_collision works on bare names (no extension); dedupe with the extension
    # re-attached so "a.m4a" + "a.m4a" -> "a_2.m4a", not "a.m4a_2".
    existing_stems = {Path(name).stem for name in existing if Path(name).suffix.lower() == suffix}
    slug = resolve_collision(existing_stems, base_slug)
    return f"{slug}{suffix}"
