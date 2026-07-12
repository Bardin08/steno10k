from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from steno10k.contracts.config import Config
from steno10k.contracts.domain import Recording
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import Event, EventBus
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.stage import StageContext

MakeCtx = Callable[..., tuple[StageContext, list[Event]]]


@pytest.fixture
def make_ctx(tmp_path: Path) -> MakeCtx:
    """Factory: build a StageContext over `tmp_path` and capture emitted events.

    Usage: `ctx, events = make_ctx([Recording(...)], force=True)`. `set_dir` is
    always `tmp_path`, so tests place source files / chunks under `tmp_path`.
    """

    def _make(
        recordings: list[Recording],
        *,
        force: bool = False,
        cfg: Config | None = None,
    ) -> tuple[StageContext, list[Event]]:
        manifest = Manifest(project_slug="p", set_slug="s", title="S", recordings=recordings)
        bus = EventBus()
        events: list[Event] = []
        bus.subscribe(events.append)
        ctx = StageContext(
            set_dir=tmp_path,
            cfg=cfg or Config(),
            force=force,
            manifest=manifest,
            errors=ErrorLog(tmp_path / "errors.log"),
            events=bus,
            llm=None,
        )
        return ctx, events

    return _make


@pytest.fixture
def set_dir(tmp_path: Path) -> Path:
    """A fresh set directory shaped like <data_root>/<project>/<set>."""
    d = tmp_path / "data" / "proj" / "set-a"
    d.mkdir(parents=True)
    return d
