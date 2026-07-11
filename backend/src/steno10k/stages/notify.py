from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


class NotifyStage:
    """Terminal emit-only stage: announces the produced artifacts as an event.

    No external sink (Telegram is deferred to M3+). Subscribers (SSE bridge, future
    Telegram) read the emitted `STAGE_PROGRESS` event's `artifacts` payload.
    """

    name = StageName.NOTIFY
    depends_on = [StageName.BUNDLE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        candidates = [
            ctx.set_dir / "merged" / "raw_transcript.md",
            ctx.set_dir / "merged" / "clean_transcript.md",
            ctx.set_dir / ctx.cfg.output.summary_filename,
            ctx.set_dir / "bundle" / "transcript.docx",
            ctx.set_dir / "bundle" / "summary.docx",
        ]
        artifacts = [p.relative_to(ctx.set_dir).as_posix() for p in candidates if p.is_file()]
        payload = {"stage": "notify", "artifacts": artifacts}
        ctx.events.emit(Event(kind=EventKind.STAGE_PROGRESS, payload=payload))
        return StageResult(StageStatus.OK, stats={"artifacts": len(artifacts)})
