from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.stage import RunOptions
from steno10k.stages._scope import in_run_scope


def test_default_all_in_scope() -> None:
    assert in_run_scope(StageName.CHUNK, RunOptions()) is True


def test_only_matches_single_stage() -> None:
    opts = RunOptions(only=StageName.CHUNK)
    assert in_run_scope(StageName.CHUNK, opts) is True
    assert in_run_scope(StageName.TRANSCRIBE, opts) is False


def test_from_stage_includes_self_and_later() -> None:
    opts = RunOptions(from_stage=StageName.CHUNK)
    assert in_run_scope(StageName.NORMALIZE, opts) is False
    assert in_run_scope(StageName.CHUNK, opts) is True
    assert in_run_scope(StageName.TRANSCRIBE, opts) is True


def test_only_takes_precedence_over_from_stage() -> None:
    opts = RunOptions(only=StageName.NORMALIZE, from_stage=StageName.TRANSCRIBE)
    assert in_run_scope(StageName.NORMALIZE, opts) is True
    assert in_run_scope(StageName.TRANSCRIBE, opts) is False
