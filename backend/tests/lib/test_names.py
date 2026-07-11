from __future__ import annotations

from steno10k.lib.names import normalize_recording_name


def test_spaces_and_case_become_hyphenated_lowercase() -> None:
    assert normalize_recording_name("My Recording 1.MP3") == "my-recording-1.mp3"


def test_extension_is_preserved_and_lowercased() -> None:
    assert normalize_recording_name("clip.M4A") == "clip.m4a"


def test_cyrillic_is_transliterated_via_slug() -> None:
    assert normalize_recording_name("Лекція 1.m4a") == "lektsiia-1.m4a"


def test_no_extension_returns_slug_only() -> None:
    assert normalize_recording_name("just a name") == "just-a-name"


def test_empty_stem_falls_back_to_untitled() -> None:
    assert normalize_recording_name(".m4a") == "untitled.m4a"
