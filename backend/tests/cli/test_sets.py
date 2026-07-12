from __future__ import annotations

import json
from pathlib import Path

import pytest

from steno10k.cli.app import main


def test_sets_create_list_delete(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = ["--data-root", str(tmp_path)]
    assert main(["projects", "create", "Bio", *root]) == 0
    capsys.readouterr()

    assert main(["sets", "create", "bio", "Lecture 1", *root]) == 0
    assert "lecture-1" in capsys.readouterr().out

    assert main(["sets", "list", "bio", "--json", *root]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [s["slug"] for s in payload] == ["lecture-1"]

    assert main(["sets", "delete", "bio", "lecture-1", "-y", *root]) == 0
    assert main(["sets", "list", "bio", "--json", *root]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_sets_create_unknown_project_exits_2(tmp_path: Path) -> None:
    assert main(["sets", "create", "nope", "X", "--data-root", str(tmp_path)]) == 2
