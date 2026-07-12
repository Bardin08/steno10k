# M1·P Single-Container Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the M0 Docker skeleton genuinely run end-to-end, prove it with an ML-free e2e smoke gate, and make the memory/hosting story honest — closing the real gaps a first boot would expose.

**Architecture:** Backend serves the built SPA from FastAPI with a client-side-routing fallback; the whisper model caches to the mounted volume; a non-root container entrypoint seeds a container-safe config and drops privileges; a `scripts/smoke.sh` builds+boots the image and asserts boot/SPA/API in CI; a non-blocking memory preflight surfaces likely-OOM configs; hosting docs live on the MDX docs site; two deferred features are recorded for M2.

**Tech Stack:** FastAPI + Starlette `StaticFiles`, Docker (multi-stage, gosu), GitHub Actions, faster-whisper/HF cache env, Astro/MDX docs site, pytest.

**Spec:** `docs/specs/2026-07-12-steno10k-m1-p-single-container-packaging-design.md`

**Frozen-contract note:** This plan touches `backend/src/steno10k/api/__init__.py` (adds SPA-serving infra, `include_in_schema=False`, no DTO/OpenAPI-schema change) and `RunQueue.enqueue` (adds a free-form `stats["warnings"]` entry — no schema change). It does **not** edit `contracts/`, existing API DTOs, `tokens.css`, or `standards/`. The ADR in Task 9 takes the shared `adr.lock.md` lock.

---

## Task 0: Tracker setup

**Files:** none (GitHub + branch only)

- [ ] **Step 1: Create the issue**

Run:
```bash
gh issue create \
  --title "M1·P — Single-container packaging" \
  --body "Make the M0 Docker skeleton real: SPA fallback, model cache to volume, non-root hardening, e2e smoke CI gate, hosting docs (MDX), memory preflight, container-safe default. Spec: docs/specs/2026-07-12-steno10k-m1-p-single-container-packaging-design.md"
```
Expected: prints the new issue URL. Note the issue number as `$ISSUE`.

- [ ] **Step 2: Add the issue to project board #16**

Run:
```bash
gh project item-add 16 --owner "@me" --url <issue-url-from-step-1>
```
Expected: prints the added item id. (If the board is org-owned, use `--owner <org>`.)

- [ ] **Step 3: Ensure the issue-numbered branch**

We are already on `feat/m1-p-single-container-packaging`. Rename it to embed the issue number:
```bash
git branch -m "feat/${ISSUE}-single-container-packaging"
git branch --show-current
```
Expected: `feat/<ISSUE>-single-container-packaging`.

---

## Task 1: SPA deep-link fallback

react-router v7 uses `createBrowserRouter`; a hard refresh on `/p/x/s/y` currently 404s because `StaticFiles(html=True)` only serves `index.html` for existing paths. Add an `SPAStaticFiles` subclass that returns `index.html` (200) for unknown non-asset paths, and make the static dir injectable so it is testable. `/api` routes keep JSON 404s because they are registered before the `/` mount.

**Files:**
- Modify: `backend/src/steno10k/api/__init__.py`
- Test: `backend/tests/api/test_spa.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/api/test_spa.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_spa.py -v`
Expected: FAIL — `create_app()` has no `static_dir` parameter (`TypeError`).

- [ ] **Step 3: Implement the fallback**

Edit `backend/src/steno10k/api/__init__.py`. Replace the import line and the static-mount block, and add the `static_dir` parameter.

Change the top imports (add `Scope` typing + `Response`):
```python
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
```

Add this class just above `create_app`:
```python
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
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise
```

Change the `create_app` signature and the static block:
```python
def create_app(data_root: Path, static_dir: Path | None = None) -> FastAPI:
```
...and replace the existing static block near the end of `create_app` with:
```python
    # Built SPA served at "/" in the container; absent during most unit tests.
    _static = static_dir if static_dir is not None else Path(__file__).parent.parent / "static"
    if _static.is_dir():
        app.mount("/", SPAStaticFiles(directory=_static, html=True), name="spa")
```

