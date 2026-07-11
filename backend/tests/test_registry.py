from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


@dataclass
class _S:
    name: StageName
    depends_on: list[StageName] = field(default_factory=list)

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        return StageResult(status=StageStatus.OK)


def _mk(name: StageName, deps: list[StageName]) -> _S:
    return _S(name=name, depends_on=deps)


def test_registry_preserves_order() -> None:
    reg = StageRegistry(
        [_mk(StageName.NORMALIZE, []), _mk(StageName.TRANSCRIBE, [StageName.NORMALIZE])]
    )
    assert reg.names == [StageName.NORMALIZE, StageName.TRANSCRIBE]


def test_registry_rejects_unknown_dependency() -> None:
    with pytest.raises(ValueError, match="unknown dependency"):
        StageRegistry([_mk(StageName.TRANSCRIBE, [StageName.NORMALIZE])])


def test_registry_rejects_forward_dependency() -> None:
    with pytest.raises(ValueError, match="after"):
        StageRegistry(
            [_mk(StageName.NORMALIZE, [StageName.TRANSCRIBE]), _mk(StageName.TRANSCRIBE, [])]
        )
