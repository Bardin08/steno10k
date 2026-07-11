from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from steno10k.contracts.domain import Recording
from steno10k.contracts.ids import new_id
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


class Manifest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=new_id)  # GUID
    project_slug: str
    set_slug: str
    title: str
    source_files: list[str] = Field(default_factory=list)
    recordings: list[Recording] = Field(default_factory=list)
    stages: dict[StageName, StageStatus] = Field(default_factory=dict)
    generated_files: list[str] = Field(default_factory=list)
    errors: int = 0
    created: str | None = None
    updated: str | None = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Manifest:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))