Leave the `_default_data_root` / module-level `app = create_app(...)` lines unchanged (they call `create_app` positionally, so the new optional param is safe).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/api/test_spa.py -v`
Expected: all 4 PASS.

- [ ] **Step 5: Confirm the OpenAPI surface is unchanged**

Run: `cd backend && uv run python -c "import json; from steno10k.api import create_app; from pathlib import Path; print(len(json.dumps(create_app(Path('/tmp/x')).openapi())))"`
Expected: prints a number and does not error. The mount adds no schema paths (StaticFiles mounts are excluded from OpenAPI), so `openapi.json` is unaffected.

- [ ] **Step 6: Commit**

```bash
git add backend/src/steno10k/api/__init__.py backend/tests/api/test_spa.py
git commit -m "feat(api): SPA client-side-routing fallback for deep links"
```

---

## Task 2: Memory preflight module

A pure, unit-testable module: estimate RAM demand from the whisper model + worker count (table sourced from vision §9), read the container's cgroup memory limit, and return a warning string when demand likely exceeds the limit.

**Files:**
- Create: `backend/src/steno10k/api/preflight.py`
- Test: `backend/tests/api/test_preflight.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/api/test_preflight.py`:
```python
from __future__ import annotations

from pathlib import Path

from steno10k.api.preflight import (
    estimate_need_gb,
    memory_warning,
    read_cgroup_limit_bytes,
)
from steno10k.contracts.config import Config

GB = 1024**3


def test_estimate_need_known_model() -> None:
    # small = 2.0 GB/worker, +0.5 overhead
    assert estimate_need_gb("small", 2) == 2.0 * 2 + 0.5


def test_estimate_need_unknown_model_is_none() -> None:
    assert estimate_need_gb("nonexistent", 4) is None


def test_read_cgroup_v2(tmp_path: Path) -> None:
    v2 = tmp_path / "memory.max"
    v2.write_text("4294967296\n")  # 4 GB
    assert read_cgroup_limit_bytes(v2_path=v2, v1_path=tmp_path / "nope") == 4 * GB


def test_read_cgroup_unlimited_is_none(tmp_path: Path) -> None:
    v2 = tmp_path / "memory.max"
    v2.write_text("max\n")
    assert read_cgroup_limit_bytes(v2_path=v2, v1_path=tmp_path / "nope") is None


def test_read_cgroup_absent_is_none(tmp_path: Path) -> None:
    assert (
        read_cgroup_limit_bytes(v2_path=tmp_path / "a", v1_path=tmp_path / "b") is None
    )


def test_memory_warning_fires_when_over() -> None:
    cfg = Config()
    cfg.transcription.model = "large-v3"  # 5.0/worker
    cfg.transcription.max_workers = 4  # need ~20.5 GB
    msg = memory_warning(cfg, limit_bytes=8 * GB)
    assert msg is not None
    assert "large-v3" in msg


def test_memory_warning_silent_when_fits() -> None:
    cfg = Config()
    cfg.transcription.model = "small"
    cfg.transcription.max_workers = 2  # need 4.5 GB
    assert memory_warning(cfg, limit_bytes=8 * GB) is None


