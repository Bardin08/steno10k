from __future__ import annotations

from fastapi.testclient import TestClient

from steno10k.api import app


def test_health_ok() -> None:
    resp = TestClient(app).get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"data": {"status": "ok"}, "error": None}
