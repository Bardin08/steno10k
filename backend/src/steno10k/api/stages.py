from __future__ import annotations

from steno10k.contracts.names import StageName

# Canonical stage dependency graph. Used now by the config cascade (api/routers/config.py
# resolves which stages get cascaded off when a dependency is disabled). Task 9 adds
# `build_registry()` to this same module to assemble the concrete `StageRegistry` once
# stage implementations exist (F2 ships with a stub/empty registry).
STAGE_DEPS: dict[StageName, list[StageName]] = {
    StageName.NORMALIZE: [],
    StageName.CHUNK: [StageName.NORMALIZE],
    StageName.TRANSCRIBE: [StageName.CHUNK],
    StageName.CLEAN: [StageName.TRANSCRIBE],
    StageName.MERGE: [StageName.TRANSCRIBE],
    StageName.SUMMARIZE: [StageName.MERGE],
    StageName.BUNDLE: [StageName.MERGE],
    StageName.NOTIFY: [StageName.BUNDLE],
}
