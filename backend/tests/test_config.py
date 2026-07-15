from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName


def test_defaults_are_small_model_and_english() -> None:
    cfg = Config()
    assert cfg.transcription.model == "small"
    assert cfg.transcription.language == "en"
    assert cfg.prompts.language == "en"
    assert cfg.output.summary_filename == "summary.md"


def test_partial_override_keeps_other_defaults() -> None:
    cfg = Config.model_validate({"transcription": {"model": "large-v3"}})
    assert cfg.transcription.model == "large-v3"
    assert cfg.audio.chunk_seconds == 600


def test_stage_flags_default_enabled() -> None:
    cfg = Config()
    assert cfg.stages.enabled[StageName.TRANSCRIBE] is True
    assert set(cfg.stages.enabled) == set(StageName)


def test_partial_stage_map_is_completed_to_full_set() -> None:
    # A config that lists only some stages must still carry the full stage set,
    # with the omitted stages defaulting to enabled. Otherwise `run_set`
    # (missing => enabled) and `ConfigService.resolve` (missing => disabled)
    # disagree and a run executes more stages than the API reports (issue #39).
    cfg = Config.model_validate({"stages": {"enabled": {"normalize": True, "chunk": True}}})
    assert set(cfg.stages.enabled) == set(StageName)
    assert cfg.stages.enabled[StageName.TRANSCRIBE] is True
    assert cfg.stages.enabled[StageName.NORMALIZE] is True


def test_partial_stage_map_preserves_explicit_disables() -> None:
    cfg = Config.model_validate({"stages": {"enabled": {"transcribe": False}}})
    assert set(cfg.stages.enabled) == set(StageName)
    assert cfg.stages.enabled[StageName.TRANSCRIBE] is False
    assert cfg.stages.enabled[StageName.NORMALIZE] is True
