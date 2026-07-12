from __future__ import annotations

from steno10k.lib.ingest import SUPPORTED_EXTENSIONS, normalized_filename


def test_supported_extensions_contains_common_audio() -> None:
    assert {".mp3", ".wav", ".m4a"} <= SUPPORTED_EXTENSIONS


def test_normalized_filename_slugifies_stem() -> None:
    assert normalized_filename("Lecture 1.M4A", set()) == "lecture-1.m4a"


def test_normalized_filename_dedupes_same_suffix_only() -> None:
    existing = {"a.m4a"}
    assert normalized_filename("a.m4a", existing) == "a_2.m4a"
    # different suffix does not collide
    assert normalized_filename("a.mp3", existing) == "a.mp3"
