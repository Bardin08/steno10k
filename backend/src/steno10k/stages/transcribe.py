from __future__ import annotations

import logging
from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.events import Event, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.transcriber import TranscribeJob, TranscribeSettings, transcribe_chunks
from steno10k.stages._scope import in_run_scope

log = logging.getLogger("steno10k.stages.transcribe")

# F1 froze TranscriptionConfig without these faster-whisper decode knobs; the
# transcribe stage supplies them as M1 defaults per
# docs/adr/0001-defer-llm-and-whisper-config-knobs.md.
_M1_BEAM_SIZE = 5
_M1_VAD_FILTER = True
_M1_MIN_SILENCE_MS = 500


class TranscribeStage:
    """Transcribe each recording's chunks with faster-whisper, in parallel."""

    name = StageName.TRANSCRIBE
    depends_on: list[StageName] = [StageName.CHUNK]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return in_run_scope(self.name, opts)

    def _settings(self, cfg: Config) -> TranscribeSettings:
        t = cfg.transcription
        return TranscribeSettings(
            model=t.model,
            device=t.device,
            compute_type=t.compute_type,
            language=t.language,
            beam_size=_M1_BEAM_SIZE,
            vad_filter=_M1_VAD_FILTER,
            min_silence_duration_ms=_M1_MIN_SILENCE_MS,
            cpu_threads=t.cpu_threads_per_worker,
        )

    def run(self, ctx: StageContext) -> StageResult:
        fmt = ctx.cfg.audio.output_format
        settings = self._settings(ctx.cfg)
        max_workers = ctx.cfg.transcription.max_workers
        recordings = ctx.manifest.recordings
        total = len(recordings)
        processed = 0
        failed = 0
        for i, rec in enumerate(recordings):
            stem = Path(rec.normalized_name).stem
            chunk_dir = ctx.set_dir / "chunks" / stem
            jobs: list[TranscribeJob] = []
            if chunk_dir.is_dir():
                for chunk_path in sorted(chunk_dir.glob(f"*.{fmt}")):
                    out = ctx.set_dir / "transcripts_raw" / stem / f"{chunk_path.stem}.txt"
                    if out.exists() and not ctx.force:
                        continue
                    jobs.append(TranscribeJob(chunk_path=chunk_path, output_path=out))
            if jobs:
                for out_path, err in transcribe_chunks(jobs, settings, max_workers):
                    processed += 1
                    if err is not None:
                        failed += 1
                        ctx.errors.log("transcribe", out_path.name, err)
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
            status=StageStatus.OK,
            stats={"chunks": processed, "transcribed": processed - failed, "failed": failed},
        )
