from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from steno10k.contracts.errors import ErrorLog
from steno10k.lib.docx import build_bundle


def _make_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_builds_docx_for_each_existing_source(tmp_path: Path) -> None:
    src = tmp_path / "clean.md"
    _make_md(src, "# Title\n\nBody.")
    dst = tmp_path / "out" / "clean.docx"
    err = ErrorLog(tmp_path / "errors.log")
    build_bundle([(src, dst)], force=False, err_log=err)
    assert dst.exists()
    assert err.count == 0
    assert any(p.text == "Title" for p in Document(str(dst)).paragraphs)


def test_missing_source_is_skipped_not_errored(tmp_path: Path) -> None:
    dst = tmp_path / "out" / "missing.docx"
    err = ErrorLog(tmp_path / "errors.log")
    build_bundle([(tmp_path / "nope.md", dst)], force=False, err_log=err)
    assert not dst.exists()
    assert err.count == 0


def test_existing_dst_not_overwritten_unless_force(tmp_path: Path) -> None:
    src = tmp_path / "clean.md"
    _make_md(src, "hello")
    dst = tmp_path / "out" / "clean.docx"
    dst.parent.mkdir(parents=True)
    dst.write_text("SENTINEL", encoding="utf-8")
    err = ErrorLog(tmp_path / "errors.log")
    build_bundle([(src, dst)], force=False, err_log=err)
    assert dst.read_text(encoding="utf-8") == "SENTINEL"
    build_bundle([(src, dst)], force=True, err_log=err)
    assert dst.read_text(encoding="utf-8", errors="ignore") != "SENTINEL"


def test_one_bad_source_does_not_abort_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import steno10k.lib.docx as docxmod

    good = tmp_path / "good.md"
    bad = tmp_path / "bad.md"
    _make_md(good, "good")
    _make_md(bad, "bad")
    good_dst = tmp_path / "out" / "good.docx"
    bad_dst = tmp_path / "out" / "bad.docx"
    err = ErrorLog(tmp_path / "errors.log")

    real_build_one = docxmod._build_one

    def flaky(source: Path, dst: Path, force: bool) -> None:
        if source == bad:
            raise RuntimeError("render exploded")
        real_build_one(source, dst, force)

    monkeypatch.setattr(docxmod, "_build_one", flaky)
    build_bundle([(bad, bad_dst), (good, good_dst)], force=False, err_log=err)
    assert good_dst.exists()
    assert not bad_dst.exists()
    assert err.count == 1
