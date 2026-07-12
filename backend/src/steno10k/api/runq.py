from __future__ import annotations

import functools
import logging
import queue
import threading
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from steno10k.api.configsvc import ConfigService
from steno10k.api.storage import Storage
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import Event, EventBus
from steno10k.contracts.ids import new_id
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.runner import run_set
from steno10k.contracts.stage import RunOptions, StageContext

log = logging.getLogger("steno10k.runq")


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Run:
    """A snapshot-friendly record of one enqueued run.

    `events` accumulates every `Event` emitted on this run's `EventBus` (via
    the internal handler `RunQueue` subscribes at enqueue time), so both the
    status snapshot and the SSE bridge (Task 10) can read history without
    racing the worker thread.
    """

    id: str
    project: str
    set_: str
    status: RunStatus = RunStatus.QUEUED
    position: int = 0
    force: bool = False
    stats: dict[str, Any] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)


class RunQueue:
    """Single-worker queue driving F1's `run_set` over enqueued runs.

    Runs are processed strictly one at a time on a dedicated worker thread.
    Each run gets its own `EventBus`, created at `enqueue()` time (not when
    the worker picks it up), so subscribers — including the SSE bridge — can
    attach before the run starts and never miss the `run_started` event.
    """

    def __init__(
        self,
        storage: Storage,
        registry: StageRegistry,
        config_service: ConfigService | None = None,
    ) -> None:
        self._storage = storage
        self._registry = registry
        self._config_service = config_service or ConfigService(storage.data_root / "config.yaml")
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._runs: dict[str, Run] = {}
        self._buses: dict[str, EventBus] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None

    # -- lifecycle -----------------------------------------------------

    def start(self) -> None:
        """Start the background worker. Idempotent."""
        with self._lock:
            if self._worker is not None:
                return
            worker = threading.Thread(target=self._work_loop, name="runq-worker", daemon=True)
            self._worker = worker
        worker.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the background worker and join it. Idempotent."""
        with self._lock:
            worker = self._worker
            self._worker = None
        if worker is None:
            return
        self._queue.put(None)  # sentinel: unblocks the worker's queue.get()
        worker.join(timeout=timeout)

    # -- public API ------------------------------------------------------

    def enqueue(self, project: str, set_: str, *, force: bool = False) -> Run:
        # position is a best-effort snapshot of queue depth at enqueue time;
        # it is never updated afterwards, so it can go stale as other runs
        # complete or are cancelled ahead of this one.
        run = Run(
            id=new_id(),
            project=project,
            set_=set_,
            position=self._queue.qsize(),
            force=force,
        )
        bus = EventBus()
        bus.subscribe(functools.partial(self._record_event, run.id))
        with self._lock:
            self._runs[run.id] = run
            self._buses[run.id] = bus
        self._queue.put(run.id)
        return run

    def cancel(self, run_id: str) -> bool:
        """Cancel a run. Removes it (in effect) if still queued, or flags a
        running one so the worker does not mark it completed once `run_set`
        returns — F1's `run_set` has no cooperative-cancellation hook, so a
        running job still finishes; only its recorded status changes.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.status not in (RunStatus.QUEUED, RunStatus.RUNNING):
                return False
            run.status = RunStatus.CANCELLED
            return True

    def get(self, run_id: str) -> Run:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            return self._snapshot(run)

    def list(self) -> list[Run]:
        with self._lock:
            return [self._snapshot(r) for r in self._runs.values()]

    def get_bus(self, run_id: str) -> EventBus | None:
        """Expose a run's `EventBus` so the SSE bridge can subscribe directly."""
        with self._lock:
            return self._buses.get(run_id)

    # -- internals ---------------------------------------------------------

    def _record_event(self, run_id: str, event: Event) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                run.events.append(event)

    @staticmethod
    def _snapshot(run: Run) -> Run:
        return Run(
            id=run.id,
            project=run.project,
            set_=run.set_,
            status=run.status,
            position=run.position,
            force=run.force,
            stats=dict(run.stats),
            events=list(run.events),
        )

    def _work_loop(self) -> None:
        while True:
            run_id = self._queue.get()
            try:
                if run_id is None:
                    return
                self._process(run_id)
            finally:
                self._queue.task_done()

    def _process(self, run_id: str) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            bus = self._buses.get(run_id)
            if run is None or bus is None:
                return
            if run.status is RunStatus.CANCELLED:
                return  # cancelled while still queued
            run.status = RunStatus.RUNNING

        try:
            manifest = self._storage.load_manifest(run.project, run.set_)
            cfg = self._config_service.load()
            set_dir = self._storage.set_dir(run.project, run.set_)
            errors = ErrorLog(set_dir / "errors.log")
            ctx = StageContext(
                set_dir=set_dir,
                cfg=cfg,
                force=False,
                manifest=manifest,
                errors=errors,
                events=bus,
                llm=None,
            )
            run_set(self._registry, ctx, RunOptions())
            manifest.save(self._storage.manifest_path(run.project, run.set_))
        except Exception as exc:  # isolation boundary: one bad run must not kill the worker
            log.exception("run %s failed", run_id)
            with self._lock:
                if run.status is not RunStatus.CANCELLED:
                    run.status = RunStatus.FAILED
                    run.stats["error"] = str(exc)
            return

        with self._lock:
            if run.status is not RunStatus.CANCELLED:
                run.status = RunStatus.COMPLETED
