from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from steno10k.api import create_app


def test_system_info(tmp_path: Path) -> None:
    c = TestClient(create_app(data_root=tmp_path))
    data = c.get("/api/v1/system").json()["data"]
    assert "small" in data["whisper_models"]
    assert data["current_model"] == "small"
    assert data["data_root"].endswith(str(tmp_path).split("/")[-1])


def test_system_reports_llm_key_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    c = TestClient(create_app(data_root=tmp_path))
    assert c.get("/api/v1/system").json()["data"]["llm_key_present"] is True


def test_system_reports_llm_key_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    c = TestClient(create_app(data_root=tmp_path))
    assert c.get("/api/v1/system").json()["data"]["llm_key_present"] is False
