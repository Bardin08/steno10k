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
