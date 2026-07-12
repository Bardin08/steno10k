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
