from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config


def resolve_override_dir(cfg: Config, set_dir: Path) -> Path:
    """Prompt override directory for the LLM stages.

    Mirrors the F2 prompts router: an explicit `cfg.prompts.override_dir` wins;
    otherwise `<data_root>/prompt_overrides`, where `data_root` is the grandparent
    of `set_dir` (`<data_root>/<project>/<set>`). Overrides a user sets in the UI
    (written under the same directory) are therefore honored by the stages.
    """
    if cfg.prompts.override_dir:
        return Path(cfg.prompts.override_dir)
    return set_dir.parent.parent / "prompt_overrides"
