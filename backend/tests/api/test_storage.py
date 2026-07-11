from __future__ import annotations

from pathlib import Path

import pytest

from steno10k.api.storage import NotFound, Storage
from steno10k.contracts.domain import Recording


def test_project_crud_and_slug_collision(tmp_path: Path) -> None:
    s = Storage(tmp_path)
    a = s.create_project("Constitutional Law")
    assert a.slug == "constitutional-law"
    b = s.create_project("Constitutional Law")  # same title -> collision
    assert b.slug == "constitutional-law_2"
    assert {p.slug for p in s.list_projects()} == {"constitutional-law", "constitutional-law_2"}
    s.delete_project("constitutional-law_2")
    assert {p.slug for p in s.list_projects()} == {"constitutional-law"}


def test_set_crud_and_recordings(tmp_path: Path) -> None:
    s = Storage(tmp_path)
    s.create_project("Law")
    st = s.create_set("law", "Week 1")
    assert st.slug == "week-1"
    s.add_recordings("law", "week-1", [Recording(source_name="a.m4a", normalized_name="a.m4a")])
    got = s.get_set("law", "week-1")
    assert got.recordings[0].source_name == "a.m4a"


def test_missing_raises_notfound(tmp_path: Path) -> None:
    with pytest.raises(NotFound):
        Storage(tmp_path).get_set("nope", "nope")
