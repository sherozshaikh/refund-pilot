from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

try:
    import anthropic as _anthropic

    def _is_retryable_anthropic(exc: BaseException) -> bool:
        if isinstance(exc, _anthropic.APIStatusError):
            return exc.status_code >= 500  # retry server errors only, not 4xx
        return isinstance(exc, _anthropic.APITimeoutError)

    _ANTHROPIC_RETRY_FN: Callable[[BaseException], bool] = _is_retryable_anthropic
except ImportError:

    def _noop_anthropic_retry(_exc: BaseException) -> bool:
        return False

    _ANTHROPIC_RETRY_FN = _noop_anthropic_retry


def claude_retry(max_retries: int = 1, min_wait: float = 1.0, max_wait: float = 10.0) -> Any:
    """Retry decorator for Claude API calls. Default: 1 attempt (no retry)."""
    from tenacity import retry_if_exception

    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception(_ANTHROPIC_RETRY_FN)
        | retry_if_exception_type(httpx.TimeoutException),
        reraise=True,
    )


def db_retry(max_retries: int = 3, min_wait: float = 0.5, max_wait: float = 5.0) -> Any:
    """Retry decorator for database queries."""
    from sqlalchemy.exc import DisconnectionError, OperationalError

    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception_type((OperationalError, DisconnectionError)),
        reraise=True,
    )
