from __future__ import annotations

import json
from pathlib import Path

import pytest

from steno10k.cli.app import main


def _run(argv: list[str]) -> int:
    return main(argv)


def test_projects_create_list_delete_roundtrip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = ["--data-root", str(tmp_path)]

    assert _run(["projects", "create", "Con Law", *root]) == 0
    out = capsys.readouterr().out
    assert "con-law" in out

    assert _run(["projects", "list", "--json", *root]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [p["slug"] for p in payload] == ["con-law"]
    assert payload[0]["title"] == "Con Law"

    assert _run(["projects", "delete", "con-law", "-y", *root]) == 0
    assert _run(["projects", "list", "--json", *root]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_projects_create_rejects_emoji_icon(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        _run(["projects", "create", "X", "--icon", "😀", "--data-root", str(tmp_path)])
    assert exc.value.code == 2


def test_projects_create_accepts_phosphor_icon(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        _run(["projects", "create", "Bio", "--icon", "wave-sine", "--data-root", str(tmp_path)])
        == 0
    )
    capsys.readouterr()
    assert _run(["projects", "list", "--json", "--data-root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["icon"] == "wave-sine"
