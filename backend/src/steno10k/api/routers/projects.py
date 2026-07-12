from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from steno10k.api.deps import get_storage
from steno10k.api.dto import CreateProject, ProjectDTO
from steno10k.api.envelope import ApiError, ok
from steno10k.api.storage import NotFound, Storage

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("")
def create_project(
    body: CreateProject, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    project = storage.create_project(body.title, icon=body.icon)
    return ok(ProjectDTO.from_domain(project).model_dump())


@router.get("")
def list_projects(storage: Annotated[Storage, Depends(get_storage)]) -> dict[str, Any]:
    projects = storage.list_projects()
    return ok([ProjectDTO.from_domain(p).model_dump() for p in projects])


@router.get("/{project}")
def get_project(project: str, storage: Annotated[Storage, Depends(get_storage)]) -> dict[str, Any]:
    try:
        found = storage.get_project(project)
    except NotFound as exc:
        raise ApiError(404, "project_not_found", f"project not found: {project}") from exc
    return ok(ProjectDTO.from_domain(found).model_dump())


@router.delete("/{project}")
def delete_project(
    project: str, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    try:
        storage.delete_project(project)
    except NotFound as exc:
        raise ApiError(404, "project_not_found", f"project not found: {project}") from exc
    return ok(None)
