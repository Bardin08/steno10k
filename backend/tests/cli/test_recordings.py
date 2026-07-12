from __future__ import annotations

import json
from pathlib import Path

import pytest

from steno10k.cli.app import main


def _seed_with_recording(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> list[str]:
    root = ["--data-root", str(tmp_path)]
    main(["projects", "create", "Bio", *root])
    main(["sets", "create", "bio", "L1", *root])
    src = tmp_path / "a.mp3"
    src.write_bytes(b"x")
    main(["import", "bio", "l1", str(src), *root])
    capsys.readouterr()
    return root


def test_recordings_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _seed_with_recording(tmp_path, capsys)
    assert main(["recordings", "list", "bio", "l1", "--json", *root]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [r["normalized_name"] for r in payload] == ["a.mp3"]


def test_recordings_rm(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _seed_with_recording(tmp_path, capsys)
    assert main(["recordings", "rm", "bio", "l1", "a.mp3", "-y", *root]) == 0
    assert not (tmp_path / "bio" / "l1" / "a.mp3").exists()
    assert main(["recordings", "list", "bio", "l1", "--json", *root]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_recordings_rm_unknown_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _seed_with_recording(tmp_path, capsys)
    assert main(["recordings", "rm", "bio", "l1", "ghost.mp3", "-y", *root]) == 2
