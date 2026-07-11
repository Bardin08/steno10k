from __future__ import annotations

import asyncio

from steno10k.api.sse import _POLL_TIMEOUT_SECONDS, sse_stream
from steno10k.contracts.events import Event, EventBus, EventKind


def test_backstop_terminates_when_terminal_event_is_never_delivered() -> None:
    """Regression test for the lock-ordering race documented in `sse_stream`.

    Simulates the failure mode found in review: the run's `run_completed`
    event never reaches the bridge (neither via `history()` nor via the live
    queue) -- e.g. because `EventBus.emit` and `RunQueue._record_event`
    interleaved unluckily. Without the `is_terminal` backstop, the poll loop
    would retry `queue.Empty` forever since it never sees a terminal event
    and `history()` never reports one either.

    `is_terminal` reflects the run's own recorded status, independent of the
    event stream, so the generator must still close deterministically.
    """
    bus = EventBus()

    async def run() -> list[str]:
        chunks: list[str] = []
        stream = sse_stream(
            bus,
            history=lambda: [],  # run_completed never made it into history
            is_terminal=lambda: True,  # but the run's own status is terminal
        )
        async for chunk in stream:
            chunks.append(chunk)
        return chunks

    # Bound well above one poll interval so the backstop has a chance to
    # fire, but far below "hangs forever" so a regression fails fast.
    timeout = max(2.0, _POLL_TIMEOUT_SECONDS * 4)
    chunks = asyncio.run(asyncio.wait_for(run(), timeout=timeout))

    # No events were ever seen, but the generator still closed on its own.
    assert chunks == []


def test_backstop_drains_queued_events_before_closing() -> None:
    """Non-terminal events sitting in the queue when the backstop fires are
    still delivered to the client -- the backstop only skips waiting for the
    (missing) terminal event, it doesn't drop already-emitted events.
    """
    bus = EventBus()

    async def run() -> list[str]:
        chunks: list[str] = []
        stream = sse_stream(
            bus,
            history=lambda: [],
            is_terminal=lambda: True,
        )
        gen = stream.__aiter__()

        async def pump_one_event() -> None:
            # Give the generator a moment to start polling, then emit a
            # non-terminal event straight onto the live queue so it's
            # present when the backstop drains on the next Empty timeout.
            await asyncio.sleep(_POLL_TIMEOUT_SECONDS / 2)
            bus.emit(Event(kind=EventKind.STAGE_STARTED, payload={"stage": "x"}))

        pump_task = asyncio.create_task(pump_one_event())
        try:
            async for chunk in gen:
                chunks.append(chunk)
        finally:
            await pump_task
        return chunks

    timeout = max(2.0, _POLL_TIMEOUT_SECONDS * 6)
    chunks = asyncio.run(asyncio.wait_for(run(), timeout=timeout))

    assert len(chunks) == 1
    assert "stage_started" in chunks[0]
