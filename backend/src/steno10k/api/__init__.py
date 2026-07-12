from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from steno10k.api.configsvc import ConfigService
from steno10k.api.envelope import install_error_handlers, ok
from steno10k.api.routers import (
    artifacts,
    config,
    projects,
    prompts,
    recordings,
    runs,
    sets,
    system,
)
from steno10k.api.runq import RunQueue
from steno10k.api.stages import build_registry
from steno10k.api.storage import Storage


class SPAStaticFiles(StaticFiles):
    """Serve built SPA assets, falling back to index.html for client-side routes.

    react-router uses HTML5 history routing, so a hard refresh on a deep link
    like /p/x/s/y hits the server for a path that has no file. Starlette's
    StaticFiles 404s on that; we instead return index.html so the SPA boots and
    resolves the route on the client.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api/"):
                return await super().get_response("index.html", scope)
            raise


def create_app(data_root: Path, static_dir: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.run_queue.start()
        try:
            yield
        finally:
            app.state.run_queue.stop()

    app = FastAPI(title="steno10k", lifespan=_lifespan)
    app.state.data_root = data_root
    app.state.storage = Storage(data_root)
    app.state.config_service = ConfigService(data_root / "config.yaml")
    app.state.run_queue = RunQueue(
        storage=app.state.storage,
        registry=build_registry(),
        config_service=app.state.config_service,
    )
    install_error_handlers(app)

    @app.get("/api/v1/health")
    def health() -> dict[str, object]:
        return ok({"status": "ok"})

    app.include_router(projects.router)
    app.include_router(sets.router)
    app.include_router(recordings.router)
    app.include_router(artifacts.router)
    app.include_router(config.router)
    app.include_router(prompts.router)
    app.include_router(runs.router)
    app.include_router(system.router)

    # Built SPA served at "/" in the container; absent during most unit tests.
    _static = static_dir if static_dir is not None else Path(__file__).parent.parent / "static"
    if _static.is_dir():
        app.mount("/", SPAStaticFiles(directory=_static, html=True), name="spa")

    return app


_default_data_root = Path(os.environ.get("STENO10K_DATA_ROOT", "./data"))
app = create_app(_default_data_root)
