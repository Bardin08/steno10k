from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions

# Canonical stage order = StageName declaration order.
_ORDER: list[StageName] = list(StageName)


def in_run_scope(name: StageName, opts: RunOptions) -> bool:
    """Whether `name` is in scope for this run given the run options.

    `only` wins over everything (single-stage run). Otherwise `from_stage`
    selects that stage and every later stage in canonical order. With neither
    set, every stage is in scope. (Config `stages.enabled` and its cascade are
    resolved separately by the generic `run_set` before `enabled` is called.)
    """
    if opts.only is not None:
        return name == opts.only
    if opts.from_stage is not None:
        return _ORDER.index(name) >= _ORDER.index(opts.from_stage)
    return True
