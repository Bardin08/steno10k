from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from steno10k.api import create_app


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(data_root=tmp_path))


def test_project_and_set_lifecycle(tmp_path: Path) -> None:
    c = _client(tmp_path)
    r = c.post("/api/v1/projects", json={"title": "Law"})
    assert r.status_code == 200 and r.json()["data"]["slug"] == "law"

    r = c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
    assert r.json()["data"]["slug"] == "week-1"

    r = c.get("/api/v1/projects/law")
    assert r.json()["data"]["sets"][0]["slug"] == "week-1"

    r = c.get("/api/v1/projects/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "project_not_found"


def test_create_project_persists_icon(tmp_path: Path) -> None:
    c = _client(tmp_path)
    body = c.post("/api/v1/projects", json={"title": "Law", "icon": "scales"}).json()["data"]
    assert body["icon"] == "scales"
    listed = c.get("/api/v1/projects").json()["data"]
    assert any(p["slug"] == body["slug"] and p["icon"] == "scales" for p in listed)


def test_legacy_project_json_without_icon_loads_as_none(tmp_path: Path) -> None:
    # Seed a pre-icon project.json on disk (no "icon" key) at <data_root>/<slug>/project.json.
    project_dir = tmp_path / "law"
    project_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        json.dumps({"id": "legacy-id", "slug": "law", "title": "Law"}), encoding="utf-8"
    )
    data = _client(tmp_path).get("/api/v1/projects/law").json()["data"]
    assert data["icon"] is None
