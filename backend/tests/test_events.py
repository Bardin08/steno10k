from __future__ import annotations

from steno10k.contracts.events import Event, EventBus, EventKind


def test_subscribers_receive_events() -> None:
    bus = EventBus()
    seen: list[Event] = []
    bus.subscribe(seen.append)
    bus.emit(Event(kind=EventKind.STAGE_STARTED, payload={"stage": "normalize"}))
    assert seen[0].kind is EventKind.STAGE_STARTED
    assert seen[0].payload["stage"] == "normalize"


def test_subscriber_error_is_isolated() -> None:
    bus = EventBus()
    good: list[Event] = []

    def boom(_: Event) -> None:
        raise RuntimeError("subscriber blew up")

    bus.subscribe(boom)
    bus.subscribe(good.append)
    bus.emit(Event(kind=EventKind.RUN_STARTED, payload={}))
    assert len(good) == 1
