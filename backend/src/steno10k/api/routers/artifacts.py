from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from steno10k.api.deps import get_storage
from steno10k.api.dto import Envelope
from steno10k.api.envelope import ApiError, ok
from steno10k.api.storage import Storage

router = APIRouter(prefix="/api/v1/projects/{project}/sets/{set_}/artifacts", tags=["artifacts"])

# Never surfaced as artifacts: bookkeeping files, not pipeline outputs.
_HIDDEN_NAMES = {"manifest.json", "errors.log"}

_TEXT_EXTENSIONS = {".md", ".txt", ".json", ".log", ".csv"}


class ArtifactDTO(BaseModel):
    name: str
    kind: str
    size: int
    stage: str | None = None


def _kind_for(path: Path) -> str:
    if path.suffix.lower() in _TEXT_EXTENSIONS:
        return "text"
    if path.suffix.lower() == ".docx":
        return "docx"
    return "binary"


def _stage_for(name: str) -> str | None:
    """Best-effort producing-stage guess from the artifact's filename.

    Concrete pipeline stages aren't part of F2 (stub StageRegistry, Task 9), so
    this is a lightweight heuristic rather than a real stage->output mapping.
    """
    lowered = name.lower()
    if "bundle" in lowered or lowered.endswith(".docx"):
        return "bundle"
    if "merged" in lowered or "transcript" in lowered:
        return "merge"
    if "summary" in lowered:
        return "summarize"
    return None


def _resolve_under_set_dir(set_dir: Path, requested: str) -> Path:
    """Resolve `requested` under `set_dir`, raising ApiError(404) on traversal."""
    set_dir_resolved = set_dir.resolve()
    candidate = (set_dir / requested).resolve()
    if candidate != set_dir_resolved and set_dir_resolved not in candidate.parents:
        raise ApiError(404, "artifact_not_found", f"artifact not found: {requested}")
    if not candidate.is_file():
        raise ApiError(404, "artifact_not_found", f"artifact not found: {requested}")
    return candidate


def _get_set_dir(storage: Storage, project: str, set_: str) -> Path:
    set_dir = storage.set_dir(project, set_)
    if not set_dir.is_dir():
        raise ApiError(404, "set_not_found", f"set not found: {project}/{set_}")
    return set_dir


@router.get("", response_model=Envelope[list[ArtifactDTO]])
def list_artifacts(
    project: str, set_: str, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    set_dir = _get_set_dir(storage, project, set_)
    artifacts = []
    for path in sorted(set_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in _HIDDEN_NAMES:
            continue
        rel_name = path.relative_to(set_dir).as_posix()
        artifacts.append(
            ArtifactDTO(
                name=rel_name,
                kind=_kind_for(path),
                size=path.stat().st_size,
                stage=_stage_for(rel_name),
            ).model_dump()
        )
    return ok(artifacts)


@router.get("/{path:path}/preview")
def preview_artifact(
    project: str,
    set_: str,
    path: str,
    storage: Annotated[Storage, Depends(get_storage)],
) -> PlainTextResponse:
    set_dir = _get_set_dir(storage, project, set_)
    file_path = _resolve_under_set_dir(set_dir, path)
    return PlainTextResponse(file_path.read_text(encoding="utf-8"))


@router.get("/{path:path}/download")
def download_artifact(
    project: str,
    set_: str,
    path: str,
    storage: Annotated[Storage, Depends(get_storage)],
) -> FileResponse:
    set_dir = _get_set_dir(storage, project, set_)
    file_path = _resolve_under_set_dir(set_dir, path)
    return FileResponse(file_path, filename=file_path.name)
