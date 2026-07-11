from __future__ import annotations

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
