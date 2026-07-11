from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry

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

    Empty/stub for F2: no concrete `Stage` implementations exist yet.
    Real stages register here during fan-out (one module per stage under
    `api/`, imported and appended to this list) — the run worker is already
    wired to execute whatever this returns.
    """
    return StageRegistry([])
