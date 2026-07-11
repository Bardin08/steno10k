from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from steno10k.api.envelope import install_error_handlers, ok

app = FastAPI(title="steno10k")
install_error_handlers(app)


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return ok({"status": "ok"})


# Routers are mounted here in later tasks (projects, sets, ...).

# Built SPA served at "/" in the container; absent during local tests.
_static = Path(__file__).parent.parent / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="spa")
