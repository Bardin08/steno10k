from __future__ import annotations

from pathlib import Path

import pytest

from steno10k.lib.prompts import (
    PROMPT_NAMES,
    default_prompt,
    load_prompts,
    resolve_prompt,
)


def test_prompt_names_are_the_m1_llm_stages() -> None:
    assert set(PROMPT_NAMES) == {"clean", "summarize"}


def test_defaults_are_english_and_domain_neutral() -> None:
    text = default_prompt("clean") + default_prompt("summarize")
    lowered = text.lower()
    for banned in ("lecture", "conspect", "ukrainian", "лекц"):
        assert banned not in lowered


def test_summarize_default_has_target_language_placeholder() -> None:
    assert "{target_output_language}" in default_prompt("summarize")


def test_unknown_prompt_name_raises() -> None:
    with pytest.raises(KeyError):
        default_prompt("nope")


def test_resolve_returns_default_when_no_override(tmp_path: Path) -> None:
    content, source = resolve_prompt("clean", tmp_path)
    assert source == "default"
    assert content == default_prompt("clean")


def test_override_file_wins(tmp_path: Path) -> None:
    (tmp_path / "clean.md").write_text("CUSTOM CLEAN", encoding="utf-8")
    content, source = resolve_prompt("clean", tmp_path)
    assert source == "override"
    assert content == "CUSTOM CLEAN"


def test_rollback_by_removing_override(tmp_path: Path) -> None:
    override = tmp_path / "clean.md"
    override.write_text("CUSTOM", encoding="utf-8")
    assert resolve_prompt("clean", tmp_path)[1] == "override"
    override.unlink()
    assert resolve_prompt("clean", tmp_path)[1] == "default"


def test_load_prompts_bundle(tmp_path: Path) -> None:
    (tmp_path / "summarize.md").write_text("CUSTOM SUM", encoding="utf-8")
    prompts = load_prompts(tmp_path)
    assert prompts.clean == default_prompt("clean")
    assert prompts.summarize == "CUSTOM SUM"


def test_load_prompts_with_no_override_dir_uses_defaults() -> None:
    prompts = load_prompts(None)
    assert prompts.clean == default_prompt("clean")
    assert prompts.summarize == default_prompt("summarize")
