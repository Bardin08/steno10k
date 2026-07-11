from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from steno10k.api.configsvc import ConfigService
from steno10k.api.envelope import install_error_handlers, ok
from steno10k.api.routers import artifacts, projects, recordings, sets
from steno10k.api.storage import Storage


def create_app(data_root: Path) -> FastAPI:
    app = FastAPI(title="steno10k")
    app.state.storage = Storage(data_root)
    app.state.config_service = ConfigService(data_root / "config.yaml")
    install_error_handlers(app)

    @app.get("/api/v1/health")
    def health() -> dict[str, object]:
        return ok({"status": "ok"})

    app.include_router(projects.router)
    app.include_router(sets.router)
    app.include_router(recordings.router)
    app.include_router(artifacts.router)

    # Built SPA served at "/" in the container; absent during local tests.
    _static = Path(__file__).parent.parent / "static"
    if _static.is_dir():
        app.mount("/", StaticFiles(directory=_static, html=True), name="spa")

    return app


_default_data_root = Path(os.environ.get("STENO10K_DATA_ROOT", "./data"))
app = create_app(_default_data_root)
