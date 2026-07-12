from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.stages.bundle import BundleStage
from steno10k.stages.chunk import ChunkStage
from steno10k.stages.clean import CleanStage
from steno10k.stages.merge import MergeStage
from steno10k.stages.normalize import NormalizeStage
from steno10k.stages.notify import NotifyStage
from steno10k.stages.summarize import SummarizeStage
from steno10k.stages.transcribe import TranscribeStage

# Canonical stage dependency graph. Used now by the config cascade (api/routers/config.py
# resolves which stages get cascaded off when a dependency is disabled). Task 9 adds
# `build_registry()` to this same module to assemble the concrete `StageRegistry` once
# stage implementations exist (F2 ships with a stub/empty registry).
#
# Edges are hard data-dependencies only: a stage depends on another only when it
# reads that stage's output directly. This deliberately keeps some "downstream"
# stages independent of intermediate ones: a raw-only pipeline (clean disabled) is
# a valid configuration, since merge always produces a raw merged transcript from
# transcribe's output regardless of clean; likewise a transcript-only bundle
# (summarize disabled) is valid, since bundle always renders the transcript .docx
# and only optionally includes a summary .docx. `summarize` does depend on `clean`
# because it consumes the *clean* merged transcript, not the raw one — so
# disabling `clean` must cascade `summarize` off too.
STAGE_DEPS: dict[StageName, list[StageName]] = {
    StageName.NORMALIZE: [],
    StageName.CHUNK: [StageName.NORMALIZE],
    StageName.TRANSCRIBE: [StageName.CHUNK],
    StageName.CLEAN: [StageName.TRANSCRIBE],
    StageName.MERGE: [StageName.TRANSCRIBE],
    StageName.SUMMARIZE: [StageName.MERGE, StageName.CLEAN],
    StageName.BUNDLE: [StageName.MERGE],
    StageName.NOTIFY: [StageName.BUNDLE],
}


def build_registry() -> StageRegistry:
    """Assemble the concrete `StageRegistry` the run queue executes.

    Stages are listed in canonical `StageName` order; `StageRegistry` validates
    that every `depends_on` edge points at an earlier stage.
    """
    return StageRegistry(
        [
            NormalizeStage(),
            ChunkStage(),
            TranscribeStage(),
            CleanStage(),
            MergeStage(),
            SummarizeStage(),
            BundleStage(),
            NotifyStage(),
        ]
    )
