from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, UploadFile

from steno10k.api.deps import get_storage
from steno10k.api.dto import Envelope, RecordingDTO
from steno10k.api.envelope import ApiError, ok
from steno10k.api.storage import NotFound, Storage
from steno10k.contracts.domain import Recording
from steno10k.lib.ingest import SUPPORTED_EXTENSIONS, normalized_filename

router = APIRouter(prefix="/api/v1/projects/{project}/sets/{set_}/recordings", tags=["recordings"])

_MAX_FILE_BYTES = 1024**3  # 1 GB
_READ_CHUNK_BYTES = 1024 * 1024  # 1 MiB


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


@router.post("", response_model=Envelope[list[RecordingDTO]])
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
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ApiError(422, "unsupported_type", f"unsupported file type: {source_name!r}")

    existing = {p.name for p in set_dir.iterdir()} if set_dir.is_dir() else set()
    recordings: list[Recording] = []
    written: list[Path] = []
    for f in files:
        source_name = f.filename or "upload"
        normalized_name = normalized_filename(source_name, existing)
        existing.add(normalized_name)
        dest = set_dir / normalized_name
        try:
            await _write_capped(f, dest)
        except Exception:
            # Roll back: this request is all-or-nothing, so remove the
            # current partial file plus everything already written for
            # earlier entries in this same request before re-raising.
            dest.unlink(missing_ok=True)
            for path in written:
                path.unlink(missing_ok=True)
            raise
        written.append(dest)
        recordings.append(Recording(source_name=source_name, normalized_name=normalized_name))

    storage.add_recordings(project, set_, recordings)
    return ok([RecordingDTO.from_domain(r).model_dump() for r in recordings])


@router.get("", response_model=Envelope[list[RecordingDTO]])
def list_recordings(
    project: str, set_: str, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    try:
        recording_set = storage.get_set(project, set_)
    except NotFound as exc:
        raise ApiError(404, "set_not_found", f"set not found: {project}/{set_}") from exc
    return ok([RecordingDTO.from_domain(r).model_dump() for r in recording_set.recordings])


@router.delete("/{recording}", response_model=Envelope[None])
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
