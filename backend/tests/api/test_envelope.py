from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from steno10k.api.envelope import ApiError, install_error_handlers, ok


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/thing")
    def thing() -> dict[str, object]:
        return ok({"hello": "world"})

    @app.get("/missing")
    def missing() -> dict[str, object]:
        raise ApiError(status_code=404, code="set_not_found", message="no set")

    return app


def test_success_is_enveloped() -> None:
    r = TestClient(_app()).get("/thing")
    assert r.status_code == 200
    assert r.json() == {"data": {"hello": "world"}, "error": None}


def test_api_error_is_enveloped() -> None:
    r = TestClient(_app()).get("/missing")
    assert r.status_code == 404
    body = r.json()
    assert body["data"] is None
    assert body["error"]["code"] == "set_not_found"


def test_validation_error_is_enveloped() -> None:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/typed")
    def typed(n: int) -> dict[str, object]:
        return ok({"n": n})

    r = TestClient(app).get("/typed?n=abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
