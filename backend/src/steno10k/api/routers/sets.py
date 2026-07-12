from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from steno10k.api.deps import get_storage
from steno10k.api.dto import CreateTitle, Envelope, SetDTO
from steno10k.api.envelope import ApiError, ok
from steno10k.api.storage import NotFound, Storage

router = APIRouter(prefix="/api/v1/projects/{project}/sets", tags=["sets"])


@router.post("", response_model=Envelope[SetDTO])
def create_set(
    project: str, body: CreateTitle, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    try:
        recording_set = storage.create_set(project, body.title)
    except NotFound as exc:
        raise ApiError(404, "project_not_found", f"project not found: {project}") from exc
    return ok(SetDTO.from_domain(recording_set).model_dump())


@router.get("", response_model=Envelope[list[SetDTO]])
def list_sets(project: str, storage: Annotated[Storage, Depends(get_storage)]) -> dict[str, Any]:
    sets = storage.list_sets(project)
    return ok([SetDTO.from_domain(s).model_dump() for s in sets])


@router.get("/{set_}", response_model=Envelope[SetDTO])
def get_set(
    project: str, set_: str, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    try:
        recording_set = storage.get_set(project, set_)
    except NotFound as exc:
        raise ApiError(404, "set_not_found", f"set not found: {project}/{set_}") from exc
    return ok(SetDTO.from_domain(recording_set).model_dump())


@router.delete("/{set_}", response_model=Envelope[None])
def delete_set(
    project: str, set_: str, storage: Annotated[Storage, Depends(get_storage)]
) -> dict[str, Any]:
    try:
        storage.delete_set(project, set_)
    except NotFound as exc:
        raise ApiError(404, "set_not_found", f"set not found: {project}/{set_}") from exc
    return ok(None)
