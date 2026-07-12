from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from steno10k.api import create_app


def _make_static(tmp_path: Path) -> Path:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>steno10k</title>", encoding="utf-8")
    (static / "asset.js").write_text("console.log('hi')", encoding="utf-8")
    return static


def test_root_serves_index(tmp_path: Path) -> None:
    static = _make_static(tmp_path)
    with TestClient(create_app(data_root=tmp_path / "data", static_dir=static)) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert "<!doctype html>" in r.text.lower()


def test_deep_link_serves_index(tmp_path: Path) -> None:
    static = _make_static(tmp_path)
    with TestClient(create_app(data_root=tmp_path / "data", static_dir=static)) as c:
        r = c.get("/p/smoke/s/set-1")
        assert r.status_code == 200
        assert "<!doctype html>" in r.text.lower()


def test_existing_asset_served(tmp_path: Path) -> None:
    static = _make_static(tmp_path)
    with TestClient(create_app(data_root=tmp_path / "data", static_dir=static)) as c:
        r = c.get("/asset.js")
        assert r.status_code == 200
        assert "console.log" in r.text


def test_unknown_api_path_is_json_404(tmp_path: Path) -> None:
    static = _make_static(tmp_path)
    with TestClient(create_app(data_root=tmp_path / "data", static_dir=static)) as c:
        r = c.get("/api/v1/does-not-exist")
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("application/json")
