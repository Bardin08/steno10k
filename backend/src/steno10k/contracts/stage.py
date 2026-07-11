from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from steno10k.contracts.config import Config
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import EventEmitter
from steno10k.contracts.llm import LLMClient
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.names import StageName
from steno10k.contracts.status import StageStatus


@dataclass
class RunOptions:
    force: bool = False
    only: StageName | None = None
    from_stage: StageName | None = None
    skip_llm: bool = False


@dataclass
class StageResult:
    status: StageStatus
    stats: dict[str, int] = field(default_factory=dict)
    message: str | None = None


@dataclass
class StageContext:
    set_dir: Path
    cfg: Config
    force: bool
    manifest: Manifest
    errors: ErrorLog
    events: EventEmitter
    llm: LLMClient | None


class Stage(Protocol):
    name: StageName
    depends_on: list[StageName]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool: ...
    def run(self, ctx: StageContext) -> StageResult: ...


def resolve_enabled(
    deps: dict[StageName, list[StageName]], flags: dict[StageName, bool]
) -> tuple[set[StageName], dict[StageName, StageName]]:
    """Effective enabled stages after cascade-disable.

    Iterates to a FIXED POINT, so disabling one stage propagates to every
    transitive dependent (and to multiple dependents), not just the first.
    Returns (enabled, cascaded) where `cascaded` maps each forced-off stage to
    the disabled dependency that first caused it.
    """
    enabled = {name for name, on in flags.items() if on}
    cascaded: dict[StageName, StageName] = {}
    changed = True
    while changed:
        changed = False
        for name in list(enabled):
            for dep in deps.get(name, []):
                if dep not in enabled:
                    enabled.discard(name)
                    cascaded.setdefault(name, dep)
                    changed = True
                    break
    return enabled, cascaded
