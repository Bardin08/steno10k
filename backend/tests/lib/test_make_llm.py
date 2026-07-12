from __future__ import annotations

from steno10k.contracts.config import Config
from steno10k.lib.llm import OpenAICompatibleClient, make_llm


def test_make_llm_returns_none_when_disabled() -> None:
    cfg = Config()
    cfg.llm.enabled = False
    assert make_llm(cfg) is None


def test_make_llm_returns_none_when_key_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    cfg = Config()
    cfg.llm.enabled = True
    cfg.llm.api_key_env = "STENO10K_TEST_MISSING_KEY"
    monkeypatch.delenv("STENO10K_TEST_MISSING_KEY", raising=False)
    assert make_llm(cfg) is None


def test_make_llm_builds_client_when_key_present(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    cfg = Config()
    cfg.llm.enabled = True
    cfg.llm.api_key_env = "STENO10K_TEST_KEY"
    monkeypatch.setenv("STENO10K_TEST_KEY", "sk-test")
    client = make_llm(cfg)
    assert isinstance(client, OpenAICompatibleClient)
