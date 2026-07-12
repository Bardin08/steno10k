from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from typing import Any

log = logging.getLogger("steno10k.events")


class EventKind(StrEnum):
    RUN_STARTED = "run_started"
    STAGE_STARTED = "stage_started"
    STAGE_PROGRESS = "stage_progress"
    STAGE_COMPLETED = "stage_completed"
    STAGE_SKIPPED = "stage_skipped"
    STAGE_FAILED = "stage_failed"
    RUN_COMPLETED = "run_completed"
    ERROR = "error"


@dataclass
class Event:
    kind: EventKind
    payload: dict[str, Any] = field(default_factory=dict)


class EventEmitter:
    """Emit-only handle held by stages."""

    def emit(self, event: Event) -> None:  # pragma: no cover - overridden
        raise NotImplementedError


class EventBus(EventEmitter):
    def __init__(self) -> None:
        self._subscribers: list[Callable[[Event], None]] = []
        self._lock = Lock()

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        with self._lock:
            self._subscribers.append(handler)

    def emit(self, event: Event) -> None:
        with self._lock:
            handlers = list(self._subscribers)
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # isolation: one bad subscriber must not break dispatch
                log.exception("event subscriber failed for %s", event.kind)
