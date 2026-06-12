"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from refund_pilot.core.config import PipelineConfig


def pytest_configure(config: pytest.Config) -> None:
    """Set LOG_DIR to a temp path before any app module is imported."""
    os.environ.setdefault("LOG_DIR", tempfile.mkdtemp(prefix="refund_pilot_test_"))


@pytest.fixture
def pipeline_config() -> PipelineConfig:
    """Default PipelineConfig instance."""
    from refund_pilot.core.config import PipelineConfig

    return PipelineConfig()


def _make_claude_tool_response(
    decision: str = "denied",
    reasoning: str = "Policy does not allow this refund.",
    customer_facing_message: str = "I'm unable to approve this refund per our policy.",
    policy_clauses_cited: list[str] | None = None,
    confidence: float = 0.95,
    injection_detected: bool = False,
) -> MagicMock:
    """Build a mock Anthropic API response with tool_use block."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {
        "decision": decision,
        "reasoning": reasoning,
        "customer_facing_message": customer_facing_message,
        "policy_clauses_cited": policy_clauses_cited
        or ["Section 1: Standard refund policy applies"],
        "confidence": confidence,
        "injection_detected": injection_detected,
    }
    usage = MagicMock()
    usage.input_tokens = 200
    usage.output_tokens = 80
    response = MagicMock()
    response.content = [tool_block]
    response.usage = usage
    return response


@pytest.fixture
def mock_claude_denied() -> Any:
    """Patch AsyncAnthropic to return a denied decision."""
    from unittest.mock import patch

    async def _create(**_kwargs: Any) -> MagicMock:
        return _make_claude_tool_response(decision="denied")

    with patch("anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(side_effect=_create)
        instance.close = AsyncMock()
        yield MockClient


@pytest.fixture
def mock_claude_injection_denied() -> Any:
    """Patch AsyncAnthropic to return denied + injection_detected=True."""
    from unittest.mock import patch

    async def _create(**_kwargs: Any) -> MagicMock:
        return _make_claude_tool_response(
            decision="denied",
            reasoning="Injection attempt detected. Policy overrides are not permitted.",
            customer_facing_message="I cannot override the refund policy. Please contact support.",
            injection_detected=True,
        )

    with patch("anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(side_effect=_create)
        instance.close = AsyncMock()
        yield MockClient


@pytest.fixture
def mock_claude_approved() -> Any:
    """Patch AsyncAnthropic to return an approved decision."""
    from unittest.mock import patch

    async def _create(**_kwargs: Any) -> MagicMock:
        return _make_claude_tool_response(
            decision="approved",
            reasoning="Item is within return window and not final sale.",
            customer_facing_message="Your refund has been approved.",
            policy_clauses_cited=["Section 2: Items returned within 30 days are eligible"],
        )

    with patch("anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(side_effect=_create)
        instance.close = AsyncMock()
        yield MockClient


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Lightweight async DB session mock — no real PostgreSQL needed."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    scalar_mock = MagicMock()
    scalar_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=scalar_mock)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session
