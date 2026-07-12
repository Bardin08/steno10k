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
