from __future__ import annotations

from steno10k.api.stages import build_registry
from steno10k.contracts.names import StageName


def test_build_registry_has_all_eight_stages_in_canonical_order() -> None:
    reg = build_registry()
    assert reg.names == [
        StageName.NORMALIZE,
        StageName.CHUNK,
        StageName.TRANSCRIBE,
        StageName.CLEAN,
        StageName.MERGE,
        StageName.SUMMARIZE,
        StageName.BUNDLE,
        StageName.NOTIFY,
    ]


def test_build_registry_deps_match_declared_graph() -> None:
    # StageRegistry() would raise on construction if any depends_on edge pointed
    # forward; this asserts the concrete stages' declared deps survive validation.
    reg = build_registry()
    deps = reg.deps()
    assert deps[StageName.CHUNK] == [StageName.NORMALIZE]
    assert deps[StageName.SUMMARIZE] == [StageName.MERGE, StageName.CLEAN]
    assert deps[StageName.NORMALIZE] == []