def test_memory_warning_silent_when_limit_unknown() -> None:
    cfg = Config()
    cfg.transcription.model = "large-v3"
    cfg.transcription.max_workers = 8
    assert memory_warning(cfg, limit_bytes=None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_preflight.py -v`
Expected: FAIL — `steno10k.api.preflight` does not exist (`ModuleNotFoundError`).

- [ ] **Step 3: Implement the module**

Create `backend/src/steno10k/api/preflight.py`:
```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config

_GB = 1024**3

# Per-worker int8/CPU RAM (GB), from the vision spec §9 hardware table. Each
# transcribe worker process loads its own WhisperModel copy, so total demand
# scales with max_workers. Conservative upper bounds so the warning errs toward
# firing early rather than missing a real OOM.
PER_WORKER_GB: dict[str, float] = {
    "tiny": 1.0,
    "base": 1.0,
    "small": 2.0,
    "medium": 4.0,
    "large-v3": 5.0,
}

# Base process + FastAPI + ffmpeg transient headroom.
_OVERHEAD_GB = 0.5

# Warn when estimated demand exceeds this fraction of the available limit.
_HEADROOM_FRACTION = 0.9

_CGROUP_V2 = Path("/sys/fs/cgroup/memory.max")
_CGROUP_V1 = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")

# Values at/above this are treated as "unlimited" (cgroup v1 reports a huge
# sentinel when no limit is set).
_UNLIMITED_THRESHOLD = 1 << 62


def estimate_need_gb(model: str, max_workers: int) -> float | None:
    """Estimated peak RAM (GB) for the given model x workers, or None if the
    model is not in the table (unknown model -> skip the check)."""
    per = PER_WORKER_GB.get(model)
    if per is None:
        return None
    return per * max(max_workers, 1) + _OVERHEAD_GB


def read_cgroup_limit_bytes(
    v2_path: Path = _CGROUP_V2, v1_path: Path = _CGROUP_V1
) -> int | None:
    """The container's memory limit in bytes, or None when unknown/unlimited.

    Best-effort: on Docker Desktop this reflects the VM, not a per-container
    --memory. A missing file or an unlimited sentinel returns None so the
    caller skips the warning rather than guessing.
    """
    for path in (v2_path, v1_path):
        try:
            raw = path.read_text().strip()
        except OSError:
            continue
        if raw == "max":
            return None
        try:
            value = int(raw)
        except ValueError:
            continue
        if value <= 0 or value >= _UNLIMITED_THRESHOLD:
            return None
        return value
    return None


def memory_warning(cfg: Config, limit_bytes: int | None = None) -> str | None:
    """A human-readable warning when the transcription config likely exceeds
    available RAM, else None. Advisory only — the run still proceeds."""
    if limit_bytes is None:
        limit_bytes = read_cgroup_limit_bytes()
    if limit_bytes is None:
        return None
    need = estimate_need_gb(cfg.transcription.model, cfg.transcription.max_workers)
    if need is None:
        return None
    have = limit_bytes / _GB
    if need <= _HEADROOM_FRACTION * have:
        return None
    return (
        f"transcription config may exceed available memory: "
        f"{cfg.transcription.model} x {cfg.transcription.max_workers} workers "
        f"needs ~{need:.1f} GB but only ~{have:.1f} GB is available; "
        f"lower transcription.max_workers or choose a smaller model to avoid an OOM kill"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/api/test_preflight.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/api/preflight.py backend/tests/api/test_preflight.py
git commit -m "feat(api): memory preflight estimator + cgroup limit reader"
```

---

## Task 3: Wire the preflight into run enqueue

At `enqueue()` compute the warning; if present, log it and record it on the run's free-form `stats` (already surfaced by `RunDTO.stats`, no schema change). The run still proceeds.

**Files:**
- Modify: `backend/src/steno10k/api/runq.py`
- Test: `backend/tests/api/test_runq_preflight.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/api/test_runq_preflight.py`:
```python
from __future__ import annotations

from pathlib import Path

import steno10k.api.runq as runq_mod
from steno10k.api.configsvc import ConfigService
from steno10k.api.runq import RunQueue
from steno10k.api.storage import Storage
from steno10k.contracts.registry import StageRegistry


def _queue(tmp_path: Path) -> RunQueue:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    return RunQueue(
        storage=storage,
        registry=StageRegistry([]),
        config_service=ConfigService(tmp_path / "config.yaml"),
    )


def test_enqueue_records_memory_warning(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runq_mod, "memory_warning", lambda cfg: "would OOM")
    run = _queue(tmp_path).enqueue(project="law", set_="week-1")
    assert run.stats.get("warnings") == ["would OOM"]


def test_enqueue_no_warning_leaves_stats_clean(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runq_mod, "memory_warning", lambda cfg: None)
    run = _queue(tmp_path).enqueue(project="law", set_="week-1")
    assert "warnings" not in run.stats
```

(`Storage(data_root)`, `create_project(title)`, and `create_set(project_slug, title)` are the real methods — verified in `backend/src/steno10k/api/storage.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_runq_preflight.py -v`
Expected: FAIL — `enqueue` does not populate `stats["warnings"]` (and `memory_warning` is not yet imported in `runq`).

- [ ] **Step 3: Implement the wiring**

Edit `backend/src/steno10k/api/runq.py`.

Add the import near the other `steno10k.api` imports at the top:
```python
from steno10k.api.preflight import memory_warning
```

In `enqueue`, after the `run = Run(...)` construction and before `bus = EventBus()`, insert:
```python
        warning = memory_warning(self._config_service.load())
        if warning is not None:
            log.warning("run %s: %s", run.id, warning)
            run.stats["warnings"] = [warning]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/api/test_runq_preflight.py tests/api/test_runs.py -v`
Expected: all PASS (existing run tests still green).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/api/runq.py backend/tests/api/test_runq_preflight.py
git commit -m "feat(runq): surface non-blocking memory preflight warning on enqueue"
```

---

## Task 4: Container-safe default config + first-boot seed

The frozen `contracts/config.py` default (`max_workers=4`) is left untouched. Instead lower the shipped `config.example.yaml` to 2 and have the container seed `config.yaml` from it on first boot (Task 5's entrypoint), so a fresh install runs at the safe default.

**Files:**
- Modify: `config.example.yaml`

- [ ] **Step 1: Lower the example default**

Edit `config.example.yaml`. In the `transcription:` block change:
```yaml
  max_workers: 4
```
to:
```yaml
  max_workers: 2 # each worker loads its own model copy; total RAM ~= per-worker x workers
```

- [ ] **Step 2: Verify it still parses as valid config**

Run: `cd backend && uv run python -c "import yaml; from steno10k.contracts.config import Config; Config.model_validate(yaml.safe_load(open('../config.example.yaml'))); print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add config.example.yaml
git commit -m "chore(config): default transcription.max_workers 4->2 for container-safe RAM"
```

---

## Task 5: Dockerfile hardening + entrypoint

Cache the whisper model to the volume (`HF_HOME`), run non-root via `gosu`, seed `config.yaml` on first boot, stream logs unbuffered, and add a healthcheck.

**Files:**
- Create: `entrypoint.sh`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Write the entrypoint**

Create `entrypoint.sh`:
```sh
#!/bin/sh
set -e

DATA_ROOT="${STENO10K_DATA_ROOT:-/data}"

# Cache the whisper model under the mounted volume so it downloads once and
# persists across restarts. Follows STENO10K_DATA_ROOT if the user overrides it.
export HF_HOME="${DATA_ROOT}/.cache/huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"

mkdir -p "${DATA_ROOT}" "${HF_HUB_CACHE}"

# Seed a container-safe config on first boot (never overwrite an existing one).
if [ ! -f "${DATA_ROOT}/config.yaml" ]; then
  cp /app/config.example.yaml "${DATA_ROOT}/config.yaml"
fi

# The volume is root-owned when Docker first creates it; hand it to the
# non-root runtime user, then drop privileges.
chown -R appuser:appuser "${DATA_ROOT}"

exec gosu appuser uvicorn steno10k.api:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: Update the Dockerfile**

Edit `Dockerfile`. In the runtime stage, replace the apt install line to add `gosu` and create the user, add env + config + entrypoint, and swap `CMD` for `ENTRYPOINT`.

Replace:
```dockerfile
FROM python:3.12-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --no-dev

# Built SPA served by FastAPI at "/"
COPY --from=frontend /frontend/dist ./src/steno10k/static

EXPOSE 8000
CMD ["uvicorn", "steno10k.api:app", "--host", "0.0.0.0", "--port", "8000"]
```
with:
```dockerfile
FROM python:3.12-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg gosu \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 10001 -m -d /home/appuser appuser
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    STENO10K_DATA_ROOT=/data

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --no-dev

# Default config seeded into /data on first boot by entrypoint.sh
COPY config.example.yaml ./config.example.yaml
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Built SPA served by FastAPI at "/"
COPY --from=frontend /frontend/dist ./src/steno10k/static

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').status==200 else 1)"
ENTRYPOINT ["/app/entrypoint.sh"]
```

- [ ] **Step 3: Update compose (data root + volume already present)**

Edit `docker-compose.yml` — no structural change needed (the named `steno10k-data` volume already mounts at `/data` and `STENO10K_DATA_ROOT: /data` is set). Add a clarifying comment above the `volumes:` mount:
```yaml
    volumes:
      # holds recordings, artifacts, config.yaml, AND the whisper model cache
      - steno10k-data:/data
```

- [ ] **Step 4: Build the image**

Run: `docker build -t steno10k:dev .`
Expected: build completes; final stage installs `gosu` and creates `appuser` without error.

- [ ] **Step 5: Boot and verify non-root + seeded config + health**

Run:
```bash
docker rm -f steno10k-verify 2>/dev/null || true
docker run -d --name steno10k-verify -p 8000:8000 steno10k:dev
sleep 8
docker exec steno10k-verify sh -c 'id -un && ls -1 /data/config.yaml && grep max_workers /data/config.yaml'
curl -fsS http://localhost:8000/api/v1/health
docker rm -f steno10k-verify
```
Expected: prints `appuser`, `/data/config.yaml`, `max_workers: 2`, and `{"data":{"status":"ok"},"error":null}`.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile entrypoint.sh docker-compose.yml
git commit -m "feat(docker): non-root entrypoint, HF model cache on volume, config seed, healthcheck"
```

---

## Task 6: e2e smoke script

Build the image, boot it against a throwaway volume, and assert boot + SPA (root + deep link) + an API round-trip (project -> set -> upload -> list). No whisper/LLM. Always tears down.

**Files:**
- Create: `scripts/smoke.sh`

- [ ] **Step 1: Write the script**

Create `scripts/smoke.sh`:
```bash
#!/usr/bin/env bash
# End-to-end smoke: build image, boot container, assert boot/SPA/API round-trip.
# No whisper model, no LLM. Set SKIP_BUILD=1 to reuse a prebuilt $IMAGE.
set -euo pipefail

IMAGE="${IMAGE:-steno10k:smoke}"
CONTAINER="steno10k-smoke-$$"
PORT="${PORT:-8000}"
BASE="http://localhost:${PORT}"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -f /tmp/steno-smoke-clip.wav 2>/dev/null || true
}
trap cleanup EXIT

if [ "${SKIP_BUILD:-0}" != "1" ]; then
  echo "==> building $IMAGE"
  docker build -t "$IMAGE" .
fi

echo "==> booting $CONTAINER"
docker run -d --name "$CONTAINER" -p "${PORT}:8000" "$IMAGE" >/dev/null

echo "==> waiting for health"
for _ in $(seq 1 60); do
  if curl -fsS "${BASE}/api/v1/health" >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS "${BASE}/api/v1/health" | grep -q '"status":"ok"'

echo "==> SPA root + deep link"
curl -fsS "${BASE}/" | grep -qi '<!doctype html>'
curl -fsS "${BASE}/p/smoke/s/set-1" | grep -qi '<!doctype html>'

echo "==> API round-trip"
curl -fsS -X POST "${BASE}/api/v1/projects" \
  -H 'content-type: application/json' -d '{"title":"Smoke"}' >/dev/null
curl -fsS -X POST "${BASE}/api/v1/projects/smoke/sets" \
  -H 'content-type: application/json' -d '{"title":"Set 1"}' >/dev/null
printf 'RIFF0000WAVEfmt ' > /tmp/steno-smoke-clip.wav
curl -fsS -X POST "${BASE}/api/v1/projects/smoke/sets/set-1/recordings" \
  -F 'files=@/tmp/steno-smoke-clip.wav' >/dev/null
curl -fsS "${BASE}/api/v1/projects/smoke/sets/set-1/recordings" | grep -q 'steno-smoke-clip'

echo "SMOKE PASS"
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/smoke.sh`
Expected: no output.

- [ ] **Step 3: Run the smoke locally**

Run: `./scripts/smoke.sh`
Expected: ends with `SMOKE PASS` and exit code 0. (Confirm the project/set slugs: title `Smoke` -> `smoke`, `Set 1` -> `set-1`. If the create endpoints return a different slug, adjust the URLs to match the returned `slug`.)

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke.sh
git commit -m "test(smoke): e2e container boot + SPA + API round-trip script"
```

---

## Task 7: Wire the smoke into CI

Make the existing `docker` job build the image and run the smoke against it.

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Read the current docker job**

Run: `sed -n '76,95p' .github/workflows/ci.yml`
Expected: shows the `docker:` job using `docker/build-push-action` with `push: false`, and the `needs: [backend, frontend, docker]` gate.

- [ ] **Step 2: Update the docker job to load + smoke**

Edit the `docker:` job in `.github/workflows/ci.yml`. Ensure the build step loads the image locally and add a smoke step. The job should look like:
```yaml
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Build image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          load: true
          tags: steno10k:smoke
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: e2e smoke
        run: SKIP_BUILD=1 IMAGE=steno10k:smoke ./scripts/smoke.sh
```
(Keep the existing `context`/other keys if already present; the additions are `load: true`, `tags: steno10k:smoke`, and the `e2e smoke` step. Leave the `needs: [...]` line and other jobs unchanged.)

- [ ] **Step 3: Validate the workflow YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"`
Expected: prints `yaml ok`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run e2e smoke against the built container image"
```

---

## Task 8: Hosting & prerequisites docs (MDX docs site)

Add a maintained Self-hosting page with the hardware/RAM math and Docker guidance; cross-link from getting-started and configuration.

**Files:**
- Create: `docs-site/src/pages/self-hosting.mdx`
- Modify: `docs-site/src/nav.ts`
- Modify: `docs-site/src/pages/getting-started.mdx`
- Modify: `docs-site/src/pages/configuration.mdx`

- [ ] **Step 1: Write the Self-hosting page**

Create `docs-site/src/pages/self-hosting.mdx`:
```mdx
---
layout: ../layouts/DocsLayout.astro
title: Self-hosting
---

# Self-hosting

steno10k ships as a single container that serves both the API and the web UI,
backed by one mounted volume. Everything — recordings, artifacts, `config.yaml`,
and the downloaded Whisper model — lives under that volume.

## Quick start

```bash
docker compose up
```

Then open <http://localhost:8000>. Or run the published image directly:

```bash
docker run --rm -p 8000:8000 -v steno10k-data:/data \
  ghcr.io/bardin08/steno10k:latest
```

## Secrets

The transcription stage runs locally; only the clean/summarize stages call an
LLM, and only if you configure one. Provide the key via the environment — never
in `config.yaml`:

```bash
# .env  (loaded by docker compose)
OPENAI_API_KEY=sk-...
```

## First run downloads the model

On the **first transcription**, faster-whisper downloads the configured Whisper
model into the volume (`/data/.cache/huggingface`). This can take a few minutes
and streams progress to the container logs — **it is not stuck**. Subsequent runs
reuse the cached model, so only the first run pays this cost.

## Hardware & memory

Only Whisper transcription is resource-heavy; the LLM stages are remote API calls
and the app itself is light. The single knob that sets your hardware floor is the
Whisper model size — and, critically, **each transcription worker loads its own
copy of the model**, so total RAM scales with `transcription.max_workers`.

| Model | Disk | RAM **per worker** (int8/CPU) | Quality | Speed (~realtime) |
| --- | --- | --- | --- | --- |
| tiny | ~75 MB | ~0.5–1 GB | rough | ~10–30× |
| base | ~145 MB | ~1 GB | decent | ~7–15× |
| small (default) | ~490 MB | ~1.5–2 GB | good | ~4–6× |
| medium | ~1.5 GB | ~2.5–4 GB | very good | ~1.5–2× |
| large-v3 | ~3 GB | ~4–6 GB | best | ~0.5–1× |

> **Total RAM ≈ per-worker footprint × `max_workers`.** The shipped default is
> `small × 2` (~3.5 GB peak). Bumping to `large-v3 × 4` needs ~16–20 GB and will
> be OOM-killed on a default Docker Desktop — which looks like a silent stall.
> steno10k logs a non-blocking warning (and shows it on the run) when your config
> likely exceeds available memory.

### Docker Desktop memory

Docker Desktop runs containers inside a VM with its own memory ceiling:

- **macOS:** defaults to ~8 GB on a 16 GB machine (min floor ~4 GB). Raise it in
  **Settings → Resources**, then Apply & Restart.
- **Windows (WSL 2):** defaults to up to 50% of host RAM; cap or raise it via
  `%UserProfile%\.wslconfig` (`[wsl2]` → `memory=8GB`), then `wsl --shutdown`.

Leave at least 4 GB and 2 cores for the host OS.

### Apple Silicon

CTranslate2 (the Whisper backend) is **CPU-only on Apple Silicon** — there is no
Metal/MPS acceleration (GPU acceleration is CUDA-only). Transcription runs on the
CPU on Macs; pick a smaller model if throughput matters.
```

- [ ] **Step 2: Register the page in nav**

Edit `docs-site/src/nav.ts` — add the entry after Configuration:
```ts
export const nav: NavItem[] = [
  { title: "Overview", slug: "" },
  { title: "Getting started", slug: "getting-started" },
  { title: "Configuration", slug: "configuration" },
  { title: "Self-hosting", slug: "self-hosting" },
];
```

- [ ] **Step 3: Cross-link from getting-started**

Edit `docs-site/src/pages/getting-started.mdx`. Under the "Run it in one container"
list, append a bullet:
```mdx
- The Whisper model downloads into the mounted volume on your first run (a few
  minutes, streamed to logs — not stuck), then is reused. Set `OPENAI_API_KEY`
  in `.env` if you want the clean/summarize stages. See
  [Self-hosting](/self-hosting) for hardware and memory guidance.
```

- [ ] **Step 4: Link the RAM math from configuration**

Edit `docs-site/src/pages/configuration.mdx`. Immediately after the eight-stages
table, add:
```mdx
Transcription runs multiple workers in parallel; each loads its own copy of the
Whisper model, so total RAM ≈ per-worker footprint × `max_workers`. The default
is `small × 2`. See [Self-hosting](/self-hosting#hardware--memory) before raising
either knob.
```

- [ ] **Step 5: Build the docs site**

Run: `cd docs-site && npm ci && npm run build`
Expected: build succeeds; `self-hosting` compiles into the output with no broken-link/MDX errors.

- [ ] **Step 6: Commit**

```bash
git add docs-site/src/pages/self-hosting.mdx docs-site/src/nav.ts \
  docs-site/src/pages/getting-started.mdx docs-site/src/pages/configuration.mdx
git commit -m "docs(site): self-hosting page — hardware, memory math, model cache"
```

---

## Task 9: Record M2 forward-work (roadmap + ADR)

Capture the two deferred features so they are tracked, not dropped.

**Files:**
- Modify: `docs/specs/2026-07-11-new-audio-pipeline-vision-design.md`
- Create: `docs/adr/000N-defer-resource-syscheck-and-ui-model-download.md` (N assigned under the lock)

- [ ] **Step 1: Take the ADR-numbering lock**

Create `~/.claude/locks/steno10k/adr.lock.md` with the ADR title, the next number you intend to use, and this branch. Then compute the next free number:
```bash
ls docs/adr/
```
Expected: pick the lowest unused `NNNN`. (Note: existing files reuse `0001`/`0002` prefixes; scan them and choose the next number that is genuinely unused across the directory.)

- [ ] **Step 2: Add the roadmap items to the vision spec**

Edit `docs/specs/2026-07-11-new-audio-pipeline-vision-design.md`. In the `## 9`
section, directly under the two existing bullets ("Total RAM ≈ ..." and
"CTranslate2 is CPU-only ..."), add:
```md
- **M2 — Resource syscheck (deferred from M1·P):** inspect the container's
  memory/CPU (cgroup limits), *recommend* a model + `max_workers` config, and
  *warn or refuse* infeasible selections (e.g. `large-v3 × 8` on 10 GB), surfaced
  in both config and the UI. M1·P ships only the non-blocking warning precursor.
- **M2 — UI-initiated model download (deferred from M1·P):** let the user select
  and download a Whisper model from the UI with a visible progress indicator, so
  the first-run download is never mistaken for a hang; the selector reflects which
  models are already cached.
```

- [ ] **Step 3: Write the ADR**

Create `docs/adr/000N-defer-resource-syscheck-and-ui-model-download.md` (use the
number chosen in Step 1):
```md
# 000N — Defer resource syscheck and UI model download to M2

## Status
Accepted

## Context
M1·P (single-container packaging) surfaced two resource-UX gaps around Whisper:

1. Each transcription worker loads its own model copy, so RAM scales with
   `max_workers`. A user can pick a model/worker combo that OOM-kills the
   container on a default Docker Desktop — which looks like a silent stall.
2. On first transcription the model downloads (minutes), with no in-UI signal, so
   the run appears hung.

M1·P's prime directive is simplicity; a full interactive syscheck and a UI
model-download manager are their own features and would balloon the packaging
unit.

## Decision
M1·P ships only:
- a **non-blocking memory preflight** — logs a warning and records it on the run
  when the configured model × workers likely exceeds the cgroup memory limit;
- **hosting docs** with the hardware/RAM table and Docker memory guidance;
- **model caching to the volume** (download once, persist) with a documented
  "first run downloads the model" note.

Deferred to **M2 — Configurability polish**:
- an **interactive resource syscheck** that recommends a config and warns/refuses
  infeasible selections in config + UI;
- **UI-initiated model download with progress**, with a selector reflecting cached
  models.

## Consequences
- M1·P stays small and shippable; users get honest docs and a safety-net warning.
- The M2 features have a recorded home (vision §9) and this ADR as their rationale.
```

- [ ] **Step 4: Commit and release the lock**

```bash
git add docs/specs/2026-07-11-new-audio-pipeline-vision-design.md docs/adr/000N-*.md
git commit -m "docs(adr): defer resource syscheck + UI model download to M2"
rm -f ~/.claude/locks/steno10k/adr.lock.md
```
(Replace `000N` with the actual filename.)

---

## Task 10: Full verification & PR

**Files:** none (verification + PR)

- [ ] **Step 1: Backend lint + typecheck + tests**

Run:
```bash
cd backend && uv run ruff check . && uv run mypy && uv run pytest -q
```
Expected: ruff clean, mypy clean (strict, over `src` and `tests`), all tests pass.

- [ ] **Step 2: Full pre-commit**

Run: `pre-commit run --all-files`
Expected: all hooks pass (rerun once if a formatter reflows a file, then re-stage).

- [ ] **Step 3: End-to-end smoke**

Run: `./scripts/smoke.sh`
Expected: `SMOKE PASS`.

- [ ] **Step 4: Manual acceptance — model cache persists**

Run:
```bash
docker compose up -d
# upload a short real clip via the UI at http://localhost:8000, run it (set OPENAI_API_KEY in .env for the LLM stages),
# confirm a summary/bundle artifact appears, then:
docker compose restart
# run again and confirm NO model re-download in logs (cache reused):
docker compose logs --tail=50 app
docker compose down
```
Expected: first run downloads the model to `/data/.cache/huggingface`; after restart the second run reuses it (no download log lines).

- [ ] **Step 5: Open the PR**

Run:
```bash
git push -u origin "$(git branch --show-current)"
gh pr create --fill --base main \
  --title "M1·P: single-container packaging (SPA fallback, model cache, e2e smoke, hosting docs)" \
  --body "Closes #${ISSUE}

Makes the M0 Docker skeleton real. SPA deep-link fallback, whisper model cached to the volume, non-root entrypoint with first-boot config seed + healthcheck, ML-free e2e smoke gating CI, memory preflight warning, container-safe default (small x2), Self-hosting docs page, and M2 forward-work recorded (ADR). See docs/specs/2026-07-12-steno10k-m1-p-single-container-packaging-design.md."
```
Expected: PR created; CI (backend, frontend, docker+smoke, docs) runs green.

---

## Notes on decomposition & boundaries

- **`api/preflight.py`** is a pure, dependency-light module (config + filesystem reads only) — unit-tested in isolation; `runq` just calls `memory_warning`.
- **`SPAStaticFiles`** is a small serving-infra subclass local to `api/__init__.py`; it changes no API DTO and adds no OpenAPI path.
- **`entrypoint.sh`** owns all first-boot/runtime concerns (data dir, HF cache, config seed, privilege drop), keeping the Dockerfile declarative.
- **Docs** live in `docs-site/` (MDX, maintained) as the single source of truth; the README only points there.
- No frozen contract (`contracts/`, existing API DTOs/OpenAPI, `tokens.css`, `standards/`) is edited.
```
