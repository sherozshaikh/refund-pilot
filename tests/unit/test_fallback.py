"""FallbackHandler regex matching tests."""

import pytest

from refund_pilot.agent.fallback import FallbackHandler

pytestmark = pytest.mark.no_api


@pytest.fixture
def handler():
    return FallbackHandler()


def test_refund_pattern(handler):
    result = handler.handle("I want a refund for my order")
    assert result is not None
    assert "No decision has been made" in result


def test_defective_pattern(handler):
    result = handler.handle("The item arrived broken")
    assert result is not None


def test_cancel_pattern(handler):
    result = handler.handle("I want to cancel my order")
    assert result is not None


def test_escalation_pattern(handler):
    result = handler.handle("I want to escalate this issue")
    assert result is not None


def test_no_match_returns_none(handler):
    result = handler.handle("Hello, how are you doing today?")
    assert result is None
