from __future__ import annotations


def extract_retry_after_seconds(err: Exception) -> float | None:
    """Best-effort read of a server-suggested retry delay from a rate-limit error.

    Provider-neutral: only the standard HTTP `Retry-After` response header is
    honored. Any OpenAI-compatible gateway returns it; no vendor-specific
    error-body parsing is done.
    """
    resp = getattr(err, "response", None)
    if resp is not None:
        headers = getattr(resp, "headers", None)
        if headers:
            ra = headers.get("retry-after") or headers.get("Retry-After")
            if ra:
                try:
                    return float(ra)
                except (TypeError, ValueError):
                    return None
    return None


def compute_backoff_wait(
    attempt: int,
    *,
    initial: float,
    base: float,
    max_wait: float,
    rate_limit_floor: float,
    is_rate_limit: bool,
    server_hint: float | None,
) -> float:
    """Backoff for a failed attempt (1-based).

    Non-rate-limit: exponential backoff capped at `max_wait`.
    Rate-limit: the larger of the backoff, the floor, and any server hint.
    """
    base_wait = min(max_wait, initial * (base ** (attempt - 1)))
    if not is_rate_limit:
        return base_wait
    return max(base_wait, rate_limit_floor, server_hint or 0.0)
