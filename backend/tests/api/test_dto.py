from __future__ import annotations

from steno10k.api.dto import ProjectDTO, RecordingDTO, SetDTO
from steno10k.contracts.domain import Project, Recording, RecordingSet
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


def test_set_dto_from_domain() -> None:
    s = RecordingSet(slug="week-1", title="Week 1", project_slug="law")
    s.recordings.append(
        Recording(source_name="a.m4a", normalized_name="a.m4a", duration_seconds=12.0)
    )
    s.stages[StageName.NORMALIZE] = StageStatus.OK
    dto = SetDTO.from_domain(s)
    assert isinstance(dto.recordings[0], RecordingDTO)
    assert dto.slug == "week-1"
    assert dto.recordings[0].duration_seconds == 12.0
    assert dto.stages["normalize"] == "ok"


def test_project_dto_from_domain() -> None:
    p = Project(slug="law", title="Law")
    p.sets.append(RecordingSet(slug="week-1", title="Week 1", project_slug="law"))
    dto = ProjectDTO.from_domain(p)
    assert dto.slug == "law" and dto.sets[0].slug == "week-1"
