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


def read_cgroup_limit_bytes(v2_path: Path = _CGROUP_V2, v1_path: Path = _CGROUP_V1) -> int | None:
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
