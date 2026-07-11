from __future__ import annotations

import logging
from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.ffmpeg import extract_chunk, get_duration_seconds, plan_chunks
from steno10k.stages._scope import in_run_scope

log = logging.getLogger("steno10k.stages.chunk")


class ChunkStage:
    """Split each recording into overlapping chunks under `chunks/<stem>/`."""

    name = StageName.CHUNK
    depends_on: list[StageName] = [StageName.NORMALIZE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return in_run_scope(self.name, opts)

    def run(self, ctx: StageContext) -> StageResult:
        audio = ctx.cfg.audio
        recordings = ctx.manifest.recordings
        total = len(recordings)
        chunk_total = 0
        for i, rec in enumerate(recordings):
            try:
                src = ctx.set_dir / rec.normalized_name
                if not src.is_file():
                    raise FileNotFoundError(f"source file missing: {rec.normalized_name}")
                duration = rec.duration_seconds
                if duration is None:
                    duration = get_duration_seconds(src)
                windows = plan_chunks(
                    duration,
                    audio.chunk_seconds,
                    audio.overlap_seconds,
                    audio.min_chunk_seconds,
                )
                stem = Path(rec.normalized_name).stem
                chunk_dir = ctx.set_dir / "chunks" / stem
                rel_paths: list[str] = []
                for idx, (start, end) in enumerate(windows):
                    dst = chunk_dir / f"chunk_{idx:03d}.{audio.output_format}"
                    if ctx.force or not dst.exists():
                        extract_chunk(src, dst, start, end, audio.output_format)
                    rel_paths.append(str(dst.relative_to(ctx.set_dir)))
                    chunk_total += 1
                rec.chunks = rel_paths
            except Exception as exc:  # per-recording isolation
                ctx.errors.log("chunk", rec.normalized_name, exc)
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
        return StageResult(
            status=StageStatus.OK, stats={"recordings": total, "chunks": chunk_total}
        )
