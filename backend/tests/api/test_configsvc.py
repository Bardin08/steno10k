from __future__ import annotations

from pathlib import Path

from steno10k.api.configsvc import ConfigService
from steno10k.contracts.names import StageName


def test_load_defaults_when_no_file(tmp_path: Path) -> None:
    svc = ConfigService(tmp_path / "config.yaml")
    cfg = svc.load()
    assert cfg.transcription.model == "small"


def test_file_overrides_defaults(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text("transcription:\n  model: medium\n", encoding="utf-8")
    assert ConfigService(p).load().transcription.model == "medium"


def test_save_then_load_roundtrips(tmp_path: Path) -> None:
    svc = ConfigService(tmp_path / "config.yaml")
    cfg = svc.load()
    cfg.output.summary_filename = "notes.md"
    svc.save(cfg)
    assert svc.load().output.summary_filename == "notes.md"


def test_cascade_resolution(tmp_path: Path) -> None:
    svc = ConfigService(tmp_path / "config.yaml")
    cfg = svc.load()
    cfg.stages.enabled[StageName.MERGE] = False
    deps = {StageName.MERGE: [], StageName.SUMMARIZE: [StageName.MERGE]}
    enabled, cascaded = svc.resolve(cfg, deps)
    assert StageName.SUMMARIZE not in enabled
    assert cascaded[StageName.SUMMARIZE] == StageName.MERGE
