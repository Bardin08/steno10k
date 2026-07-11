from __future__ import annotations

from pathlib import Path

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.prompts import load_prompts
from steno10k.stages._pool import run_pool
from steno10k.stages._prompts import resolve_override_dir


class CleanStage:
    """LLM-cleans each raw chunk transcript into a Markdown clean transcript."""

    name = StageName.CLEAN
    depends_on = [StageName.TRANSCRIBE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return cfg.llm.enabled and not opts.skip_llm

    def run(self, ctx: StageContext) -> StageResult:
        if ctx.llm is None:
            return StageResult(StageStatus.SKIPPED, message="no LLM client")

        system = load_prompts(resolve_override_dir(ctx.cfg, ctx.set_dir)).clean

        targets: list[tuple[Path, Path]] = []  # (raw_txt, clean_md)
        skipped = 0
        for rec in ctx.manifest.recordings:
            stem = Path(rec.normalized_name).stem
            raw_dir = ctx.set_dir / "transcripts_raw" / stem
            if not raw_dir.is_dir():
                continue
            for raw in sorted(raw_dir.glob("chunk_*.txt")):
                clean_md = ctx.set_dir / "transcripts_clean" / stem / f"{raw.stem}.md"
                if clean_md.exists() and not ctx.force:
                    skipped += 1
                    continue
                targets.append((raw, clean_md))

        llm = ctx.llm

        def _do(item: tuple[Path, Path]) -> str:
            raw, _dst = item
            text = raw.read_text(encoding="utf-8").strip()
            if not text:
                return ""
            return llm.complete(system, text)

        cleaned = 0
        failed = 0
        for (raw, dst), result, err in run_pool(targets, _do, ctx.cfg.llm.concurrency):
            if err is not None:
                ctx.errors.log("clean", str(raw), err)
                failed += 1
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(result or "", encoding="utf-8")
            cleaned += 1

        return StageResult(
            StageStatus.OK,
            stats={"cleaned": cleaned, "skipped": skipped, "failed": failed},
        )
