from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from steno10k.api import create_app


def _client(tmp_path: Path) -> TestClient:
    c = TestClient(create_app(data_root=tmp_path))
    c.post("/api/v1/projects", json={"title": "Law"})
    c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
    return c


def test_artifact_list_skips_manifest_and_errors_log(tmp_path: Path) -> None:
    c = _client(tmp_path)
    set_dir = tmp_path / "law" / "week-1"
    (set_dir / "summary.md").write_text("# Notes", encoding="utf-8")
    (set_dir / "errors.log").write_text("boom", encoding="utf-8")

    r = c.get("/api/v1/projects/law/sets/week-1/artifacts")
    assert r.status_code == 200
    names = {a["name"] for a in r.json()["data"]}
    assert "summary.md" in names
    assert "errors.log" not in names
    assert "manifest.json" not in names

    entry = next(a for a in r.json()["data"] if a["name"] == "summary.md")
    assert entry["size"] == len(b"# Notes")
    assert entry["kind"] == "text"


def test_artifact_preview_and_traversal_guard(tmp_path: Path) -> None:
    c = _client(tmp_path)
    set_dir = tmp_path / "law" / "week-1"
    (set_dir / "summary.md").write_text("# Notes", encoding="utf-8")

    r = c.get("/api/v1/projects/law/sets/week-1/artifacts/summary.md/preview")
    assert r.status_code == 200 and "# Notes" in r.text
    # not enveloped: raw text response, no "data"/"error" wrapper
    assert r.headers["content-type"].startswith("text/plain")

    r = c.get("/api/v1/projects/law/sets/week-1/artifacts/..%2f..%2fconfig.yaml/preview")
    assert r.status_code == 404  # traversal blocked


def test_artifact_download(tmp_path: Path) -> None:
    c = _client(tmp_path)
    set_dir = tmp_path / "law" / "week-1"
    (set_dir / "summary.md").write_text("# Notes", encoding="utf-8")

    r = c.get("/api/v1/projects/law/sets/week-1/artifacts/summary.md/download")
    assert r.status_code == 200
    assert r.content == b"# Notes"
    assert "attachment" in r.headers["content-disposition"]


def test_artifact_download_traversal_guard(tmp_path: Path) -> None:
    c = _client(tmp_path)
    # a real secret file that exists one level above the set dir
    (tmp_path / "law" / "secret.txt").write_text("nope", encoding="utf-8")

    r = c.get("/api/v1/projects/law/sets/week-1/artifacts/..%2fsecret.txt/download")
    assert r.status_code == 404


def test_artifact_missing_returns_404(tmp_path: Path) -> None:
    c = _client(tmp_path)
    r = c.get("/api/v1/projects/law/sets/week-1/artifacts/nope.md/preview")
    assert r.status_code == 404
