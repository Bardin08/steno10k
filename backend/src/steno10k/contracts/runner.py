from __future__ import annotations

from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.stage import RunOptions, StageContext
from steno10k.contracts.status import StageStatus


def run_set(reg: StageRegistry, ctx: StageContext, opts: RunOptions) -> None:
    """Generic loop: for each active stage, run it, record status, emit events."""
    ctx.events.emit(Event(kind=EventKind.RUN_STARTED, payload={"set": ctx.manifest.set_slug}))
    flags = {name: ctx.cfg.stages.enabled.get(name, True) for name in reg.names}
    active, _cascaded = reg.resolve_enabled(flags)

    for stage in reg.stages:
        if stage.name not in active or not stage.enabled(ctx.cfg, opts):
            ctx.manifest.stages[stage.name] = StageStatus.SKIPPED
            continue
        ctx.events.emit(Event(kind=EventKind.STAGE_STARTED, payload={"stage": stage.name}))
        result = stage.run(ctx)
        ctx.manifest.stages[stage.name] = result.status
        if result.status is StageStatus.OK:
            kind = EventKind.STAGE_COMPLETED
        elif result.status is StageStatus.SKIPPED:
            kind = EventKind.STAGE_SKIPPED
        else:
            # FAILED (and defensively PENDING, which is never a valid run() result)
            kind = EventKind.STAGE_FAILED
        ctx.events.emit(Event(kind=kind, payload={"stage": stage.name, "stats": result.stats}))

    ctx.events.emit(Event(kind=EventKind.RUN_COMPLETED, payload={"set": ctx.manifest.set_slug}))
