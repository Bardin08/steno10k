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


def _started_stages(reg: StageRegistry, cfg: Config) -> list[StageName]:
    """Run `run_set` over `cfg` and return the stages that actually started."""
    manifest = Manifest(project_slug="p", set_slug="s", title="S")
    started: list[StageName] = []
    bus = EventBus()
    bus.subscribe(
        lambda e: started.append(e.payload["stage"]) if e.kind is EventKind.STAGE_STARTED else None
    )
    tmp = Path(str(manifest.set_slug))  # unused dir; stages here are fakes
    ctx = StageContext(
        set_dir=tmp,
        cfg=cfg,
        force=False,
        manifest=manifest,
        errors=ErrorLog(tmp / "errors.log"),
        events=bus,
        llm=None,
    )
    run_set(reg, ctx, RunOptions())
    return started


def test_run_set_skips_config_disabled_stage_and_dependents() -> None:
    reg = StageRegistry(
        [
            _stage(StageName.NORMALIZE, [], StageStatus.OK),
            _stage(StageName.TRANSCRIBE, [StageName.NORMALIZE], StageStatus.OK),
            _stage(StageName.MERGE, [StageName.TRANSCRIBE], StageStatus.OK),
        ]
    )
    cfg = Config.model_validate({"stages": {"enabled": {"transcribe": False}}})
    started = _started_stages(reg, cfg)
    # transcribe disabled -> transcribe skipped, and merge cascades off too
    assert started == [StageName.NORMALIZE]


def test_run_set_treats_omitted_stage_as_enabled() -> None:
    # A config that lists only `normalize` (transcribe/merge omitted) still runs
    # every stage: omission means enabled, matching the API's completed view of
    # the map. This is the semantic complement of the skip test above (issue #39).
    reg = StageRegistry(
        [
            _stage(StageName.NORMALIZE, [], StageStatus.OK),
            _stage(StageName.TRANSCRIBE, [StageName.NORMALIZE], StageStatus.OK),
            _stage(StageName.MERGE, [StageName.TRANSCRIBE], StageStatus.OK),
        ]
    )
    cfg = Config.model_validate({"stages": {"enabled": {"normalize": True}}})
    started = _started_stages(reg, cfg)
    assert set(started) == {StageName.NORMALIZE, StageName.TRANSCRIBE, StageName.MERGE}


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
