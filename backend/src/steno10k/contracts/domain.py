from __future__ import annotations

from dataclasses import dataclass, field

from steno10k.contracts.ids import new_id
from steno10k.contracts.status import StageStatus


@dataclass
class Recording:
    source_name: str
    normalized_name: str
    duration_seconds: float | None = None
    chunks: list[str] = field(default_factory=list)


@dataclass
class RecordingSet:
    slug: str
    title: str
    project_slug: str
    id: str = field(default_factory=new_id)  # GUID
    recordings: list[Recording] = field(default_factory=list)
    stages: dict[str, StageStatus] = field(default_factory=dict)


@dataclass
class Project:
    slug: str
    title: str
    id: str = field(default_factory=new_id)  # GUID
    sets: list[RecordingSet] = field(default_factory=list)
    icon: str | None = None
