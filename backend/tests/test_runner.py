from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import EventBus, EventKind
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.runner import run_set
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


@dataclass
class _S:
    name: StageName
    status: StageStatus
    depends_on: list[StageName] = field(default_factory=list)

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        return StageResult(status=self.status)


def _stage(name: StageName, deps: list[StageName], status: StageStatus) -> _S:
    return _S(name=name, status=status, depends_on=deps)


def test_runner_records_status_and_emits(tmp_path: Path) -> None:
    reg = StageRegistry([_stage(StageName.NORMALIZE, [], StageStatus.OK)])
    manifest = Manifest(project_slug="p", set_slug="s", title="S")
    bus = EventBus()
    kinds: list[EventKind] = []
    bus.subscribe(lambda e: kinds.append(e.kind))
    ctx = StageContext(
        set_dir=tmp_path,
        cfg=Config(),
        force=False,
        manifest=manifest,
        errors=ErrorLog(tmp_path / "errors.log"),
        events=bus,
        llm=None,
    )
    run_set(reg, ctx, RunOptions())

    assert manifest.stages[StageName.NORMALIZE] is StageStatus.OK
    assert {EventKind.RUN_STARTED, EventKind.STAGE_COMPLETED, EventKind.RUN_COMPLETED} <= set(kinds)


def test_runner_emits_stage_skipped_for_skipped_status(tmp_path: Path) -> None:
    reg = StageRegistry([_stage(StageName.NORMALIZE, [], StageStatus.SKIPPED)])
    manifest = Manifest(project_slug="p", set_slug="s", title="S")
    bus = EventBus()
    kinds: list[EventKind] = []
    bus.subscribe(lambda e: kinds.append(e.kind))
    ctx = StageContext(
        set_dir=tmp_path,
        cfg=Config(),
        force=False,
        manifest=manifest,
        errors=ErrorLog(tmp_path / "errors.log"),
        events=bus,
        llm=None,
    )
    run_set(reg, ctx, RunOptions())

    assert manifest.stages[StageName.NORMALIZE] is StageStatus.SKIPPED
    assert EventKind.STAGE_SKIPPED in kinds
    assert EventKind.STAGE_FAILED not in kinds


def test_runner_emits_stage_failed_for_failed_status(tmp_path: Path) -> None:
    reg = StageRegistry([_stage(StageName.NORMALIZE, [], StageStatus.FAILED)])
    manifest = Manifest(project_slug="p", set_slug="s", title="S")
    bus = EventBus()
    kinds: list[EventKind] = []
    bus.subscribe(lambda e: kinds.append(e.kind))
    ctx = StageContext(
        set_dir=tmp_path,
        cfg=Config(),
        force=False,
        manifest=manifest,
        errors=ErrorLog(tmp_path / "errors.log"),
        events=bus,
        llm=None,
    )
    run_set(reg, ctx, RunOptions())

    assert EventKind.STAGE_FAILED in kinds
    assert EventKind.STAGE_SKIPPED not in kinds
