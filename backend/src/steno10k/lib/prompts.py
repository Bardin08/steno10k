from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROMPT_NAMES: tuple[str, ...] = ("clean", "summarize")

# English, domain-neutral built-in defaults. The `summarize` template carries a
# `{target_output_language}` placeholder that the summarize stage formats; the
# loader itself never formats (it only stores/loads text).
_DEFAULTS: dict[str, str] = {
    "clean": (
        "You are cleaning a raw speech-to-text transcript. Fix punctuation, "
        "capitalization, obvious recognition errors, and paragraph structure, and "
        "remove repeated filler fragments. Preserve the original meaning, wording, "
        "and language. Do not summarize, translate, or add facts. Return only the "
        "corrected transcript as Markdown (paragraphs separated by blank lines), "
        "with no preamble."
    ),
    "summarize": (
        "You produce a detailed, well-structured Markdown summary from a cleaned "
        "transcript. Preserve concrete facts: dates, names, places, numbers, "
        "definitions, and short direct quotes. Do not generalize away specifics or "
        "invent facts; mark anything unclear inline as (unclear: ...). Organize the "
        "summary by topic with headings. Write the output in this language: "
        "{target_output_language}. Return only the Markdown summary, with no preamble."
    ),
}


@dataclass(frozen=True)
class Prompts:
    clean: str
    summarize: str


def default_prompt(name: str) -> str:
    """Built-in default for `name`. Raises KeyError for an unknown name."""
    return _DEFAULTS[name]


def resolve_prompt(name: str, override_dir: Path | None) -> tuple[str, str]:
    """Return (content, source) where source is "override" or "default".

    An override is a file `<override_dir>/<name>.md`; if present it wins.
    """
    if name not in _DEFAULTS:
        raise KeyError(name)
    if override_dir is not None:
        candidate = override_dir / f"{name}.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8"), "override"
    return _DEFAULTS[name], "default"


def load_prompts(override_dir: Path | None) -> Prompts:
    """Resolve every prompt into a `Prompts` bundle for the stages."""
    resolved = {name: resolve_prompt(name, override_dir)[0] for name in PROMPT_NAMES}
    return Prompts(**resolved)
