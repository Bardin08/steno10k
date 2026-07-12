from __future__ import annotations

from pathlib import Path

import pytest

import steno10k.api.runq as runq_mod
from steno10k.api.configsvc import ConfigService
from steno10k.api.runq import RunQueue
from steno10k.api.storage import Storage
from steno10k.contracts.registry import StageRegistry


def _queue(tmp_path: Path) -> RunQueue:
    storage = Storage(tmp_path)
    storage.create_project("Law")
    storage.create_set("law", "Week 1")
    return RunQueue(
        storage=storage,
        registry=StageRegistry([]),
        config_service=ConfigService(tmp_path / "config.yaml"),
    )


def test_enqueue_records_memory_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runq_mod, "memory_warning", lambda cfg: "would OOM")
    run = _queue(tmp_path).enqueue(project="law", set_="week-1")
    assert run.stats.get("warnings") == ["would OOM"]


def test_enqueue_no_warning_leaves_stats_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runq_mod, "memory_warning", lambda cfg: None)
    run = _queue(tmp_path).enqueue(project="law", set_="week-1")
    assert "warnings" not in run.stats
