from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.prompts import load_prompts
from steno10k.stages._prompts import resolve_override_dir


class SummarizeStage:
    """Produces the summary document from the merged clean transcript via the LLM."""

    name = StageName.SUMMARIZE
    depends_on = [StageName.MERGE, StageName.CLEAN]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return cfg.llm.enabled and not opts.skip_llm

    def run(self, ctx: StageContext) -> StageResult:
        if ctx.llm is None:
            return StageResult(StageStatus.SKIPPED, message="no LLM client")

        dst = ctx.set_dir / ctx.cfg.output.summary_filename
        if dst.exists() and not ctx.force:
            return StageResult(StageStatus.OK, stats={"skipped": 1})

        transcript_path = ctx.set_dir / "merged" / "clean_transcript.md"
        if not transcript_path.is_file():
            ctx.errors.log("summarize", ctx.manifest.set_slug, "merged/clean_transcript.md missing")
            return StageResult(StageStatus.FAILED, message="clean transcript missing")
        transcript = transcript_path.read_text(encoding="utf-8").strip()
        if not transcript:
            ctx.errors.log("summarize", ctx.manifest.set_slug, "clean transcript empty")
            return StageResult(StageStatus.FAILED, message="clean transcript empty")

        prompts = load_prompts(resolve_override_dir(ctx.cfg, ctx.set_dir))
        system = prompts.summarize.format(
            target_output_language=ctx.cfg.prompts.target_output_language
        )
        summary = ctx.llm.complete(system, transcript)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(summary + "\n", encoding="utf-8")
        return StageResult(StageStatus.OK, stats={"chars": len(summary)})
