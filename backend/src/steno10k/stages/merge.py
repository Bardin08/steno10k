from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


class MergeStage:
    """Concatenates per-recording chunk transcripts into single Markdown files."""

    name = StageName.MERGE
    depends_on = [StageName.TRANSCRIBE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        stems = [Path(r.normalized_name).stem for r in ctx.manifest.recordings]
        merged_dir = ctx.set_dir / "merged"

        wrote_raw = 0
        wrote_clean = 0
        if ctx.cfg.output.save_merged_raw_transcript:
            wrote_raw = int(
                self._merge(
                    ctx, stems, "transcripts_raw", "chunk_*.txt", merged_dir / "raw_transcript.md"
                )
            )
        if ctx.cfg.output.save_merged_clean_transcript:
            wrote_clean = int(
                self._merge(
                    ctx,
                    stems,
                    "transcripts_clean",
                    "chunk_*.md",
                    merged_dir / "clean_transcript.md",
                )
            )
        return StageResult(StageStatus.OK, stats={"raw": wrote_raw, "clean": wrote_clean})

    def _merge(
        self, ctx: StageContext, stems: list[str], subdir: str, glob: str, dst: Path
    ) -> bool:
        parts: list[str] = []
        for stem in stems:
            d = ctx.set_dir / subdir / stem
            if not d.is_dir():
                continue
            files = sorted(d.glob(glob))
            if not files:
                continue
            chunk_parts: list[str] = []
            for f in files:
                try:
                    body = f.read_text(encoding="utf-8").strip()
                except (OSError, UnicodeDecodeError) as e:
                    ctx.errors.log("merge", str(f), e)
                    continue
                chunk_parts.append(f"\n### {f.stem}\n")
                chunk_parts.append(body)
            if not chunk_parts:
                continue  # every chunk for this stem failed to read
            parts.append(f"\n\n## {stem}\n")
            parts.extend(chunk_parts)
        if not parts:
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
        return True
