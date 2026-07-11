from __future__ import annotations

from steno10k.lib.retry import compute_backoff_wait, extract_retry_after_seconds


def _wait(attempt: int, is_rate_limit: bool = False, server_hint: float | None = None) -> float:
    return compute_backoff_wait(
        attempt,
        initial=2.0,
        base=2.0,
        max_wait=60.0,
        rate_limit_floor=30.0,
        is_rate_limit=is_rate_limit,
        server_hint=server_hint,
    )


def test_backoff_grows_exponentially() -> None:
    assert _wait(1) == 2.0
    assert _wait(2) == 4.0
    assert _wait(3) == 8.0


def test_backoff_capped_at_max_wait() -> None:
    assert _wait(10) == 60.0


def test_rate_limit_uses_floor_when_backoff_is_smaller() -> None:
    assert _wait(1, is_rate_limit=True) == 30.0


def test_rate_limit_server_hint_wins_when_largest() -> None:
    assert _wait(1, is_rate_limit=True, server_hint=45.0) == 45.0


def test_non_rate_limit_ignores_floor_and_hint() -> None:
    assert _wait(1, is_rate_limit=False, server_hint=999.0) == 2.0


class _Resp:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


class _Err(Exception):
    def __init__(self, msg: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(msg)
        self.response = _Resp(headers) if headers is not None else None


def test_extract_retry_after_from_header() -> None:
    assert extract_retry_after_seconds(_Err("boom", headers={"Retry-After": "12"})) == 12.0


def test_provider_specific_body_is_ignored() -> None:
    assert extract_retry_after_seconds(_Err("429 ... retry_delay { seconds: 42 } ...")) is None


def test_extract_retry_after_none_when_absent() -> None:
    assert extract_retry_after_seconds(_Err("plain error")) is None
