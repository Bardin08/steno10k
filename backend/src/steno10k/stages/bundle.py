from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus
from steno10k.lib.docx import build_bundle


class BundleStage:
    """Renders the merged clean transcript and the summary to `.docx` files."""

    name = StageName.BUNDLE
    depends_on = [StageName.MERGE]

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return cfg.output.save_bundle_docx

    def run(self, ctx: StageContext) -> StageResult:
        bundle_dir = ctx.set_dir / "bundle"
        pairs = [
            (ctx.set_dir / "merged" / "clean_transcript.md", bundle_dir / "transcript.docx"),
            (ctx.set_dir / ctx.cfg.output.summary_filename, bundle_dir / "summary.docx"),
        ]

        before = ctx.errors.count
        build_bundle(pairs, ctx.force, ctx.errors)
        built = sum(1 for _src, dst in pairs if dst.is_file())

        if ctx.errors.count > before:
            return StageResult(
                StageStatus.FAILED,
                stats={"built": built},
                message="one or more bundle files failed",
            )
        return StageResult(StageStatus.OK, stats={"built": built})
