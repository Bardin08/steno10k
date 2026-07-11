from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import EventBus
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import Stage, StageContext, StageResult, resolve_enabled
from steno10k.contracts.status import StageStatus

DEPS = {
    StageName.NORMALIZE: [],
    StageName.TRANSCRIBE: [StageName.NORMALIZE],
    StageName.MERGE: [StageName.TRANSCRIBE],
    StageName.SUMMARIZE: [StageName.MERGE],
    StageName.BUNDLE: [StageName.MERGE],
}


def test_all_enabled_stays_enabled() -> None:
    enabled, cascaded = resolve_enabled(DEPS, {k: True for k in DEPS})
    assert enabled == set(DEPS) and cascaded == {}


def test_disable_cascades_to_all_dependents_transitively() -> None:
    flags = {k: True for k in DEPS}
    flags[StageName.TRANSCRIBE] = False
    enabled, cascaded = resolve_enabled(DEPS, flags)
    # transcribe off -> merge off -> summarize AND bundle off
    assert enabled == {StageName.NORMALIZE}
    assert cascaded[StageName.MERGE] == StageName.TRANSCRIBE
    assert StageName.SUMMARIZE in cascaded and StageName.BUNDLE in cascaded


class FakeStage:
    name = StageName.NORMALIZE
    depends_on: list[StageName] = []

    def enabled(self, cfg: Config, opts: object) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        return StageResult(status=StageStatus.OK, stats={"files": 1})


def test_fake_stage_satisfies_protocol(tmp_path: Path) -> None:
    stage: Stage = FakeStage()
    ctx = StageContext(
        set_dir=tmp_path,
        cfg=Config(),
        force=False,
        manifest=Manifest(project_slug="p", set_slug="s", title="S"),
        errors=ErrorLog(tmp_path / "errors.log"),
        events=EventBus(),
        llm=None,
    )
    assert stage.run(ctx).status is StageStatus.OK
