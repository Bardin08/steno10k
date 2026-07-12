from __future__ import annotations

import json
from pathlib import Path

import pytest

from steno10k.cli.app import main


def _seed_set(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> list[str]:
    root = ["--data-root", str(tmp_path)]
    main(["projects", "create", "Bio", *root])
    main(["sets", "create", "bio", "L1", *root])
    capsys.readouterr()
    return root


def test_import_copies_and_registers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _seed_set(tmp_path, capsys)
    src = tmp_path / "Lecture 1.m4a"
    src.write_bytes(b"audio")

    assert main(["import", "bio", "l1", str(src), "--json", *root]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["normalized_name"] == "lecture-1.m4a"
    assert payload[0]["source_name"] == "Lecture 1.m4a"
    # file copied into the set dir under the normalized name
    assert (tmp_path / "bio" / "l1" / "lecture-1.m4a").read_bytes() == b"audio"


def test_import_rejects_unsupported_extension(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _seed_set(tmp_path, capsys)
    bad = tmp_path / "notes.txt"
    bad.write_text("nope")
    assert main(["import", "bio", "l1", str(bad), *root]) == 2


def test_import_unknown_set_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _seed_set(tmp_path, capsys)
    src = tmp_path / "a.mp3"
    src.write_bytes(b"x")
    assert main(["import", "bio", "nope", str(src), *root]) == 2
