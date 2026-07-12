# syntax=docker/dockerfile:1

# --- Stage 1: build the frontend SPA ---
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend runtime (serves the built SPA) ---
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
