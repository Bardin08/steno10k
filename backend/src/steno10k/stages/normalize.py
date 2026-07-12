from __future__ import annotations

import logging

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.ffmpeg import (
    FFmpegError,
    ensure_ffmpeg_available,
    get_duration_seconds,
)
from steno10k.stages._scope import in_run_scope

log = logging.getLogger("steno10k.stages.normalize")


class NormalizeStage:
    """Validate uploaded recordings and probe their durations.

    Upload already slug-names source audio into `set_dir/<normalized_name>`
    (see api/routers/recordings.py), so there is no copy/rename step. This stage
    fails fast if ffmpeg is unavailable, then records each recording's duration
    on the manifest (feeding the recordings table and the chunk stage).
    """

    name = StageName.NORMALIZE
    depends_on: list[StageName] = []

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return in_run_scope(self.name, opts)

    def run(self, ctx: StageContext) -> StageResult:
        try:
            ensure_ffmpeg_available()
        except FFmpegError as exc:
            ctx.errors.log("normalize", "ffmpeg", exc)
            return StageResult(status=StageStatus.FAILED, message=str(exc))

        recordings = ctx.manifest.recordings
        total = len(recordings)
        probed = 0
        for i, rec in enumerate(recordings):
            src = ctx.set_dir / rec.normalized_name
            if not src.is_file():
                ctx.errors.log("normalize", rec.normalized_name, "source file missing")
            else:
                try:
                    rec.duration_seconds = get_duration_seconds(src)
                    probed += 1
                except Exception as exc:  # per-recording isolation
                    ctx.errors.log("normalize", rec.normalized_name, exc)
            ctx.events.emit(
                Event(
                    kind=EventKind.STAGE_PROGRESS,
                    payload={
                        "stage": self.name,
                        "progress": (i + 1) / total if total else 1.0,
                        "current": i + 1,
                        "total": total,
                    },
                )
            )
        return StageResult(status=StageStatus.OK, stats={"recordings": probed})
