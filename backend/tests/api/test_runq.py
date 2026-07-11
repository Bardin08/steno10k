from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

from steno10k.api.runq import RunQueue, RunStatus
from steno10k.api.storage import Storage
from steno10k.contracts.registry import StageRegistry


def _wait(pred: Callable[[], bool], timeout: float = 2.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return
        time.sleep(0.02)
    raise AssertionError("timeout")


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
