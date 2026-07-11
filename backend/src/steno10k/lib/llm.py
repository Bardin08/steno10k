from __future__ import annotations

import logging
import os
import time as time

import httpx
from openai import APIStatusError, OpenAI, OpenAIError, RateLimitError

from steno10k.contracts.config import LLMConfig
from steno10k.lib.retry import compute_backoff_wait, extract_retry_after_seconds

log = logging.getLogger("steno10k.llm")

# Retry/timeout policy is a hardcoded M1 constant set — not a user knob. Deferred
# to M2; see the deferred-config ADR under docs/adr/.
_TIMEOUT_SECONDS = 120
_MAX_RETRIES = 3
_RETRY_INITIAL_WAIT = 2.0
_RETRY_BACKOFF_BASE = 2.0
_RETRY_MAX_WAIT = 60.0
_RETRY_RATE_LIMIT_WAIT = 60.0


class OpenAICompatibleClient:
    """`contracts.llm.LLMClient` over any OpenAI-compatible chat-completions endpoint.

    Provider-neutral: base URL + model come from `LLMConfig`; rate-limit backoff
    uses the standard `Retry-After` header (via `lib.retry`). No vendor-specific code.
    """

    def __init__(self, config: LLMConfig, *, client: OpenAI | None = None) -> None:
        self.config = config
        if client is not None:
            self.client = client
            return
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key. Set env var {config.api_key_env}.")
        kwargs: dict[str, object] = {"api_key": api_key, "timeout": _TIMEOUT_SECONDS}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self.client = OpenAI(**kwargs)  # type: ignore[arg-type]

    def _compute_wait(self, attempt: int, err: Exception) -> float:
        is_rate_limit = isinstance(err, RateLimitError) or (
            isinstance(err, APIStatusError) and getattr(err, "status_code", None) == 429
        )
        return compute_backoff_wait(
            attempt,
            initial=_RETRY_INITIAL_WAIT,
            base=_RETRY_BACKOFF_BASE,
            max_wait=_RETRY_MAX_WAIT,
            rate_limit_floor=_RETRY_RATE_LIMIT_WAIT,
            is_rate_limit=is_rate_limit,
            server_hint=extract_retry_after_seconds(err),
        )

    def complete(self, system: str, user: str) -> str:
        last_err: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return (resp.choices[0].message.content or "").strip()
            except (OpenAIError, httpx.HTTPError) as e:
                last_err = e
                if attempt >= _MAX_RETRIES:
                    break
                log.warning(
                    "LLM call failed (attempt %s/%s): %s. Retrying.",
                    attempt,
                    _MAX_RETRIES,
                    e,
                )
                time.sleep(self._compute_wait(attempt, e))
        raise RuntimeError(f"LLM call failed after {_MAX_RETRIES} attempts: {last_err}")
