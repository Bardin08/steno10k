from __future__ import annotations

from pathlib import Path

import pytest

import steno10k.stages.normalize as normalize_mod
from stages.conftest import MakeCtx
from steno10k.contracts.domain import Recording
from steno10k.contracts.events import EventKind
from steno10k.contracts.status import StageStatus
from steno10k.lib.ffmpeg import FFmpegError
from steno10k.stages.normalize import NormalizeStage


def test_ffmpeg_missing_fails_fast(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise FFmpegError("no ffmpeg")

    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", boom)
    ctx, _ = make_ctx([Recording(source_name="a.m4a", normalized_name="a.m4a")])
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.FAILED
    assert ctx.errors.count == 1


def test_probes_duration_and_records_on_manifest(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(normalize_mod, "get_duration_seconds", lambda p: 123.0)
    rec = Recording(source_name="a.m4a", normalized_name="a.m4a")
    ctx, events = make_ctx([rec])
    (ctx.set_dir / "a.m4a").write_bytes(b"x")
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert rec.duration_seconds == 123.0
    assert result.stats == {"recordings": 1}
    assert any(e.kind is EventKind.STAGE_PROGRESS for e in events)


def test_missing_source_is_logged_not_fatal(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(normalize_mod, "get_duration_seconds", lambda p: 10.0)
    present = Recording(source_name="a.m4a", normalized_name="a.m4a")
    missing = Recording(source_name="b.m4a", normalized_name="b.m4a")
    ctx, _ = make_ctx([present, missing])
    (ctx.set_dir / "a.m4a").write_bytes(b"x")
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK  # sibling survived
    assert present.duration_seconds == 10.0
    assert missing.duration_seconds is None
    assert ctx.errors.count == 1
    assert result.stats == {"recordings": 1}


def test_probe_error_is_isolated(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def flaky(p: Path) -> float:
        raise RuntimeError("probe blew up")

    monkeypatch.setattr(normalize_mod, "ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr(normalize_mod, "get_duration_seconds", flaky)
    rec = Recording(source_name="a.m4a", normalized_name="a.m4a")
    ctx, _ = make_ctx([rec])
    (ctx.set_dir / "a.m4a").write_bytes(b"x")
    result = NormalizeStage().run(ctx)
    assert result.status is StageStatus.OK
    assert ctx.errors.count == 1
    assert result.stats == {"recordings": 0}
