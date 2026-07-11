from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.domain import Recording
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import Event, EventBus
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.stage import StageContext


class FakeLLM:
    """Stands in for the `contracts.llm.LLMClient` protocol in stage tests.

    `responder(system, user) -> str` computes each reply (default: echo the user
    text). Records every call for assertions. Pass a responder that raises to
    exercise per-item error isolation.
    """

    def __init__(self, responder: Callable[[str, str], str] | None = None) -> None:
        self._responder = responder or (lambda system, user: f"[out] {user}")
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._responder(system, user)


class RecordingBus(EventBus):
    """An `EventBus` that also keeps every emitted event for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[Event] = []
        self.subscribe(self.events.append)


def make_manifest(normalized_names: list[str]) -> Manifest:
    return Manifest(
        project_slug="proj",
        set_slug="set-a",
        title="Set A",
        recordings=[Recording(source_name=n, normalized_name=n) for n in normalized_names],
    )


def seed_raw(set_dir: Path, stem: str, chunks: list[str]) -> None:
    """Write transcripts_raw/<stem>/chunk_NNN.txt fixtures (S1's output shape)."""
    d = set_dir / "transcripts_raw" / stem
    d.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(chunks):
        (d / f"chunk_{i:03d}.txt").write_text(text, encoding="utf-8")


def seed_clean(set_dir: Path, stem: str, chunks: list[str]) -> None:
    """Write transcripts_clean/<stem>/chunk_NNN.md fixtures (clean's output shape)."""
    d = set_dir / "transcripts_clean" / stem
    d.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(chunks):
        (d / f"chunk_{i:03d}.md").write_text(text, encoding="utf-8")


def make_ctx(
    set_dir: Path,
    *,
    cfg: Config | None = None,
    manifest: Manifest | None = None,
    force: bool = False,
    llm: object | None = None,
    events: EventBus | None = None,
) -> StageContext:
    return StageContext(
        set_dir=set_dir,
        cfg=cfg or Config(),
        force=force,
        manifest=manifest or make_manifest(["rec-1.m4a"]),
        errors=ErrorLog(set_dir / "errors.log"),
        events=events or EventBus(),
        llm=llm,  # type: ignore[arg-type]  # FakeLLM implements the complete() protocol
    )
