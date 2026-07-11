from __future__ import annotations

import uuid

from steno10k.contracts.domain import Project, Recording, RecordingSet
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


def test_recording_defaults() -> None:
    r = Recording(source_name="a.m4a", normalized_name="a.m4a")
    assert r.duration_seconds is None and r.chunks == []


def test_set_gets_a_guid_id_and_holds_recordings() -> None:
    s = RecordingSet(slug="week-1", title="Week 1", project_slug="law")
    uuid.UUID(s.id)  # raises if not a valid GUID
    s.recordings.append(Recording(source_name="a.m4a", normalized_name="a.m4a"))
    s.stages[StageName.NORMALIZE] = StageStatus.OK
    assert len(s.recordings) == 1


def test_project_gets_guid_and_holds_sets() -> None:
    p = Project(slug="law", title="Law")
    uuid.UUID(p.id)
    p.sets.append(RecordingSet(slug="week-1", title="Week 1", project_slug="law"))
    assert p.sets[0].project_slug == "law"
