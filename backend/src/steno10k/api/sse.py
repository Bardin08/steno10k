from __future__ import annotations

import asyncio
import json
import queue
from collections.abc import AsyncIterator, Callable

from steno10k.contracts.events import Event, EventBus, EventKind

# F1's `EventKind` has no distinct "run failed" kind: `run_set` (contracts/runner.py)
# emits `RUN_COMPLETED` unconditionally once the stage loop finishes, regardless of
# whether individual stages ended `STAGE_FAILED` -- per-stage failures don't abort
# the run. `RUN_COMPLETED` is therefore the only true run-level terminal event.
_TERMINAL_KINDS = {EventKind.RUN_COMPLETED}

# Bounds how long each poll of the queue blocks before the generator loops
# back around; keeps the loop responsive to client disconnects without
# busy-waiting.
_POLL_TIMEOUT_SECONDS = 0.5


def _format_event(event: Event) -> str:
    payload = dict(event.payload)
    payload["kind"] = str(event.kind)
    return f"event: {event.kind}\ndata: {json.dumps(payload)}\n\n"


async def sse_stream(
    bus: EventBus, history: Callable[[], list[Event]] | None = None
) -> AsyncIterator[str]:
    """Bridge a run's (sync) `EventBus` to an async SSE stream.

    Subscribes a handler that pushes every `Event` onto a thread-safe
    `queue.Queue` -- the bus dispatches from the worker thread, so the
    handoff to this async generator must not touch the event loop directly.
    The generator polls the queue off-thread via `asyncio.to_thread`, which
    avoids blocking the event loop while waiting for the next event, and
    stops once the run's terminal event (`run_completed`) is seen so the
    stream closes deterministically instead of hanging forever.

    `history`, if given, is called *after* subscribing (see below) and
    replays events the run already emitted before this bridge attached --
    without it, a run that finishes fast (an empty `StageRegistry` runs to
    completion essentially instantly) can complete before a client even
    opens the stream, leaving `run_completed` forever unseen by a
    live-only subscriber and the generator polling forever.

    Ordering matters here: `bus.subscribe` happens synchronously below,
    before `history()` is invoked, so no event can be emitted in the gap
    between "start listening live" and "read what already happened" --
    every event is captured by at least one of the two paths. An event
    landing in both (already recorded in history *and* pushed to the live
    queue) is deduplicated by object identity (`id()`), since every
    subscriber -- including `RunQueue`'s own history recorder -- receives
    the exact same `Event` instance from `EventBus.emit`.
    """
    q: queue.Queue[Event] = queue.Queue()
    bus.subscribe(q.put)
    seen: set[int] = set()

    for event in history() if history is not None else []:
        if id(event) in seen:
            continue
        seen.add(id(event))
        yield _format_event(event)
        if event.kind in _TERMINAL_KINDS:
            return

    while True:
        try:
            event = await asyncio.to_thread(q.get, timeout=_POLL_TIMEOUT_SECONDS)
        except queue.Empty:
            continue

        if id(event) in seen:
            continue
        seen.add(id(event))

        yield _format_event(event)

        if event.kind in _TERMINAL_KINDS:
            return
