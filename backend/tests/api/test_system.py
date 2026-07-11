from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from steno10k.api import create_app


def test_system_info(tmp_path: Path) -> None:
    c = TestClient(create_app(data_root=tmp_path))
    data = c.get("/api/v1/system").json()["data"]
    assert "small" in data["whisper_models"]
    assert data["current_model"] == "small"
    assert data["data_root"].endswith(str(tmp_path).split("/")[-1])
