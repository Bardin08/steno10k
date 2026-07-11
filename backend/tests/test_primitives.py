from __future__ import annotations

from steno10k.contracts.ids import new_id
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


def test_stage_status_values() -> None:
    expected: str = "ok"
    assert StageStatus.OK == expected


def test_stage_names_ordered() -> None:
    assert list(StageName) == [
        StageName.NORMALIZE,
        StageName.CHUNK,
        StageName.TRANSCRIBE,
        StageName.CLEAN,
        StageName.MERGE,
        StageName.SUMMARIZE,
        StageName.BUNDLE,
        StageName.NOTIFY,
    ]
    expected: str = "summarize"
    assert StageName.SUMMARIZE == expected


def test_new_id_is_a_unique_guid() -> None:
    a, b = new_id(), new_id()
    assert len(a) == 36 and a.count("-") == 4
    assert a != b
