from __future__ import annotations

from steno10k.contracts.slug import resolve_collision, slugify


def test_slugify_lowercases_and_hyphenates() -> None:
    assert slugify("Judicial Review — Part 1") == "judicial-review-part-1"


def test_slugify_handles_unicode() -> None:
    assert slugify("Івана Франка") == "ivana-franka"


def test_slugify_empty_falls_back() -> None:
    assert slugify("   ") == "untitled"


def test_resolve_collision_suffixes() -> None:
    assert resolve_collision(set(), "week-1") == "week-1"
    assert resolve_collision({"week-1"}, "week-1") == "week-1_2"
    assert resolve_collision({"week-1", "week-1_2"}, "week-1") == "week-1_3"
