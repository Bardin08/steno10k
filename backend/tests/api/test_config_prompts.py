from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from steno10k.api import create_app


def test_config_get_put_defaults(tmp_path: Path) -> None:
    c = TestClient(create_app(data_root=tmp_path))
    assert c.get("/api/v1/config").json()["data"]["transcription"]["model"] == "small"
    body = c.get("/api/v1/config").json()["data"]
    body["stages"]["enabled"]["merge"] = False
    r = c.put("/api/v1/config", json=body)
    assert r.status_code == 200
    # summarize depends on merge -> cascaded off in the response meta
    assert "summarize" in r.json()["data"]["cascaded_off"]
    defaults = c.get("/api/v1/config/defaults").json()["data"]
    assert defaults["output"]["summary_filename"] == "summary.md"


def test_config_put_persists(tmp_path: Path) -> None:
    c = TestClient(create_app(data_root=tmp_path))
    body = c.get("/api/v1/config").json()["data"]
    body["output"]["summary_filename"] = "notes.md"
    c.put("/api/v1/config", json=body)
    assert c.get("/api/v1/config").json()["data"]["output"]["summary_filename"] == "notes.md"


def test_prompts_get_put_reset(tmp_path: Path) -> None:
    c = TestClient(create_app(data_root=tmp_path))

    r = c.get("/api/v1/prompts")
    assert r.status_code == 200
    names = {p["name"] for p in r.json()["data"]}
    assert "clean" in names
    assert all(p["source"] == "default" for p in r.json()["data"])

    r = c.put("/api/v1/prompts/clean", json={"content": "custom clean prompt"})
    assert r.status_code == 200
    assert r.json()["data"]["source"] == "override"
    assert r.json()["data"]["content"] == "custom clean prompt"

    r = c.get("/api/v1/prompts")
    clean = next(p for p in r.json()["data"] if p["name"] == "clean")
    assert clean["source"] == "override"
    assert clean["content"] == "custom clean prompt"

    r = c.post("/api/v1/prompts/clean/reset")
    assert r.status_code == 200
    assert r.json()["data"]["source"] == "default"

    r = c.get("/api/v1/prompts")
    clean = next(p for p in r.json()["data"] if p["name"] == "clean")
    assert clean["source"] == "default"


def test_prompts_unknown_name_404(tmp_path: Path) -> None:
    c = TestClient(create_app(data_root=tmp_path))
    r = c.put("/api/v1/prompts/nope", json={"content": "x"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "prompt_not_found"
