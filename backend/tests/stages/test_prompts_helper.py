from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.stages._prompts import resolve_override_dir


def test_falls_back_to_data_root_prompt_overrides():
    set_dir = Path("/data/proj/set-a")
    cfg = Config()  # prompts.override_dir defaults to None
    assert resolve_override_dir(cfg, set_dir) == Path("/data/prompt_overrides")


def test_explicit_override_dir_wins():
    set_dir = Path("/data/proj/set-a")
    cfg = Config()
    cfg.prompts.override_dir = "/custom/prompts"
    assert resolve_override_dir(cfg, set_dir) == Path("/custom/prompts")
