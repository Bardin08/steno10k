from __future__ import annotations

import json
from pathlib import Path

import pytest

from steno10k.cli.app import main


def test_status_reports_recordings_and_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = ["--data-root", str(tmp_path)]
    main(["projects", "create", "Bio", *root])
    main(["sets", "create", "bio", "L1", *root])
    src = tmp_path / "a.mp3"
    src.write_bytes(b"x")
    main(["import", "bio", "l1", str(src), *root])
    # a stray on-disk artifact next to the recording
    (tmp_path / "bio" / "l1" / "summary.md").write_text("done")
    capsys.readouterr()

    assert main(["status", "bio", "l1", "--json", *root]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["slug"] == "l1"
    assert "a.mp3" in [r["normalized_name"] for r in payload["recordings"]]
    assert "summary.md" in payload["artifacts"]
    assert "a.mp3" not in payload["artifacts"]
    assert "manifest.json" not in payload["artifacts"]


def test_status_unknown_set_exits_2(tmp_path: Path) -> None:
    assert main(["status", "nope", "nope", "--data-root", str(tmp_path)]) == 2
