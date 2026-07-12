from __future__ import annotations

import json
from pathlib import Path

import pytest

from steno10k.cli.app import main


def test_config_show_json_includes_llm_key_present(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["config", "show", "--json", "--data-root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["llm_key_present"] is False
    assert payload["config"]["llm"]["api_key_env"] == "OPENAI_API_KEY"


def test_config_show_reports_present_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    assert main(["config", "show", "--json", "--data-root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["llm_key_present"] is True
