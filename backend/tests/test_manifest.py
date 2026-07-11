from __future__ import annotations

import uuid
from pathlib import Path

from steno10k.contracts.domain import Recording
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


def test_manifest_round_trip(tmp_path: Path) -> None:
    m = Manifest(project_slug="law", set_slug="week-1", title="Week 1")
    uuid.UUID(m.id)  # id is a GUID
    m.recordings.append(Recording(source_name="a.m4a", normalized_name="a.m4a"))
    m.stages[StageName.NORMALIZE] = StageStatus.OK
    path = tmp_path / "manifest.json"
    m.save(path)

    loaded = Manifest.load(path)
    assert loaded.id == m.id
    assert loaded.recordings[0].source_name == "a.m4a"
    assert loaded.stages[StageName.NORMALIZE] is StageStatus.OK
