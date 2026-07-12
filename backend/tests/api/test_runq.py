from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from steno10k.api.runq import RunQueue, RunStatus
from steno10k.api.storage import Storage
from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


def _wait(pred: Callable[[], bool], timeout: float = 2.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return
        time.sleep(0.02)
    raise AssertionError("timeout")


@dataclass
class _RaisingOnceStage:
    """Minimal F1 `Stage` protocol implementation whose `run()` raises on its
    first invocation only, then succeeds -- lets a test prove the worker
    thread survives a failure and keeps processing later runs."""

    name: StageName = StageName.NORMALIZE
    depends_on: list[StageName] = field(default_factory=list)
    _calls: int = 0

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("boom")
        return StageResult(status=StageStatus.OK)


@dataclass
class _SlowRaisingStage:
    """Like `_RaisingOnceStage`, but sleeps briefly first so a test can
    observe the run in RUNNING state before it fails."""

    delay: float
    name: StageName = StageName.NORMALIZE
    depends_on: list[StageName] = field(default_factory=list)

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        time.sleep(self.delay)
        raise RuntimeError("boom")


def test_runs_process_sequentially(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    # empty registry: run completes trivially
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    q.start()
    try:
        run = q.enqueue(project="law", set_="week-1")
        _wait(lambda: q.get(run.id).status == RunStatus.COMPLETED)
        assert q.get(run.id).status == RunStatus.COMPLETED
    finally:
        q.stop()


def test_multiple_runs_process_in_order(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    storage.create_set("law", "Week 2")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    q.start()
    try:
        run1 = q.enqueue(project="law", set_="week-1")
        run2 = q.enqueue(project="law", set_="week-2")
        _wait(lambda: q.get(run2.id).status == RunStatus.COMPLETED)
        assert q.get(run1.id).status == RunStatus.COMPLETED
        assert q.get(run2.id).status == RunStatus.COMPLETED
        ids = {r.id for r in q.list()}
        assert ids == {run1.id, run2.id}
    finally:
        q.stop()


def test_get_missing_run_raises(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    with pytest.raises(KeyError):
        q.get("nope")


def test_cancel_queued_run(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    storage.create_set("law", "Week 2")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    # Do not start the worker: both runs stay queued so we can cancel deterministically.
    run1 = q.enqueue(project="law", set_="week-1")
    run2 = q.enqueue(project="law", set_="week-2")
    assert q.cancel(run2.id) is True
    assert q.get(run2.id).status == RunStatus.CANCELLED

    q.start()
    try:
        _wait(lambda: q.get(run1.id).status == RunStatus.COMPLETED)
        assert q.get(run1.id).status == RunStatus.COMPLETED
        # cancelled run must never flip to completed once the worker drains it
        assert q.get(run2.id).status == RunStatus.CANCELLED
    finally:
        q.stop()


def test_cancel_unknown_run_returns_false(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    assert q.cancel("nope") is False


def test_start_stop_lifecycle_is_idempotent(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    q.start()
    q.start()  # idempotent: does not spawn a second worker
    try:
        run = q.enqueue(project="law", set_="week-1")
        _wait(lambda: q.get(run.id).status == RunStatus.COMPLETED)
    finally:
        q.stop()
        q.stop()  # idempotent: safe to call twice


def test_run_bus_accessible_for_sse_bridge(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    run = q.enqueue(project="law", set_="week-1")
    bus = q.get_bus(run.id)
    assert bus is not None
    received = []
    bus.subscribe(lambda event: received.append(event))

    q.start()
    try:
        _wait(lambda: q.get(run.id).status == RunStatus.COMPLETED)
        _wait(lambda: len(received) > 0)
        kinds = {e.kind for e in received}
        assert "run_started" in kinds and "run_completed" in kinds
        # events are also captured on the run snapshot itself
        assert len(q.get(run.id).events) > 0
    finally:
        q.stop()


def test_worker_survives_failed_run_and_processes_next(tmp_path: Path) -> None:
    """Task 9's failure isolation: a run whose stage raises must end FAILED,
    and the worker thread must keep processing subsequent runs afterwards."""
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    storage.create_set("law", "Week 2")
    q = RunQueue(storage=storage, registry=StageRegistry([_RaisingOnceStage()]))
    q.start()
    try:
        run1 = q.enqueue(project="law", set_="week-1")
        run2 = q.enqueue(project="law", set_="week-2")
        _wait(lambda: q.get(run1.id).status == RunStatus.FAILED)
        assert q.get(run1.id).status == RunStatus.FAILED
        assert "error" in q.get(run1.id).stats

        # the worker thread must still be alive and keep draining the queue
        # after the first run's exception.
        _wait(lambda: q.get(run2.id).status == RunStatus.COMPLETED)
        assert q.get(run2.id).status == RunStatus.COMPLETED
    finally:
        q.stop()


def test_cancel_during_running_then_exception_stays_cancelled(tmp_path: Path) -> None:
    """Regression test: cancelling a run that is RUNNING and later raises
    must not clobber the CANCELLED status with FAILED."""
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    q = RunQueue(storage=storage, registry=StageRegistry([_SlowRaisingStage(delay=0.2)]))
    q.start()
    try:
        run = q.enqueue(project="law", set_="week-1")
        _wait(lambda: q.get(run.id).status == RunStatus.RUNNING)
        assert q.cancel(run.id) is True
        _wait(lambda: q.get(run.id).status != RunStatus.RUNNING, timeout=3.0)
        assert q.get(run.id).status == RunStatus.CANCELLED
    finally:
        q.stop()


def test_enqueue_defaults_force_false(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    run = q.enqueue(project="law", set_="week-1")
    assert run.force is False
    assert q.get(run.id).force is False


def test_enqueue_records_force_true(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    q = RunQueue(storage=storage, registry=StageRegistry([]))
    run = q.enqueue(project="law", set_="week-1", force=True)
    assert run.force is True
    assert q.get(run.id).force is True  # survives _snapshot round-trip


@dataclass
class _ForceRecordingStage:
    """Records the `ctx.force` value seen at run time so a test can assert
    the queue threaded the per-run force flag into the StageContext."""

    seen: list[bool] = field(default_factory=list)
    name: StageName = StageName.NORMALIZE
    depends_on: list[StageName] = field(default_factory=list)

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        self.seen.append(ctx.force)
        return StageResult(status=StageStatus.OK)


def test_force_threads_into_stage_context(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    stage = _ForceRecordingStage()
    q = RunQueue(storage=storage, registry=StageRegistry([stage]))
    q.start()
    try:
        run = q.enqueue(project="law", set_="week-1", force=True)
        _wait(lambda: q.get(run.id).status == RunStatus.COMPLETED)
        assert stage.seen == [True]
    finally:
        q.stop()
