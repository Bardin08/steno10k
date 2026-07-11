from __future__ import annotations

from pathlib import Path

import pytest
from openai import OpenAIError

from steno10k.contracts.config import LLMConfig
from steno10k.contracts.llm import LLMClient
from steno10k.lib.llm import OpenAICompatibleClient


class _Msg:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str | None) -> None:
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content: str | None) -> None:
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, behaviors: list[object]) -> None:
        self._behaviors = list(behaviors)
        self.calls = 0

    def create(self, **kwargs: object) -> _Resp:
        b = self._behaviors[self.calls]
        self.calls += 1
        if isinstance(b, Exception):
            raise b
        return _Resp(b)  # type: ignore[arg-type]


class _Chat:
    def __init__(self, behaviors: list[object]) -> None:
        self.completions = _Completions(behaviors)


class FakeOpenAI:
    """Stands in for `openai.OpenAI`; `behaviors` is a list of str|Exception."""

    def __init__(self, behaviors: list[object]) -> None:
        self.chat = _Chat(behaviors)


def _cfg() -> LLMConfig:
    return LLMConfig(model="test-model", base_url="http://local", temperature=0.2, max_tokens=100)


def test_satisfies_llmclient_protocol() -> None:
    client: LLMClient = OpenAICompatibleClient(_cfg(), client=FakeOpenAI(["hi"]))  # type: ignore[arg-type]
    assert client.complete("sys", "user") == "hi"


def test_content_is_stripped() -> None:
    c = OpenAICompatibleClient(_cfg(), client=FakeOpenAI(["  padded \n"]))  # type: ignore[arg-type]
    assert c.complete("s", "u") == "padded"


def test_none_content_becomes_empty_string() -> None:
    c = OpenAICompatibleClient(_cfg(), client=FakeOpenAI([None]))  # type: ignore[arg-type]
    assert c.complete("s", "u") == ""


def test_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    import steno10k.lib.llm as llmmod

    monkeypatch.setattr(llmmod.time, "sleep", lambda _s: None)
    fake = FakeOpenAI([OpenAIError("boom"), "recovered"])
    c = OpenAICompatibleClient(_cfg(), client=fake)  # type: ignore[arg-type]
    assert c.complete("s", "u") == "recovered"
    assert fake.chat.completions.calls == 2


def test_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    import steno10k.lib.llm as llmmod

    monkeypatch.setattr(llmmod.time, "sleep", lambda _s: None)
    fake = FakeOpenAI([OpenAIError("e1"), OpenAIError("e2"), OpenAIError("e3")])
    c = OpenAICompatibleClient(_cfg(), client=fake)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        c.complete("s", "u")
    assert fake.chat.completions.calls == 3


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Missing API key"):
        OpenAICompatibleClient(_cfg())


def test_no_vendor_names_anywhere_in_lib() -> None:
    lib_dir = Path(__file__).resolve().parents[2] / "src" / "steno10k" / "lib"
    for py in lib_dir.glob("*.py"):
        lowered = py.read_text(encoding="utf-8").lower()
        for vendor in ("gemini", "anthropic", "claude", "google"):
            assert vendor not in lowered, f"vendor name {vendor!r} in {py.name}"
