from __future__ import annotations

from pathlib import Path

import pytest

import steno10k.stages.transcribe as transcribe_mod
from stages.conftest import MakeCtx
from steno10k.contracts.domain import Recording
from steno10k.contracts.events import EventKind
from steno10k.lib.transcriber import TranscribeJob, TranscribeSettings
from steno10k.stages.transcribe import (
    _M1_BEAM_SIZE,
    _M1_MIN_SILENCE_MS,
    _M1_VAD_FILTER,
    TranscribeStage,
)


def _make_chunk(set_dir: Path, stem: str, idx: int, fmt: str = "m4a") -> Path:
    d = set_dir / "chunks" / stem
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"chunk_{idx:03d}.{fmt}"
    p.write_bytes(b"audio")
    return p


def test_transcribes_pending_chunks_and_maps_settings(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        captured["settings"] = settings
        captured["max_workers"] = max_workers
        out: list[tuple[Path, str | None]] = []
        for j in jobs:
            j.output_path.parent.mkdir(parents=True, exist_ok=True)
            j.output_path.write_text("text", encoding="utf-8")
            out.append((j.output_path, None))
        return out

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")
    ctx, events = make_ctx([rec])
    _make_chunk(ctx.set_dir, "rec", 0)
    _make_chunk(ctx.set_dir, "rec", 1)
    result = TranscribeStage().run(ctx)
    assert result.stats == {"chunks": 2, "transcribed": 2, "failed": 0}
    assert (ctx.set_dir / "transcripts_raw" / "rec" / "chunk_000.txt").read_text() == "text"
    settings = captured["settings"]
    assert isinstance(settings, TranscribeSettings)
    assert settings.beam_size == _M1_BEAM_SIZE
    assert settings.vad_filter is _M1_VAD_FILTER
    assert settings.min_silence_duration_ms == _M1_MIN_SILENCE_MS
    assert settings.cpu_threads == ctx.cfg.transcription.cpu_threads_per_worker
    assert settings.model == ctx.cfg.transcription.model
    assert captured["max_workers"] == ctx.cfg.transcription.max_workers
    assert any(e.kind is EventKind.STAGE_PROGRESS for e in events)


def test_skips_already_transcribed_unless_force(
    make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        for j in jobs:
            seen.append(j.output_path.name)
            j.output_path.parent.mkdir(parents=True, exist_ok=True)
            j.output_path.write_text("new", encoding="utf-8")
        return [(j.output_path, None) for j in jobs]

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    ctx, _ = make_ctx([Recording(source_name="rec.m4a", normalized_name="rec.m4a")], force=False)
    _make_chunk(ctx.set_dir, "rec", 0)
    done = ctx.set_dir / "transcripts_raw" / "rec" / "chunk_000.txt"
    done.parent.mkdir(parents=True)
    done.write_text("old", encoding="utf-8")
    r1 = TranscribeStage().run(ctx)
    assert seen == []  # nothing pending
    assert r1.stats == {"chunks": 0, "transcribed": 0, "failed": 0}

    ctx2, _ = make_ctx([Recording(source_name="rec.m4a", normalized_name="rec.m4a")], force=True)
    TranscribeStage().run(ctx2)
    assert seen == ["chunk_000.txt"]  # force re-transcribed


def test_per_chunk_failure_is_isolated(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        results: list[tuple[Path, str | None]] = []
        for k, j in enumerate(jobs):
            if k == 0:
                results.append((j.output_path, "WhisperError: boom"))
            else:
                j.output_path.parent.mkdir(parents=True, exist_ok=True)
                j.output_path.write_text("ok", encoding="utf-8")
                results.append((j.output_path, None))
        return results

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")
    ctx, _ = make_ctx([rec])
    _make_chunk(ctx.set_dir, "rec", 0)
    _make_chunk(ctx.set_dir, "rec", 1)
    result = TranscribeStage().run(ctx)
    assert result.stats == {"chunks": 2, "transcribed": 1, "failed": 1}
    assert ctx.errors.count == 1


def test_no_chunks_never_invokes_worker(make_ctx: MakeCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[int] = []

    def fake_transcribe(
        jobs: list[TranscribeJob], settings: TranscribeSettings, max_workers: int
    ) -> list[tuple[Path, str | None]]:
        called.append(1)
        return []

    monkeypatch.setattr(transcribe_mod, "transcribe_chunks", fake_transcribe)
    rec = Recording(source_name="rec.m4a", normalized_name="rec.m4a")  # no chunks dir
    ctx, _ = make_ctx([rec])
    result = TranscribeStage().run(ctx)
    assert result.stats == {"chunks": 0, "transcribed": 0, "failed": 0}
    assert called == []
