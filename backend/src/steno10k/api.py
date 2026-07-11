from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="steno10k")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# In the built container the frontend is copied here and served at "/".
# Absent during local backend tests, so the mount is conditional.
_static = Path(__file__).parent / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="spa")
