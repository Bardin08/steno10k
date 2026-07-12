from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from stages.support import make_ctx
from steno10k.contracts.config import Config
from steno10k.contracts.stage import RunOptions
from steno10k.contracts.status import StageStatus
from steno10k.stages.bundle import BundleStage


def _seed(set_dir: Path, *, clean: str | None = None, summary: str | None = None) -> None:
    if clean is not None:
        (set_dir / "merged").mkdir(parents=True, exist_ok=True)
        (set_dir / "merged" / "clean_transcript.md").write_text(clean, encoding="utf-8")
    if summary is not None:
        (set_dir / "summary.md").write_text(summary, encoding="utf-8")


def test_name_and_deps() -> None:
    stage = BundleStage()
    assert stage.name == "bundle"
    assert stage.depends_on == ["merge"]


def test_enabled_gates_on_save_bundle_docx() -> None:
    stage = BundleStage()
    cfg = Config()
    assert stage.enabled(cfg, RunOptions()) is True
    cfg.output.save_bundle_docx = False
    assert stage.enabled(cfg, RunOptions()) is False


def test_builds_both_docx(set_dir: Path) -> None:
    _seed(set_dir, clean="# Transcript\n\nBody.", summary="# Summary\n\nPoints.")
    result = BundleStage().run(set_dir_ctx := make_ctx(set_dir))

    assert result.status == StageStatus.OK
    assert result.stats["built"] == 2
    transcript = set_dir / "bundle" / "transcript.docx"
    summary = set_dir / "bundle" / "summary.docx"
    assert transcript.is_file() and summary.is_file()
    assert any(p.text == "Transcript" for p in Document(str(transcript)).paragraphs)
    assert set_dir_ctx.errors.count == 0


def test_missing_summary_yields_transcript_only(set_dir: Path) -> None:
    _seed(set_dir, clean="# Transcript\n\nBody.")  # no summary.md
    ctx = make_ctx(set_dir)

    result = BundleStage().run(ctx)

    assert result.status == StageStatus.OK
    assert (set_dir / "bundle" / "transcript.docx").is_file()
    assert not (set_dir / "bundle" / "summary.docx").exists()
    assert result.stats["built"] == 1


def test_render_failure_reports_failed(set_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import steno10k.lib.docx as docxmod

    _seed(set_dir, clean="# Transcript\n\nBody.", summary="# Summary")

    def boom(source: Path, dst: Path, force: bool) -> None:
        raise RuntimeError("render exploded")

    monkeypatch.setattr(docxmod, "_build_one", boom)
    ctx = make_ctx(set_dir)

    result = BundleStage().run(ctx)

    assert result.status == StageStatus.FAILED
    assert ctx.errors.count >= 1
