from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from steno10k.api.runq import Run
from steno10k.contracts.domain import Project, Recording, RecordingSet


class RecordingDTO(BaseModel):
    source_name: str
    normalized_name: str
    duration_seconds: float | None
    chunks: list[str]

    @classmethod
    def from_domain(cls, r: Recording) -> RecordingDTO:
        return cls(
            source_name=r.source_name,
            normalized_name=r.normalized_name,
            duration_seconds=r.duration_seconds,
            chunks=list(r.chunks),
        )


class SetDTO(BaseModel):
    id: str
    slug: str
    title: str
    project_slug: str
    recordings: list[RecordingDTO]
    stages: dict[str, str]

    @classmethod
    def from_domain(cls, s: RecordingSet) -> SetDTO:
        return cls(
            id=s.id,
            slug=s.slug,
            title=s.title,
            project_slug=s.project_slug,
            recordings=[RecordingDTO.from_domain(r) for r in s.recordings],
            stages={str(k): str(v) for k, v in s.stages.items()},
        )


class ProjectDTO(BaseModel):
    id: str
    slug: str
    title: str
    sets: list[SetDTO]

    @classmethod
    def from_domain(cls, p: Project) -> ProjectDTO:
        return cls(
            id=p.id, slug=p.slug, title=p.title, sets=[SetDTO.from_domain(s) for s in p.sets]
        )


class CreateTitle(BaseModel):
    title: str


class RunDTO(BaseModel):
    id: str
    project: str
    set_: str
    status: str
    position: int
    stats: dict[str, Any]

    @classmethod
    def from_domain(cls, r: Run) -> RunDTO:
        return cls(
            id=r.id,
            project=r.project,
            set_=r.set_,
            status=str(r.status),
            position=r.position,
            stats=dict(r.stats),
        )
