"""Unit tests for tasks.py — RestateResponse validator and restate injection detection."""

from __future__ import annotations

import pytest

from refund_pilot.workers.tasks import (
    _RESTATE_CHAR_LIMIT,
    _RESTATE_FALLBACK,
    _RESTATE_INJECTION_MSG,
    RestateResponse,
)

pytestmark = pytest.mark.no_api


class TestRestateResponse:
    def test_valid_short_text_unchanged(self) -> None:
        r = RestateResponse(text="Refund denied. Decision is final.")
        assert r.text == "Refund denied. Decision is final."

    def test_strips_leading_trailing_whitespace(self) -> None:
        r = RestateResponse(text="  Refund denied.  ")
        assert r.text == "Refund denied."

    def test_long_text_not_truncated(self) -> None:
        # max_tokens=80 bounds Claude output at API level — validator does not truncate
        long_text = "A" * 200
        r = RestateResponse(text=long_text)
        assert r.text == long_text

    def test_exactly_at_limit_unchanged(self) -> None:
        text = "B" * _RESTATE_CHAR_LIMIT
        r = RestateResponse(text=text)
        assert r.text == text

    def test_empty_string_returns_fallback(self) -> None:
        r = RestateResponse(text="")
        assert r.text == _RESTATE_FALLBACK

    def test_whitespace_only_returns_fallback(self) -> None:
        r = RestateResponse(text="   \n\t  ")
        assert r.text == _RESTATE_FALLBACK

    def test_fallback_constant_not_truncated(self) -> None:
        # Fallback text may exceed 80 chars — must flow as-is (static value, not LLM output)
        assert len(_RESTATE_FALLBACK) > 0
        r = RestateResponse(text="")
        assert r.text == _RESTATE_FALLBACK

    def test_injection_msg_constant_defined(self) -> None:
        assert "logged" in _RESTATE_INJECTION_MSG
        assert "notified" in _RESTATE_INJECTION_MSG
        assert len(_RESTATE_INJECTION_MSG) > 0
