from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, UploadFile

from steno10k.api.deps import get_storage
from steno10k.api.dto import RecordingDTO
from steno10k.api.envelope import ApiError, ok
from steno10k.api.storage import NotFound, Storage
from steno10k.contracts.domain import Recording
from steno10k.contracts.slug import resolve_collision, slugify

router = APIRouter(prefix="/api/v1/projects/{project}/sets/{set_}/recordings", tags=["recordings"])

# Audio containers the pipeline's ffmpeg-based chunker can read. Extend as needed.
_SUPPORTED_EXTENSIONS = {
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

_MAX_FILE_BYTES = 1024**3  # 1 GB
_READ_CHUNK_BYTES = 1024 * 1024  # 1 MiB


def _normalized_filename(source_name: str, existing: set[str]) -> str:
    """Slugify the stem (F1 slug rules) and dedupe against files already in the set dir."""
    stem = Path(source_name).stem
    suffix = Path(source_name).suffix.lower()
    base_slug = slugify(stem)
    # resolve_collision works on bare names (no extension); dedupe with the
    # extension re-attached so "a.m4a" + "a.m4a" -> "a_2.m4a", not "a.m4a_2".
    existing_stems = {Path(name).stem for name in existing if Path(name).suffix.lower() == suffix}
    slug = resolve_collision(existing_stems, base_slug)
    return f"{slug}{suffix}"


async def _write_capped(upload: UploadFile, dest: Path) -> int:
    """Stream `upload` to `dest` in chunks, aborting once the 1 GB cap is exceeded.

    Never buffers the whole file in memory; partial output is removed on overflow.
    """
    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(_READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_FILE_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise ApiError(
                    413,
                    "file_too_large",
                    "files over 1 GB aren't supported yet — open a GitHub issue if you need this",
                )
            out.write(chunk)
    return total


@router.post("")
async def upload_recordings(
    project: str,
    set_: str,
    files: list[UploadFile],
    storage: Annotated[Storage, Depends(get_storage)],
) -> dict[str, Any]:
    set_dir = storage.set_dir(project, set_)
    if not set_dir.is_dir():
        raise ApiError(404, "set_not_found", f"set not found: {project}/{set_}")

    for f in files:
        source_name = f.filename or ""
        suffix = Path(source_name).suffix.lower()
        if suffix not in _SUPPORTED_EXTENSIONS:
            raise ApiError(422, "unsupported_type", f"unsupported file type: {source_name!r}")

    existing = {p.name for p in set_dir.iterdir()} if set_dir.is_dir() else set()
    recordings: list[Recording] = []
    for f in files:
        source_name = f.filename or "upload"
        normalized_name = _normalized_filename(source_name, existing)
        existing.add(normalized_name)
        await _write_capped(f, set_dir / normalized_name)
        recordings.append(Recording(source_name=source_name, normalized_name=normalized_name))

    storage.add_recordings(project, set_, recordings)
    return ok([RecordingDTO.from_domain(r).model_dump() for r in recordings])


@router.get("")
def list_recordings(
    project: str, set_: str, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    try:
        recording_set = storage.get_set(project, set_)
    except NotFound as exc:
        raise ApiError(404, "set_not_found", f"set not found: {project}/{set_}") from exc
    return ok([RecordingDTO.from_domain(r).model_dump() for r in recording_set.recordings])


@router.delete("/{recording}")
def delete_recording(
    project: str,
    set_: str,
    recording: str,
    storage: Annotated[Storage, Depends(get_storage)],
) -> dict[str, Any]:
    try:
        storage.remove_recording(project, set_, recording)
    except NotFound as exc:
        raise ApiError(
            404, "recording_not_found", f"recording not found: {project}/{set_}/{recording}"
        ) from exc
    return ok(None)
