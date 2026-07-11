from __future__ import annotations

from pathlib import Path

import pytest

import steno10k.stages.chunk as chunk_mod
from stages.conftest import MakeCtx
from steno10k.contracts.domain import Recording
from steno10k.contracts.events import EventKind
from steno10k.contracts.status import StageStatus
from steno10k.stages.chunk import ChunkStage


def _fake_extract(src: Path, dst: Path, start: float, end: float, fmt: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(b"chunk")


def test_extracts_chunks_and_records_relative_paths(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chunk_mod, "plan_chunks", lambda *a, **k: [(0.0, 600.0), (585.0, 900.0)])
    calls: list[tuple[str, float, float, str]] = []

    def rec_extract(src: Path, dst: Path, start: float, end: float, fmt: str) -> None:
        _fake_extract(src, dst, start, end, fmt)
        calls.append((dst.name, start, end, fmt))

    monkeypatch.setattr(chunk_mod, "extract_chunk", rec_extract)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a", duration_seconds=900.0)
    ctx, events = make_ctx([rec])
    (ctx.set_dir / "rec.m4a").write_bytes(b"x")
    result = ChunkStage().run(ctx)
    assert result.status is StageStatus.OK
    assert rec.chunks == ["chunks/rec/chunk_000.m4a", "chunks/rec/chunk_001.m4a"]
    assert (ctx.set_dir / "chunks" / "rec" / "chunk_000.m4a").exists()
    assert result.stats == {"recordings": 1, "chunks": 2}
    assert calls[0] == ("chunk_000.m4a", 0.0, 600.0, "m4a")
    assert any(e.kind is EventKind.STAGE_PROGRESS for e in events)


def test_skips_existing_chunk_unless_force(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chunk_mod, "plan_chunks", lambda *a, **k: [(0.0, 600.0)])
    extracted: list[str] = []

    def rec_extract(src: Path, dst: Path, start: float, end: float, fmt: str) -> None:
        _fake_extract(src, dst, start, end, fmt)
        extracted.append(dst.name)

    monkeypatch.setattr(chunk_mod, "extract_chunk", rec_extract)
    ctx, _ = make_ctx(
        [Recording(source_name="rec.m4a", normalized_name="rec.m4a", duration_seconds=600.0)],
        force=False,
    )
    (ctx.set_dir / "rec.m4a").write_bytes(b"x")
    existing = ctx.set_dir / "chunks" / "rec" / "chunk_000.m4a"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    ChunkStage().run(ctx)
    assert extracted == []  # existing chunk left alone

    ctx2, _ = make_ctx(
        [Recording(source_name="rec.m4a", normalized_name="rec.m4a", duration_seconds=600.0)],
        force=True,
    )
    ChunkStage().run(ctx2)
    assert extracted == ["chunk_000.m4a"]  # force re-extracted


def test_probes_duration_when_manifest_lacks_it(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chunk_mod, "get_duration_seconds", lambda p: 300.0)
    captured: dict[str, float] = {}

    def fake_plan(
        duration: float, chunk_seconds: int, overlap_seconds: int, min_chunk_seconds: int
    ) -> list[tuple[float, float]]:
        captured["duration"] = duration
        return [(0.0, 300.0)]

    monkeypatch.setattr(chunk_mod, "plan_chunks", fake_plan)
    monkeypatch.setattr(chunk_mod, "extract_chunk", _fake_extract)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")  # no duration
    ctx, _ = make_ctx([rec])
    (ctx.set_dir / "rec.m4a").write_bytes(b"x")
    ChunkStage().run(ctx)
    assert captured["duration"] == 300.0


def test_missing_source_is_logged_and_isolated(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chunk_mod, "plan_chunks", lambda *a, **k: [(0.0, 10.0)])
    monkeypatch.setattr(chunk_mod, "extract_chunk", _fake_extract)
    bad = Recording(source_name="b.m4a", normalized_name="b.m4a", duration_seconds=10.0)  # no file
    good = Recording(source_name="g.m4a", normalized_name="g.m4a", duration_seconds=10.0)
    ctx, _ = make_ctx([bad, good])
    (ctx.set_dir / "g.m4a").write_bytes(b"x")
    result = ChunkStage().run(ctx)
    assert ctx.errors.count == 1
    assert good.chunks == ["chunks/g/chunk_000.m4a"]
    assert bad.chunks == []
    assert result.status is StageStatus.OK


def test_partial_failure_persists_completed_chunks(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        chunk_mod, "plan_chunks", lambda *a, **k: [(0.0, 10.0), (10.0, 20.0), (20.0, 30.0)]
    )

    def flaky_extract(src: Path, dst: Path, start: float, end: float, fmt: str) -> None:
        if dst.name == "chunk_002.m4a":
            raise RuntimeError("ffmpeg blew up")
        _fake_extract(src, dst, start, end, fmt)

    monkeypatch.setattr(chunk_mod, "extract_chunk", flaky_extract)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a", duration_seconds=30.0)
    ctx, _ = make_ctx([rec])
    (ctx.set_dir / "rec.m4a").write_bytes(b"x")
    result = ChunkStage().run(ctx)
    assert ctx.errors.count == 1
    # the two chunks that succeeded are recorded, matching what's on disk
    assert rec.chunks == ["chunks/rec/chunk_000.m4a", "chunks/rec/chunk_001.m4a"]
    assert result.status is StageStatus.OK
