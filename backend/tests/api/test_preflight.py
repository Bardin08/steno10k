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
    assert read_cgroup_limit_bytes(v2_path=tmp_path / "a", v1_path=tmp_path / "b") is None


def test_memory_warning_fires_when_over() -> None:
    cfg = Config()
    cfg.transcription.model = "large-v3"
    cfg.transcription.max_workers = 4
    msg = memory_warning(cfg, limit_bytes=8 * GB)
    assert msg is not None
    assert "large-v3" in msg


def test_memory_warning_silent_when_fits() -> None:
    cfg = Config()
    cfg.transcription.model = "small"
    cfg.transcription.max_workers = 2
    assert memory_warning(cfg, limit_bytes=8 * GB) is None


def test_memory_warning_silent_when_limit_unknown() -> None:
    cfg = Config()
    cfg.transcription.model = "large-v3"
    cfg.transcription.max_workers = 8
    assert memory_warning(cfg, limit_bytes=None) is None
